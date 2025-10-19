from __future__ import annotations

import logging
from typing import Any, List, Optional

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback, HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .synapse.base_entity import SynapseBaseEntity
from .synapse.bridge import SynapseBridge
from .synapse.const import DOMAIN, SynapseSelectDefinition

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Setup the select platform."""
    bridge: SynapseBridge = hass.data[DOMAIN][config_entry.entry_id]

    # Use dynamic configuration if available, otherwise fall back to static config
    entities: List[SynapseSelectDefinition] = []
    if bridge._current_configuration and "select" in bridge._current_configuration:
        entities = bridge._current_configuration.get("select", [])
        bridge.logger.info(f"Select platform setup: Using dynamic configuration with {len(entities)} entities")
    else:
        entities = bridge.app_data.get("select", [])
        bridge.logger.info(f"Select platform setup: Using static configuration with {len(entities)} entities")

    if entities:
        bridge.logger.info(f"Adding {len(entities)} select entities: {[e.get('name') for e in entities]}")
        async_add_entities(SynapseSelect(hass, bridge, entity) for entity in entities)
    else:
        bridge.logger.info("No select entities to add")

    # Listen for registration events to add new entities dynamically
    async def handle_registration(event):
        """Handle registration events to add new select entities."""
        bridge.logger.info(f"Select platform received registration event: {event.data}")
        bridge.logger.info(f"Event unique_id: {event.data.get('unique_id')}, bridge.metadata_unique_id: {bridge.metadata_unique_id}")

        if event.data.get("unique_id") == bridge.metadata_unique_id:
            bridge.logger.info("Registration event received, checking for new select entities")

            # Check if there are new select entities in the dynamic configuration
            if bridge._current_configuration and "select" in bridge._current_configuration:
                new_entities = bridge._current_configuration.get("select", [])
                if new_entities:
                    bridge.logger.info(f"Adding {len(new_entities)} new select entities: {[e.get('name') for e in new_entities]}")
                    async_add_entities(SynapseSelect(hass, bridge, entity) for entity in new_entities)
                else:
                    bridge.logger.debug("No new select entities found in registration")
            else:
                bridge.logger.debug("No dynamic configuration found for select entities")
        else:
            bridge.logger.debug(f"Registration event not for this bridge: {event.data.get('unique_id')} != {bridge.metadata_unique_id}")

    # Register the event listener
    bridge.logger.info(f"Registering select platform event listener for: {bridge.event_name('register')}")
    bridge.logger.info(f"Bridge metadata_unique_id: {bridge.metadata_unique_id}")
    hass.bus.async_listen(bridge.event_name("register"), handle_registration)
    bridge.logger.info("Select platform event listener registered successfully")

class SynapseSelect(SynapseBaseEntity, SelectEntity):
    def __init__(
        self,
        hass: HomeAssistant,
        bridge: SynapseBridge,
        entity: SynapseSelectDefinition,
    ) -> None:
        super().__init__(hass, bridge, entity)
        self.logger: logging.Logger = logging.getLogger(__name__)

    @property
    def current_option(self) -> Optional[str]:
        return self.entity.get("current_option")

    @property
    def options(self) -> List[str]:
        return self.entity.get("options", [])

    @callback
    async def async_select_option(self, option: str, **kwargs: Any) -> None:
        """Proxy the request to select an option."""
        await self.bridge.emit_event(
            "select_option",
            {"unique_id": self.entity.get("unique_id"), "option": option, **kwargs},
        )
