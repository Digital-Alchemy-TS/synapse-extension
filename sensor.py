from __future__ import annotations

import logging
from typing import Any, List, Optional

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .synapse.base_entity import SynapseBaseEntity
from .synapse.bridge import SynapseBridge
from .synapse.const import DOMAIN, SynapseSensorDefinition

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform.

    Creates sensor entities from app configuration and sets up dynamic
    entity registration for runtime configuration updates.
    """
    bridge: SynapseBridge = hass.data[DOMAIN][config_entry.entry_id]

    # Use dynamic configuration if available, otherwise fall back to static config
    entities: List[SynapseSensorDefinition] = []
    if bridge._current_configuration and "sensor" in bridge._current_configuration:
        entities = bridge._current_configuration.get("sensor", [])
    else:
        entities = bridge.app_data.get("sensor", [])

    if entities:
        async_add_entities(SynapseSensor(hass, bridge, entity) for entity in entities)

    # Listen for registration events to add new entities dynamically
    async def handle_registration(event):
        """Handle registration events to add new sensor entities.

        Called when an app sends updated configuration. Adds new sensor
        entities that weren't present in the initial configuration.
        """
        if event.data.get("unique_id") == bridge.metadata_unique_id:
            # Check if there are new sensor entities in the dynamic configuration
            if bridge._current_configuration and "sensor" in bridge._current_configuration:
                new_entities = bridge._current_configuration.get("sensor", [])
                if new_entities:
                    async_add_entities(SynapseSensor(hass, bridge, entity) for entity in new_entities)

    # Register the event listener
    hass.bus.async_listen(bridge.event_name("register"), handle_registration)

class SynapseSensor(SynapseBaseEntity, SensorEntity):
    """Home Assistant sensor entity for Synapse apps.

    Represents a sensor from a connected NodeJS app. Handles state updates
    and configuration changes through the bridge.
    """

    def __init__(
        self, hass: HomeAssistant, bridge: SynapseBridge, entity: SynapseSensorDefinition
    ) -> None:
        """Initialize the sensor entity."""
        super().__init__(hass, bridge, entity)
        self.logger: logging.Logger = logging.getLogger(__name__)

    @property
    def state(self) -> Optional[str | int]:
        return self.entity.get("state")

    @property
    def state_class(self) -> Optional[str]:
        return self.entity.get("state_class")

    @property
    def suggested_display_precision(self) -> Optional[int]:
        return self.entity.get("suggested_display_precision")

    @property
    def capability_attributes(self) -> Optional[int]:
        return self.entity.get("capability_attributes")

    @property
    def native_unit_of_measurement(self) -> Optional[str]:
        return self.entity.get("native_unit_of_measurement")

    @property
    def supported_features(self) -> int:
        return self.entity.get("supported_features", 0)

    @property
    def device_class(self) -> Optional[str]:
        return self.entity.get("device_class")

    @property
    def unit_of_measurement(self) -> Optional[str]:
        return self.entity.get("unit_of_measurement")

    @property
    def options(self) -> List[str]:
        return self.entity.get("options", [])

    @property
    def last_reset(self) -> Optional[str]:
        return self.entity.get("last_reset")
