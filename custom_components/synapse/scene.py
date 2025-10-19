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
    """Setup the scene platform."""
    bridge: SynapseBridge = hass.data[DOMAIN][config_entry.entry_id]

    # Use dynamic configuration if available, otherwise fall back to static config
    entities: List[SynapseSceneDefinition] = []
    if bridge._current_configuration and "scene" in bridge._current_configuration:
        entities = bridge._current_configuration.get("scene", [])
        bridge.logger.info(f"Scene platform setup: Using dynamic configuration with {len(entities)} entities")
    else:
        entities = bridge.app_data.get("scene", [])
        bridge.logger.info(f"Scene platform setup: Using static configuration with {len(entities)} entities")

    if entities:
        bridge.logger.info(f"Adding {len(entities)} scene entities: {[e.get('name') for e in entities]}")
        async_add_entities(SynapseScene(hass, bridge, entity) for entity in entities)
    else:
        bridge.logger.info("No scene entities to add")

    # Listen for registration events to add new entities dynamically
    async def handle_registration(event):
        """Handle registration events to add new scene entities."""
        bridge.logger.info(f"Scene platform received registration event: {event.data}")
        bridge.logger.info(f"Event unique_id: {event.data.get('unique_id')}, bridge.metadata_unique_id: {bridge.metadata_unique_id}")

        if event.data.get("unique_id") == bridge.metadata_unique_id:
            bridge.logger.info("Registration event received, checking for new scene entities")

            # Check if there are new scene entities in the dynamic configuration
            if bridge._current_configuration and "scene" in bridge._current_configuration:
                new_entities = bridge._current_configuration.get("scene", [])
                if new_entities:
                    bridge.logger.info(f"Adding {len(new_entities)} new scene entities: {[e.get('name') for e in new_entities]}")
                    async_add_entities(SynapseScene(hass, bridge, entity) for entity in new_entities)
                else:
                    bridge.logger.debug("No new scene entities found in registration")
            else:
                bridge.logger.debug("No dynamic configuration found for scene entities")
        else:
            bridge.logger.debug(f"Registration event not for this bridge: {event.data.get('unique_id')} != {bridge.metadata_unique_id}")

    # Register the event listener
    bridge.logger.info(f"Registering scene platform event listener for: {bridge.event_name('register')}")
    bridge.logger.info(f"Bridge metadata_unique_id: {bridge.metadata_unique_id}")
    hass.bus.async_listen(bridge.event_name("register"), handle_registration)
    bridge.logger.info("Scene platform event listener registered successfully")

class SynapseScene(SynapseBaseEntity, SceneEntity):
    def __init__(
        self,
        hass: HomeAssistant,
        bridge: SynapseBridge,
        entity: SynapseSceneDefinition,
    ) -> None:
        super().__init__(hass, bridge, entity)
        self.logger: logging.Logger = logging.getLogger(__name__)

    @callback
    async def async_activate(self) -> None:
        """Handle the scene press."""
        await self.bridge.emit_event(
            "activate", {"unique_id": self.entity.get("unique_id")}
        )
