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
    """Setup the number platform."""
    bridge: SynapseBridge = hass.data[DOMAIN][config_entry.entry_id]

    # Use dynamic configuration if available, otherwise fall back to static config
    entities: List[SynapseNumberDefinition] = []
    if bridge._current_configuration and "number" in bridge._current_configuration:
        entities = bridge._current_configuration.get("number", [])
        bridge.logger.info(f"Number platform setup: Using dynamic configuration with {len(entities)} entities")
    else:
        entities = bridge.app_data.get("number", [])
        bridge.logger.info(f"Number platform setup: Using static configuration with {len(entities)} entities")

    if entities:
        bridge.logger.info(f"Adding {len(entities)} number entities: {[e.get('name') for e in entities]}")
        async_add_entities(SynapseNumber(hass, bridge, entity) for entity in entities)
    else:
        bridge.logger.info("No number entities to add")

    # Listen for registration events to add new entities dynamically
    async def handle_registration(event):
        """Handle registration events to add new number entities."""
        bridge.logger.info(f"Number platform received registration event: {event.data}")
        bridge.logger.info(f"Event unique_id: {event.data.get('unique_id')}, bridge.metadata_unique_id: {bridge.metadata_unique_id}")

        if event.data.get("unique_id") == bridge.metadata_unique_id:
            bridge.logger.info("Registration event received, checking for new number entities")

            # Check if there are new number entities in the dynamic configuration
            if bridge._current_configuration and "number" in bridge._current_configuration:
                new_entities = bridge._current_configuration.get("number", [])
                if new_entities:
                    bridge.logger.info(f"Adding {len(new_entities)} new number entities: {[e.get('name') for e in new_entities]}")
                    async_add_entities(SynapseNumber(hass, bridge, entity) for entity in new_entities)
                else:
                    bridge.logger.debug("No new number entities found in registration")
            else:
                bridge.logger.debug("No dynamic configuration found for number entities")
        else:
            bridge.logger.debug(f"Registration event not for this bridge: {event.data.get('unique_id')} != {bridge.metadata_unique_id}")

    # Register the event listener
    bridge.logger.info(f"Registering number platform event listener for: {bridge.event_name('register')}")
    bridge.logger.info(f"Bridge metadata_unique_id: {bridge.metadata_unique_id}")
    hass.bus.async_listen(bridge.event_name("register"), handle_registration)
    bridge.logger.info("Number platform event listener registered successfully")

class SynapseNumber(SynapseBaseEntity, NumberEntity):
    def __init__(
        self,
        hass: HomeAssistant,
        bridge: SynapseBridge,
        entity: SynapseNumberDefinition,
    ) -> None:
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
