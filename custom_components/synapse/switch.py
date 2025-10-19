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
    """Setup the switch platform."""
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
        """Handle registration events to add new switch entities."""
        bridge.logger.info(f"Switch platform received registration event: {event.data}")
        bridge.logger.info(f"Event unique_id: {event.data.get('unique_id')}, bridge.metadata_unique_id: {bridge.metadata_unique_id}")

        if event.data.get("unique_id") == bridge.metadata_unique_id:
            bridge.logger.info("Registration event received, checking for new switch entities")

            # Check if there are new switch entities in the dynamic configuration
            if bridge._current_configuration and "switch" in bridge._current_configuration:
                new_entities = bridge._current_configuration.get("switch", [])
                if new_entities:
                    bridge.logger.info(f"Adding {len(new_entities)} new switch entities: {[e.get('name') for e in new_entities]}")
                    async_add_entities(SynapseSwitch(hass, bridge, entity) for entity in new_entities)
                else:
                    bridge.logger.debug("No new switch entities found in registration")
            else:
                bridge.logger.debug("No dynamic configuration found for switch entities")
        else:
            bridge.logger.debug(f"Registration event not for this bridge: {event.data.get('unique_id')} != {bridge.metadata_unique_id}")

    # Register the event listener
    bridge.logger.info(f"Registering switch platform event listener for: {bridge.event_name('register')}")
    bridge.logger.info(f"Bridge metadata_unique_id: {bridge.metadata_unique_id}")
    hass.bus.async_listen(bridge.event_name("register"), handle_registration)
    bridge.logger.info("Switch platform event listener registered successfully")

class SynapseSwitch(SynapseBaseEntity, SwitchEntity):
    def __init__(
        self,
        hass: HomeAssistant,
        bridge: SynapseBridge,
        entity: SynapseSwitchDefinition,
    ) -> None:
        super().__init__(hass, bridge, entity)
        self.logger: logging.Logger = logging.getLogger(__name__)

    @property
    def is_on(self) -> bool:
        return self.entity.get("is_on", False)

    @property
    def device_class(self) -> Optional[str]:
        return self.entity.get("device_class")

    @callback
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Handle the switch press."""
        await self.bridge.emit_event(
            "turn_on", {"unique_id": self.entity.get("unique_id"), **kwargs}
        )

    @callback
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Handle the switch press."""
        await self.bridge.emit_event(
            "turn_off", {"unique_id": self.entity.get("unique_id"), **kwargs}
        )

    @callback
    async def async_turn_toggle(self, **kwargs: Any) -> None:
        """Handle the switch press."""
        await self.bridge.emit_event(
            "toggle", {"unique_id": self.entity.get("unique_id"), **kwargs}
        )
