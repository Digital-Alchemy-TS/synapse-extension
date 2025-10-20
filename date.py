from __future__ import annotations

import logging
from datetime import date
from typing import Any, List, Optional

from homeassistant.components.date import DateEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback, HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .synapse.base_entity import SynapseBaseEntity
from .synapse.bridge import SynapseBridge
from .synapse.const import DOMAIN, SynapseDateDefinition

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the date platform.

    Creates date entities from app configuration and sets up dynamic
    entity registration for runtime configuration updates.
    """
    bridge: SynapseBridge = hass.data[DOMAIN][config_entry.entry_id]

    # Use dynamic configuration if available, otherwise fall back to static config
    entities: List[SynapseDateDefinition] = []
    if bridge._current_configuration and "date" in bridge._current_configuration:
        entities = bridge._current_configuration.get("date", [])
    else:
        entities = bridge.app_data.get("date", [])

    if entities:
        async_add_entities(SynapseDate(hass, bridge, entity) for entity in entities)

    # Listen for registration events to add new entities dynamically
    async def handle_registration(event):
        """Handle registration events to add new date entities.

        Called when an app sends updated configuration. Adds new date
        entities that weren't present in the initial configuration.
        """
        if event.data.get("unique_id") == bridge.metadata_unique_id:
            # Check if there are new date entities in the dynamic configuration
            if bridge._current_configuration and "date" in bridge._current_configuration:
                new_entities = bridge._current_configuration.get("date", [])
                if new_entities:
                    async_add_entities(SynapseDate(hass, bridge, entity) for entity in new_entities)

    # Register the event listener
    hass.bus.async_listen(bridge.event_name("register"), handle_registration)

class SynapseDate(SynapseBaseEntity, DateEntity):
    """Home Assistant date entity for Synapse apps.

    Represents a date input from a connected NodeJS app. Handles
    date value updates and user interactions through the bridge.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        bridge: SynapseBridge,
        entity: SynapseDateDefinition,
    ) -> None:
        """Initialize the date entity."""
        super().__init__(hass, bridge, entity)
        self.logger: logging.Logger = logging.getLogger(__name__)

    @property
    def native_value(self) -> Optional[date]:
        """Return the current date value."""
        native_value = self.entity.get("native_value")
        if native_value is not None:
            return date.fromisoformat(native_value)
        return None

    @callback
    async def async_set_value(self, value: date, **kwargs: Any) -> None:
        """Set the date value.

        Sends a set_value event to the connected app with the entity's unique_id
        and the new date value.
        """
        await self.bridge.emit_event(
            "set_value",
            {"unique_id": self.entity.get("unique_id"), "value": value, **kwargs},
        )
