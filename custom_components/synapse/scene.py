from __future__ import annotations

import logging
from typing import List

from homeassistant.components.scene import Scene as SceneEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback, HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .synapse.base_entity import SynapseBaseEntity
from .synapse.bridge import SynapseBridge
from .synapse.const import DOMAIN, SynapseSceneDefinition

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the scene platform.

    Creates scene entities from app configuration and sets up dynamic
    entity registration for runtime configuration updates.
    """
    bridge: SynapseBridge = hass.data[DOMAIN][config_entry.entry_id]

    # Use dynamic configuration if available, otherwise fall back to static config
    entities: List[SynapseSceneDefinition] = []
    if bridge._current_configuration and "scene" in bridge._current_configuration:
        entities = bridge._current_configuration.get("scene", [])
    else:
        entities = bridge.app_data.get("scene", [])

    if entities:
        async_add_entities(SynapseScene(hass, bridge, entity) for entity in entities)

    # Listen for registration events to add new entities dynamically
    async def handle_registration(event):
        """Handle registration events to add new scene entities.

        Called when an app sends updated configuration. Adds new scene
        entities that weren't present in the initial configuration.
        """
        if event.data.get("unique_id") == bridge.metadata_unique_id:
            # Check if there are new scene entities in the dynamic configuration
            if bridge._current_configuration and "scene" in bridge._current_configuration:
                new_entities = bridge._current_configuration.get("scene", [])
                if new_entities:
                    async_add_entities(SynapseScene(hass, bridge, entity) for entity in new_entities)

    # Register the event listener
    hass.bus.async_listen(bridge.event_name("register"), handle_registration)

class SynapseScene(SynapseBaseEntity, SceneEntity):
    """Home Assistant scene entity for Synapse apps.

    Represents a scene from a connected NodeJS app. Handles scene
    activation through the bridge.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        bridge: SynapseBridge,
        entity: SynapseSceneDefinition,
    ) -> None:
        """Initialize the scene entity."""
        super().__init__(hass, bridge, entity)
        self.logger: logging.Logger = logging.getLogger(__name__)

    @callback
    async def async_activate(self) -> None:
        """Activate the scene.

        Sends an activate event to the connected app with the entity's unique_id.
        """
        await self.bridge.emit_event(
            "activate", {"unique_id": self.entity.get("unique_id")}
        )
