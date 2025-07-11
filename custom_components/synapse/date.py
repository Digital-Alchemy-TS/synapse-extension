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
    """Setup the router platform."""
    bridge: SynapseBridge = hass.data[DOMAIN][config_entry.entry_id]
    entities: List[SynapseDateDefinition] = bridge.app_data.get("date", [])
    if entities is not None:
        async_add_entities(SynapseDate(hass, bridge, entity) for entity in entities)

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
        self.hass.bus.async_fire(
            self.bridge.event_name("set_value"),
            {"unique_id": self.entity.get("unique_id"), "value": value, **kwargs},
        )
