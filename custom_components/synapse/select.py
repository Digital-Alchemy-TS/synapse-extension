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
    """Set up the select platform.

    Creates select entities from app configuration and sets up dynamic
    entity registration for runtime configuration updates.
    """
    bridge: SynapseBridge = hass.data[DOMAIN][config_entry.entry_id]

    # Use dynamic configuration if available, otherwise fall back to static config
    entities: List[SynapseSelectDefinition] = []
    if bridge._current_configuration and "select" in bridge._current_configuration:
        entities = bridge._current_configuration.get("select", [])
    else:
        entities = bridge.app_data.get("select", [])

    if entities:
        async_add_entities(SynapseSelect(hass, bridge, entity) for entity in entities)

    # Listen for registration events to add new entities dynamically
    async def handle_registration(event):
        """Handle registration events to add new select entities.

        Called when an app sends updated configuration. Adds new select
        entities that weren't present in the initial configuration.
        """
        if event.data.get("unique_id") == bridge.metadata_unique_id:
            # Check if there are new select entities in the dynamic configuration
            if bridge._current_configuration and "select" in bridge._current_configuration:
                new_entities = bridge._current_configuration.get("select", [])
                if new_entities:
                    async_add_entities(SynapseSelect(hass, bridge, entity) for entity in new_entities)

    # Register the event listener
    hass.bus.async_listen(bridge.event_name("register"), handle_registration)

class SynapseSelect(SynapseBaseEntity, SelectEntity):
    """Home Assistant select entity for Synapse apps.

    Represents a dropdown selection from a connected NodeJS app. Handles
    option selection and state updates through the bridge.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        bridge: SynapseBridge,
        entity: SynapseSelectDefinition,
    ) -> None:
        """Initialize the select entity."""
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
