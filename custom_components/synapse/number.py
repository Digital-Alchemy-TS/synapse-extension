from __future__ import annotations

import logging
from typing import Any, List, Optional

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback, HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .synapse.base_entity import SynapseBaseEntity
from .synapse.bridge import SynapseBridge
from .synapse.const import DOMAIN, SynapseNumberDefinition

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Setup the router platform."""
    bridge: SynapseBridge = hass.data[DOMAIN][config_entry.entry_id]
    entities: List[SynapseNumberDefinition] = bridge.app_data.get("number", [])
    if entities is not None:
      async_add_entities(SynapseNumber(hass, bridge, entity) for entity in entities)

class SynapseNumber(SynapseBaseEntity, NumberEntity):
    def __init__(
        self,
        hass: HomeAssistant,
        bridge: SynapseBridge,
        entity: SynapseNumberDefinition,
    ) -> None:
        super().__init__(hass, bridge, entity)
        self.logger: logging.Logger = logging.getLogger(__name__)

    @property
    def device_class(self) -> Optional[str]:
        return self.entity.get("device_class")

    @property
    def mode(self) -> str:
        return self.entity.get("mode", "auto")

    @property
    def native_max_value(self) -> float:
        return self.entity.get("native_max_value", 100.0)

    @property
    def native_value(self) -> Optional[float]:
        return self.entity.get("native_value")

    @property
    def native_min_value(self) -> float:
        return self.entity.get("native_min_value", 0.0)

    @property
    def native_step(self) -> float:
        return self.entity.get("step", 1.0)

    @property
    def native_unit_of_measurement(self) -> Optional[str]:
        return self.entity.get("native_unit_of_measurement")

    @callback
    async def async_set_native_value(self, value: float, **kwargs: Any) -> None:
        """Proxy the request to set the value."""
        self.hass.bus.async_fire(
            self.bridge.event_name("set_value"),
            {"unique_id": self.entity.get("unique_id"), "value": value, **kwargs},
        )
