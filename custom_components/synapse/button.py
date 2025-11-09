from __future__ import annotations

import logging
from typing import Any, List, Optional

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback, HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .synapse.base_entity import SynapseBaseEntity
from .synapse.bridge import SynapseBridge
from .synapse.const import DOMAIN, SynapseButtonDefinition

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the button platform.

    Creates button entities from app configuration and sets up dynamic
    entity registration for runtime configuration updates.
    """
    bridge: SynapseBridge = hass.data[DOMAIN][config_entry.entry_id]

    # Use dynamic configuration if available, otherwise fall back to static config
    entities: List[SynapseButtonDefinition] = []
    if bridge._current_configuration and "button" in bridge._current_configuration:
        entities = bridge._current_configuration.get("button", [])
    else:
        entities = bridge.app_data.get("button", [])

    if entities:
        async_add_entities(SynapseButton(hass, bridge, entity) for entity in entities)

    # Listen for registration events to add new entities dynamically
    async def handle_registration(event):
        """Handle registration events to add new button entities.

        Called when an app sends updated configuration. Adds new button
        entities that weren't present in the initial configuration.
        """
        if event.data.get("unique_id") == bridge.metadata_unique_id:
            # Check if there are new button entities in the dynamic configuration
            if bridge._current_configuration and "button" in bridge._current_configuration:
                new_entities = bridge._current_configuration.get("button", [])
                if new_entities:
                    async_add_entities(SynapseButton(hass, bridge, entity) for entity in new_entities)

    # Register the event listener
    hass.bus.async_listen(bridge.event_name("register"), handle_registration)

class SynapseButton(SynapseBaseEntity, ButtonEntity):
    """Home Assistant button entity for Synapse apps.

    Represents a button from a connected NodeJS app. Handles button
    press events through the bridge.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        bridge: SynapseBridge,
        entity: SynapseButtonDefinition,
    ) -> None:
        """Initialize the button entity."""
        super().__init__(hass, bridge, entity)
        self.logger: logging.Logger = logging.getLogger(__name__)

    @property
    def device_class(self) -> Optional[str]:
        """Return the device class of the button."""
        return self.entity.get("device_class")

    @callback
    async def async_press(self, **kwargs: Any) -> None:
        """Handle the button press.

        Sends a press event to the connected app with the entity's unique_id.
        """
        await self.bridge.emit_event(
            "press",
            {"unique_id": self.entity.get("unique_id"), **kwargs},
        )
