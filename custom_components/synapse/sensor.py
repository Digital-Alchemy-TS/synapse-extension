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
    """Setup the sensor platform."""
    bridge: SynapseBridge = hass.data[DOMAIN][config_entry.entry_id]

    # Use dynamic configuration if available, otherwise fall back to static config
    entities: List[SynapseSensorDefinition] = []
    if bridge._current_configuration and "sensor" in bridge._current_configuration:
        entities = bridge._current_configuration.get("sensor", [])
        bridge.logger.info(f"Sensor platform setup: Using dynamic configuration with {len(entities)} entities")
    else:
        entities = bridge.app_data.get("sensor", [])
        bridge.logger.info(f"Sensor platform setup: Using static configuration with {len(entities)} entities")

    if entities:
        bridge.logger.info(f"Adding {len(entities)} sensor entities: {[e.get('name') for e in entities]}")
        async_add_entities(SynapseSensor(hass, bridge, entity) for entity in entities)
    else:
        bridge.logger.info("No sensor entities to add")

    # Listen for registration events to add new entities dynamically
    async def handle_registration(event):
        """Handle registration events to add new sensor entities."""
        bridge.logger.info(f"Sensor platform received registration event: {event.data}")
        bridge.logger.info(f"Event unique_id: {event.data.get('unique_id')}, bridge.metadata_unique_id: {bridge.metadata_unique_id}")

        if event.data.get("unique_id") == bridge.metadata_unique_id:
            bridge.logger.info("Registration event received, checking for new sensor entities")

            # Check if there are new sensor entities in the dynamic configuration
            if bridge._current_configuration and "sensor" in bridge._current_configuration:
                new_entities = bridge._current_configuration.get("sensor", [])
                if new_entities:
                    bridge.logger.info(f"Adding {len(new_entities)} new sensor entities: {[e.get('name') for e in new_entities]}")
                    async_add_entities(SynapseSensor(hass, bridge, entity) for entity in new_entities)
                else:
                    bridge.logger.debug("No new sensor entities found in registration")
            else:
                bridge.logger.debug("No dynamic configuration found for sensor entities")
        else:
            bridge.logger.debug(f"Registration event not for this bridge: {event.data.get('unique_id')} != {bridge.metadata_unique_id}")

    # Register the event listener
    bridge.logger.info(f"Registering sensor platform event listener for: {bridge.event_name('register')}")
    bridge.logger.info(f"Bridge metadata_unique_id: {bridge.metadata_unique_id}")
    hass.bus.async_listen(bridge.event_name("register"), handle_registration)
    bridge.logger.info("Sensor platform event listener registered successfully")

class SynapseSensor(SynapseBaseEntity, SensorEntity):
    def __init__(
        self, hass: HomeAssistant, bridge: SynapseBridge, entity: SynapseSensorDefinition
    ) -> None:
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
