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
    """Setup the router platform."""
    bridge: SynapseBridge = hass.data[DOMAIN][config_entry.entry_id]
    entities: List[SynapseSensorDefinition] = bridge.app_data.get("sensor", [])
    if entities is not None:
      async_add_entities(SynapseSensor(hass, bridge, entity) for entity in entities)

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
