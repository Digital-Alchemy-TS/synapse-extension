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
    """Setup the binary_sensor platform."""
    bridge: SynapseBridge = hass.data[DOMAIN][config_entry.entry_id]

    # Use dynamic configuration if available, otherwise fall back to static config
    entities: List[SynapseBinarySensorDefinition] = []
    if bridge._current_configuration and "binary_sensor" in bridge._current_configuration:
        entities = bridge._current_configuration.get("binary_sensor", [])
    else:
        entities = bridge.app_data.get("binary_sensor", [])

    if entities:
        async_add_entities(SynapseBinarySensor(hass, bridge, entity) for entity in entities)

    # add health check sensor
    health = SynapseHealthSensor(bridge, hass)
    async_add_entities([health])

    # Listen for registration events to add new entities dynamically
    async def handle_registration(event):
        """Handle registration events to add new binary_sensor entities."""
        bridge.logger.info(f"Binary sensor platform received registration event: {event.data}")
        bridge.logger.info(f"Event unique_id: {event.data.get('unique_id')}, bridge.metadata_unique_id: {bridge.metadata_unique_id}")

        if event.data.get("unique_id") == bridge.metadata_unique_id:
            bridge.logger.info("Registration event received, checking for new binary_sensor entities")

            # Check if there are new binary_sensor entities in the dynamic configuration
            if bridge._current_configuration and "binary_sensor" in bridge._current_configuration:
                new_entities = bridge._current_configuration.get("binary_sensor", [])
                if new_entities:
                    bridge.logger.info(f"Adding {len(new_entities)} new binary_sensor entities: {[e.get('name') for e in new_entities]}")
                    async_add_entities(SynapseBinarySensor(hass, bridge, entity) for entity in new_entities)
                else:
                    bridge.logger.debug("No new binary_sensor entities found in registration")
            else:
                bridge.logger.debug("No dynamic configuration found for binary_sensor entities")
        else:
            bridge.logger.debug(f"Registration event not for this bridge: {event.data.get('unique_id')} != {bridge.metadata_unique_id}")

    # Register the event listener
    bridge.logger.info(f"Registering binary_sensor platform event listener for: {bridge.event_name('register')}")
    bridge.logger.info(f"Bridge metadata_unique_id: {bridge.metadata_unique_id}")
    hass.bus.async_listen(bridge.event_name("register"), handle_registration)
    bridge.logger.info("Binary sensor platform event listener registered successfully")

class SynapseBinarySensor(SynapseBaseEntity, BinarySensorEntity):
    def __init__(
        self,
        hass: HomeAssistant,
        bridge: SynapseBridge,
        entity: SynapseBinarySensorDefinition,
    ) -> None:
        super().__init__(hass, bridge, entity)
        self.logger: logging.Logger = logging.getLogger(__name__)

    @property
    def device_class(self) -> Optional[str]:
        return self.entity.get("device_class")

    @property
    def is_on(self) -> bool:
        return self.entity.get("is_on", False)
