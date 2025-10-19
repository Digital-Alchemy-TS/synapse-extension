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
    """Setup the date platform."""
    bridge: SynapseBridge = hass.data[DOMAIN][config_entry.entry_id]

    # Use dynamic configuration if available, otherwise fall back to static config
    entities: List[SynapseDateDefinition] = []
    if bridge._current_configuration and "date" in bridge._current_configuration:
        entities = bridge._current_configuration.get("date", [])
        bridge.logger.info(f"Date platform setup: Using dynamic configuration with {len(entities)} entities")
    else:
        entities = bridge.app_data.get("date", [])
        bridge.logger.info(f"Date platform setup: Using static configuration with {len(entities)} entities")

    if entities:
        bridge.logger.info(f"Adding {len(entities)} date entities: {[e.get('name') for e in entities]}")
        async_add_entities(SynapseDate(hass, bridge, entity) for entity in entities)
    else:
        bridge.logger.info("No date entities to add")

    # Listen for registration events to add new entities dynamically
    async def handle_registration(event):
        """Handle registration events to add new date entities."""
        bridge.logger.info(f"Date platform received registration event: {event.data}")
        bridge.logger.info(f"Event unique_id: {event.data.get('unique_id')}, bridge.metadata_unique_id: {bridge.metadata_unique_id}")

        if event.data.get("unique_id") == bridge.metadata_unique_id:
            bridge.logger.info("Registration event received, checking for new date entities")

            # Check if there are new date entities in the dynamic configuration
            if bridge._current_configuration and "date" in bridge._current_configuration:
                new_entities = bridge._current_configuration.get("date", [])
                if new_entities:
                    bridge.logger.info(f"Adding {len(new_entities)} new date entities: {[e.get('name') for e in new_entities]}")
                    async_add_entities(SynapseDate(hass, bridge, entity) for entity in new_entities)
                else:
                    bridge.logger.debug("No new date entities found in registration")
            else:
                bridge.logger.debug("No dynamic configuration found for date entities")
        else:
            bridge.logger.debug(f"Registration event not for this bridge: {event.data.get('unique_id')} != {bridge.metadata_unique_id}")

    # Register the event listener
    bridge.logger.info(f"Registering date platform event listener for: {bridge.event_name('register')}")
    bridge.logger.info(f"Bridge metadata_unique_id: {bridge.metadata_unique_id}")
    hass.bus.async_listen(bridge.event_name("register"), handle_registration)
    bridge.logger.info("Date platform event listener registered successfully")

class SynapseDate(SynapseBaseEntity, DateEntity):
    def __init__(
        self,
        hass: HomeAssistant,
        bridge: SynapseBridge,
        entity: SynapseDateDefinition,
    ) -> None:
        super().__init__(hass, bridge, entity)
        self.logger: logging.Logger = logging.getLogger(__name__)

    @property
    def native_value(self) -> Optional[date]:
        native_value = self.entity.get("native_value")
        if native_value is not None:
            return date.fromisoformat(native_value)
        return None

    @callback
    async def async_set_value(self, value: date, **kwargs: Any) -> None:
        """Proxy the request to set the value."""
        await self.bridge.emit_event(
            "set_value",
            {"unique_id": self.entity.get("unique_id"), "value": value, **kwargs},
        )
