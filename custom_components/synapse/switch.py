from __future__ import annotations

import logging
from typing import Any, List, Optional

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback, HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .synapse.base_entity import SynapseBaseEntity
from .synapse.bridge import SynapseBridge
from .synapse.const import DOMAIN, SynapseSwitchDefinition

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the switch platform.

    Creates switch entities from app configuration and sets up dynamic
    entity registration for runtime configuration updates.
    """
    bridge: SynapseBridge = hass.data[DOMAIN][config_entry.entry_id]

    # Use dynamic configuration if available, otherwise fall back to static config
    entities: List[SynapseSwitchDefinition] = []
    if bridge._current_configuration and "switch" in bridge._current_configuration:
        entities = bridge._current_configuration.get("switch", [])
    else:
        entities = bridge.app_data.get("switch", [])

    if entities:
        async_add_entities(SynapseSwitch(hass, bridge, entity) for entity in entities)

    # Listen for registration events to add new entities dynamically
    async def handle_registration(event):
        """Handle registration events to add new switch entities.

        Called when an app sends updated configuration. Adds new switch
        entities that weren't present in the initial configuration.
        """
        if event.data.get("unique_id") == bridge.metadata_unique_id:
            # Check if there are new switch entities in the dynamic configuration
            if bridge._current_configuration and "switch" in bridge._current_configuration:
                new_entities = bridge._current_configuration.get("switch", [])
                if new_entities:
                    async_add_entities(SynapseSwitch(hass, bridge, entity) for entity in new_entities)

    # Register the event listener
    hass.bus.async_listen(bridge.event_name("register"), handle_registration)

class SynapseSwitch(SynapseBaseEntity, SwitchEntity):
    """Home Assistant switch entity for Synapse apps.

    Represents a switch from a connected NodeJS app. Handles state updates
    and user interactions through the bridge.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        bridge: SynapseBridge,
        entity: SynapseSwitchDefinition,
    ) -> None:
        """Initialize the switch entity."""
        super().__init__(hass, bridge, entity)
        self.logger: logging.Logger = logging.getLogger(__name__)

    @property
    def is_on(self) -> bool:
        """Return True if the switch is on."""
        return self.entity.get("is_on", False)

    @property
    def device_class(self) -> Optional[str]:
        """Return the device class of the switch."""
        return self.entity.get("device_class")

    @callback
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on.

        Sends a turn_on event to the connected app with the entity's unique_id.
        """
        await self.bridge.emit_event(
            "turn_on", {"unique_id": self.entity.get("unique_id"), **kwargs}
        )

    @callback
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off.

        Sends a turn_off event to the connected app with the entity's unique_id.
        """
        await self.bridge.emit_event(
            "turn_off", {"unique_id": self.entity.get("unique_id"), **kwargs}
        )

    @callback
    async def async_turn_toggle(self, **kwargs: Any) -> None:
        """Toggle the switch state.

        Sends a toggle event to the connected app with the entity's unique_id.
        """
        await self.bridge.emit_event(
            "toggle", {"unique_id": self.entity.get("unique_id"), **kwargs}
        )
