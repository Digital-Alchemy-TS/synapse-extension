from __future__ import annotations

import logging
from typing import Any, List, Optional

from homeassistant.components.lock import LockEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback, HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .synapse.base_entity import SynapseBaseEntity
from .synapse.bridge import SynapseBridge
from .synapse.const import DOMAIN, SynapseLockDefinition

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Setup the router platform."""
    bridge: SynapseBridge = hass.data[DOMAIN][config_entry.entry_id]
    entities: List[SynapseLockDefinition] = bridge.app_data.get("lock", [])
    if entities is not None:
      async_add_entities(SynapseLock(hass, bridge, entity) for entity in entities)

class SynapseLock(SynapseBaseEntity, LockEntity):
    def __init__(
        self,
        hass: HomeAssistant,
        bridge: SynapseBridge,
        entity: SynapseLockDefinition,
    ) -> None:
        super().__init__(hass, bridge, entity)
        self.logger: logging.Logger = logging.getLogger(__name__)

    @property
    def changed_by(self) -> Optional[str]:
        return self.entity.get("changed_by")

    @property
    def code_format(self) -> Optional[str]:
        return self.entity.get("code_format")

    @property
    def is_locked(self) -> bool:
        return self.entity.get("is_locked", False)

    @property
    def is_locking(self) -> bool:
        return self.entity.get("is_locking", False)

    @property
    def is_unlocking(self) -> bool:
        return self.entity.get("is_unlocking", False)

    @property
    def is_jammed(self) -> bool:
        return self.entity.get("is_jammed", False)

    @property
    def is_opening(self) -> bool:
        return self.entity.get("is_opening", False)

    @property
    def is_open(self) -> bool:
        return self.entity.get("is_open", False)

    @property
    def supported_features(self) -> int:
        return self.entity.get("supported_features", 0)

    @callback
    async def async_lock(self, **kwargs: Any) -> None:
        """Proxy the request to lock."""
        self.hass.bus.async_fire(
            self.bridge.event_name("lock"), {"unique_id": self.entity.get("unique_id"), **kwargs}
        )

    @callback
    async def async_unlock(self, **kwargs: Any) -> None:
        """Proxy the request to unlock."""
        self.hass.bus.async_fire(
            self.bridge.event_name("unlock"), {"unique_id": self.entity.get("unique_id"), **kwargs}
        )

    @callback
    async def async_open(self, **kwargs: Any) -> None:
        """Proxy the request to open."""
        self.hass.bus.async_fire(
            self.bridge.event_name("open"), {"unique_id": self.entity.get("unique_id"), **kwargs}
        )
