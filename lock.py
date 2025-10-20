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
    """Set up the lock platform.

    Creates lock entities from app configuration and sets up dynamic
    entity registration for runtime configuration updates.
    """
    bridge: SynapseBridge = hass.data[DOMAIN][config_entry.entry_id]

    # Use dynamic configuration if available, otherwise fall back to static config
    entities: List[SynapseLockDefinition] = []
    if bridge._current_configuration and "lock" in bridge._current_configuration:
        entities = bridge._current_configuration.get("lock", [])
    else:
        entities = bridge.app_data.get("lock", [])

    if entities:
        async_add_entities(SynapseLock(hass, bridge, entity) for entity in entities)

    # Listen for registration events to add new entities dynamically
    async def handle_registration(event):
        """Handle registration events to add new lock entities.

        Called when an app sends updated configuration. Adds new lock
        entities that weren't present in the initial configuration.
        """
        if event.data.get("unique_id") == bridge.metadata_unique_id:
            # Check if there are new lock entities in the dynamic configuration
            if bridge._current_configuration and "lock" in bridge._current_configuration:
                new_entities = bridge._current_configuration.get("lock", [])
                if new_entities:
                    async_add_entities(SynapseLock(hass, bridge, entity) for entity in new_entities)

    # Register the event listener
    hass.bus.async_listen(bridge.event_name("register"), handle_registration)

class SynapseLock(SynapseBaseEntity, LockEntity):
    """Home Assistant lock entity for Synapse apps.

    Represents a lock from a connected NodeJS app. Handles lock/unlock
    operations and state monitoring through the bridge.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        bridge: SynapseBridge,
        entity: SynapseLockDefinition,
    ) -> None:
        """Initialize the lock entity."""
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
        await self.bridge.emit_event(
            "lock", {"unique_id": self.entity.get("unique_id"), **kwargs}
        )

    @callback
    async def async_unlock(self, **kwargs: Any) -> None:
        """Proxy the request to unlock."""
        await self.bridge.emit_event(
            "unlock", {"unique_id": self.entity.get("unique_id"), **kwargs}
        )

    @callback
    async def async_open(self, **kwargs: Any) -> None:
        """Proxy the request to open."""
        await self.bridge.emit_event(
            "open", {"unique_id": self.entity.get("unique_id"), **kwargs}
        )
