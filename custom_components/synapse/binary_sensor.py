from __future__ import annotations

import logging
from typing import List, Optional

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .synapse.bridge import SynapseBridge
from .synapse.const import DOMAIN, SynapseBinarySensorDefinition
from .synapse.base_entity import SynapseBaseEntity
from .health import SynapseHealthSensor

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the binary_sensor platform.

    Creates binary sensor entities from app configuration, adds a health
    sensor, and sets up dynamic entity registration for runtime updates.
    """
    bridge: SynapseBridge = hass.data[DOMAIN][config_entry.entry_id]

    # Use dynamic configuration if available, otherwise fall back to static config
    entities: List[SynapseBinarySensorDefinition] = []
    if bridge._current_configuration and "binary_sensor" in bridge._current_configuration:
        entities = bridge._current_configuration.get("binary_sensor", [])
    else:
        entities = bridge.app_data.get("binary_sensor", [])

    if entities:
        async_add_entities(SynapseBinarySensor(hass, bridge, entity) for entity in entities)

    # Add health check sensor to monitor app connectivity
    health = SynapseHealthSensor(bridge, hass)
    # Register the health sensor as a generated entity (not from app registration)
    bridge.register_generated_entity(health.unique_id)
    async_add_entities([health])

    # Listen for registration events to add new entities dynamically
    async def handle_registration(event):
        """Handle registration events to add new binary_sensor entities.

        Called when an app sends updated configuration. Adds new binary sensor
        entities that weren't present in the initial configuration.
        """
        if event.data.get("unique_id") == bridge.metadata_unique_id:
            # Check if there are new binary_sensor entities in the dynamic configuration
            if bridge._current_configuration and "binary_sensor" in bridge._current_configuration:
                new_entities = bridge._current_configuration.get("binary_sensor", [])
                if new_entities:
                    async_add_entities(SynapseBinarySensor(hass, bridge, entity) for entity in new_entities)

    # Register the event listener
    hass.bus.async_listen(bridge.event_name("register"), handle_registration)

class SynapseBinarySensor(SynapseBaseEntity, BinarySensorEntity):
    """Home Assistant binary sensor entity for Synapse apps.

    Represents a binary sensor from a connected NodeJS app. Handles state
    updates and configuration changes through the bridge.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        bridge: SynapseBridge,
        entity: SynapseBinarySensorDefinition,
    ) -> None:
        """Initialize the binary sensor entity."""
        super().__init__(hass, bridge, entity)
        self.logger: logging.Logger = logging.getLogger(__name__)

    @property
    def device_class(self) -> Optional[str]:
        """Return the device class of the binary sensor."""
        return self.entity.get("device_class")

    @property
    def is_on(self) -> bool:
        """Return True if the binary sensor is on."""
        return self.entity.get("is_on", False)
