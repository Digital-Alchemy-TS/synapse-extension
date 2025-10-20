from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, List, Optional

from homeassistant.components.datetime import DateTimeEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback, HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .synapse.base_entity import SynapseBaseEntity
from .synapse.bridge import SynapseBridge
from .synapse.const import DOMAIN, SynapseDateTimeDefinition

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the datetime platform.

    Creates datetime entities from app configuration and sets up dynamic
    entity registration for runtime configuration updates.
    """
    bridge: SynapseBridge = hass.data[DOMAIN][config_entry.entry_id]

    # Use dynamic configuration if available, otherwise fall back to static config
    entities: List[SynapseDateTimeDefinition] = []
    if bridge._current_configuration and "datetime" in bridge._current_configuration:
        entities = bridge._current_configuration.get("datetime", [])
    else:
        entities = bridge.app_data.get("datetime", [])

    if entities:
        async_add_entities(SynapseDateTime(hass, bridge, entity) for entity in entities)

    # Listen for registration events to add new entities dynamically
    async def handle_registration(event):
        """Handle registration events to add new datetime entities.

        Called when an app sends updated configuration. Adds new datetime
        entities that weren't present in the initial configuration.
        """
        if event.data.get("unique_id") == bridge.metadata_unique_id:
            # Check if there are new datetime entities in the dynamic configuration
            if bridge._current_configuration and "datetime" in bridge._current_configuration:
                new_entities = bridge._current_configuration.get("datetime", [])
                if new_entities:
                    async_add_entities(SynapseDateTime(hass, bridge, entity) for entity in new_entities)

    # Register the event listener
    hass.bus.async_listen(bridge.event_name("register"), handle_registration)

class SynapseDateTime(SynapseBaseEntity, DateTimeEntity):
    """Home Assistant datetime entity for Synapse apps.

    Represents a datetime input from a connected NodeJS app. Handles
    datetime value updates and user interactions through the bridge.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        bridge: SynapseBridge,
        entity: SynapseDateTimeDefinition,
    ) -> None:
        """Initialize the datetime entity."""
        super().__init__(hass, bridge, entity)
        self.logger: logging.Logger = logging.getLogger(__name__)

    @property
    def native_value(self) -> Optional[datetime]:
        """Return the current datetime value."""
        native_value = self.entity.get("native_value")
        if native_value is not None:
            return datetime.fromisoformat(native_value)
        return None

    @callback
    async def async_set_value(self, value: datetime, **kwargs: Any) -> None:
        """Set the datetime value.

        Sends a set_value event to the connected app with the entity's unique_id
        and the new datetime value in ISO format.
        """
        await self.bridge.emit_event(
            "set_value",
            {"unique_id": self.entity.get("unique_id"), "value": value.isoformat(), **kwargs},
        )
