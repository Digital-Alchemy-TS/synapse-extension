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
    """Setup the router platform."""
    bridge: SynapseBridge = hass.data[DOMAIN][config_entry.entry_id]
    entities: List[SynapseBinarySensorDefinition] = bridge.app_data.get("binary_sensor", [])

    if entities is not None:
      async_add_entities(SynapseBinarySensor(hass, bridge, entity) for entity in entities)

    # add health check sensor
    health = SynapseHealthSensor(bridge, hass)
    async_add_entities([health])

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
