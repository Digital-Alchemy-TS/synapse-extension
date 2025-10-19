from __future__ import annotations

import logging
from typing import Any, List, Optional

from homeassistant.components.text import TextEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback, HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .synapse.base_entity import SynapseBaseEntity
from .synapse.bridge import SynapseBridge
from .synapse.const import DOMAIN, SynapseTextDefinition

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Setup the text platform."""
    bridge: SynapseBridge = hass.data[DOMAIN][config_entry.entry_id]

    # Use dynamic configuration if available, otherwise fall back to static config
    entities: List[SynapseTextDefinition] = []
    if bridge._current_configuration and "text" in bridge._current_configuration:
        entities = bridge._current_configuration.get("text", [])
        bridge.logger.info(f"Text platform setup: Using dynamic configuration with {len(entities)} entities")
    else:
        entities = bridge.app_data.get("text", [])
        bridge.logger.info(f"Text platform setup: Using static configuration with {len(entities)} entities")

    if entities:
        bridge.logger.info(f"Adding {len(entities)} text entities: {[e.get('name') for e in entities]}")
        async_add_entities(SynapseText(hass, bridge, entity) for entity in entities)
    else:
        bridge.logger.info("No text entities to add")

    # Listen for registration events to add new entities dynamically
    async def handle_registration(event):
        """Handle registration events to add new text entities."""
        bridge.logger.info(f"Text platform received registration event: {event.data}")
        bridge.logger.info(f"Event unique_id: {event.data.get('unique_id')}, bridge.metadata_unique_id: {bridge.metadata_unique_id}")

        if event.data.get("unique_id") == bridge.metadata_unique_id:
            bridge.logger.info("Registration event received, checking for new text entities")

            # Check if there are new text entities in the dynamic configuration
            if bridge._current_configuration and "text" in bridge._current_configuration:
                new_entities = bridge._current_configuration.get("text", [])
                if new_entities:
                    bridge.logger.info(f"Adding {len(new_entities)} new text entities: {[e.get('name') for e in new_entities]}")
                    async_add_entities(SynapseText(hass, bridge, entity) for entity in new_entities)
                else:
                    bridge.logger.debug("No new text entities found in registration")
            else:
                bridge.logger.debug("No dynamic configuration found for text entities")
        else:
            bridge.logger.debug(f"Registration event not for this bridge: {event.data.get('unique_id')} != {bridge.metadata_unique_id}")

    # Register the event listener
    bridge.logger.info(f"Registering text platform event listener for: {bridge.event_name('register')}")
    bridge.logger.info(f"Bridge metadata_unique_id: {bridge.metadata_unique_id}")
    hass.bus.async_listen(bridge.event_name("register"), handle_registration)
    bridge.logger.info("Text platform event listener registered successfully")

class SynapseText(SynapseBaseEntity, TextEntity):
    def __init__(
        self,
        hass: HomeAssistant,
        bridge: SynapseBridge,
        entity: SynapseTextDefinition,
    ) -> None:
        super().__init__(hass, bridge, entity)
        self.logger: logging.Logger = logging.getLogger(__name__)

    @property
    def native_value(self) -> Optional[str]:
        return self.entity.get("native_value")

    @callback
    async def async_set_value(self, value: str, **kwargs: Any) -> None:
        """Proxy the request to set the value."""
        await self.bridge.emit_event(
            "set_value",
            {"unique_id": self.entity.get("unique_id"), "value": value, **kwargs},
        )
