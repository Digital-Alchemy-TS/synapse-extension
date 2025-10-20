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
    """Set up the text platform.

    Creates text entities from app configuration and sets up dynamic
    entity registration for runtime configuration updates.
    """
    bridge: SynapseBridge = hass.data[DOMAIN][config_entry.entry_id]

    # Use dynamic configuration if available, otherwise fall back to static config
    entities: List[SynapseTextDefinition] = []
    if bridge._current_configuration and "text" in bridge._current_configuration:
        entities = bridge._current_configuration.get("text", [])
    else:
        entities = bridge.app_data.get("text", [])

    if entities:
        async_add_entities(SynapseText(hass, bridge, entity) for entity in entities)

    # Listen for registration events to add new entities dynamically
    async def handle_registration(event):
        """Handle registration events to add new text entities.

        Called when an app sends updated configuration. Adds new text
        entities that weren't present in the initial configuration.
        """
        if event.data.get("unique_id") == bridge.metadata_unique_id:
            # Check if there are new text entities in the dynamic configuration
            if bridge._current_configuration and "text" in bridge._current_configuration:
                new_entities = bridge._current_configuration.get("text", [])
                if new_entities:
                    async_add_entities(SynapseText(hass, bridge, entity) for entity in new_entities)

    # Register the event listener
    hass.bus.async_listen(bridge.event_name("register"), handle_registration)

class SynapseText(SynapseBaseEntity, TextEntity):
    """Home Assistant text entity for Synapse apps.

    Represents a text input from a connected NodeJS app. Handles
    text value updates and user interactions through the bridge.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        bridge: SynapseBridge,
        entity: SynapseTextDefinition,
    ) -> None:
        """Initialize the text entity."""
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
