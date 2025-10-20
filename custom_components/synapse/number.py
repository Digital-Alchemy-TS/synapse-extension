from __future__ import annotations

import logging
from typing import Any, List, Optional

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback, HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .synapse.base_entity import SynapseBaseEntity
from .synapse.bridge import SynapseBridge
from .synapse.const import DOMAIN, SynapseNumberDefinition

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the number platform.

    Creates number entities from app configuration and sets up dynamic
    entity registration for runtime configuration updates.
    """
    bridge: SynapseBridge = hass.data[DOMAIN][config_entry.entry_id]

    # Use dynamic configuration if available, otherwise fall back to static config
    entities: List[SynapseNumberDefinition] = []
    if bridge._current_configuration and "number" in bridge._current_configuration:
        entities = bridge._current_configuration.get("number", [])
    else:
        entities = bridge.app_data.get("number", [])

    if entities:
        async_add_entities(SynapseNumber(hass, bridge, entity) for entity in entities)

    # Listen for registration events to add new entities dynamically
    async def handle_registration(event):
        """Handle registration events to add new number entities.

        Called when an app sends updated configuration. Adds new number
        entities that weren't present in the initial configuration.
        """
        if event.data.get("unique_id") == bridge.metadata_unique_id:
            # Check if there are new number entities in the dynamic configuration
            if bridge._current_configuration and "number" in bridge._current_configuration:
                new_entities = bridge._current_configuration.get("number", [])
                if new_entities:
                    async_add_entities(SynapseNumber(hass, bridge, entity) for entity in new_entities)

    # Register the event listener
    hass.bus.async_listen(bridge.event_name("register"), handle_registration)

class SynapseNumber(SynapseBaseEntity, NumberEntity):
    """Home Assistant number entity for Synapse apps.

    Represents a numeric input from a connected NodeJS app. Handles
    numeric value updates and user interactions through the bridge.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        bridge: SynapseBridge,
        entity: SynapseNumberDefinition,
    ) -> None:
        """Initialize the number entity."""
        super().__init__(hass, bridge, entity)
        self.logger: logging.Logger = logging.getLogger(__name__)

    @property
    def device_class(self) -> Optional[str]:
        return self.entity.get("device_class")

    @property
    def mode(self) -> str:
        return self.entity.get("mode", "auto")

    @property
    def native_max_value(self) -> float:
        return self.entity.get("native_max_value", 100.0)

    @property
    def native_value(self) -> Optional[float]:
        return self.entity.get("native_value")

    @property
    def native_min_value(self) -> float:
        return self.entity.get("native_min_value", 0.0)

    @property
    def native_step(self) -> float:
        return self.entity.get("step", 1.0)

    @property
    def native_unit_of_measurement(self) -> Optional[str]:
        return self.entity.get("native_unit_of_measurement")

    @callback
    async def async_set_native_value(self, value: float, **kwargs: Any) -> None:
        """Proxy the request to set the value."""
        await self.bridge.emit_event(
            "set_value",
            {"unique_id": self.entity.get("unique_id"), "value": value, **kwargs},
        )
