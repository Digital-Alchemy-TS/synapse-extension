"""
# Digital Alchemy Synapse base entity

This base class is used across the various entity domains:
- associates entity with device
- handles standard entity interactions
- availability
- live configuration updates

It is up to the helper domains to:
- extend this
- override logger
- implement domain specific properties & event callbacks
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from homeassistant.const import EntityCategory
from homeassistant.core import callback, HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity

from .bridge import SynapseBridge
from .const import SynapseBaseEntity

class SynapseBaseEntity(Entity):
    def __init__(
        self,
        hass: HomeAssistant,
        bridge: SynapseBridge,
        entity: SynapseBaseEntity
    ) -> None:
        """Init"""
        self.logger: logging.Logger = logging.getLogger(__name__)
        self.hass: HomeAssistant = hass
        self.bridge: SynapseBridge = bridge
        self.entity: SynapseBaseEntity = entity
        self.logger.debug(f"{self.bridge.app_name} init entity: {self.entity.get('name')}")
        self.async_on_remove(
            self.hass.bus.async_listen(
                self.bridge.event_name("update"),
                self._handle_entity_update,
            )
        )
        self.async_on_remove(
            self.hass.bus.async_listen(
                self.bridge.event_name("health"),
                self._handle_availability_update,
            )
        )

    @property
    def device_info(self) -> DeviceInfo:
        """Return device registry information for this entity."""
        declared_device = self.entity.get("device_id", "")
        if len(declared_device) > 0:
            device = self.bridge.via_primary_device[declared_device] or None
            if device is not None:
                return device
            self.logger.error(f"{self.bridge.app_name}:{self.entity.get('name')} cannot find device info for {declared_device}")

        # everything is associated with the app device if all else fails
        return self.bridge.primary_device

    @property
    def unique_id(self) -> str:
        return self.entity.get("unique_id")

    @property
    def suggested_object_id(self) -> str:
        return self.entity.get("suggested_object_id")

    @property
    def translation_key(self) -> Optional[str]:
        return self.entity.get("translation_key")

    @property
    def icon(self) -> Optional[str]:
        return self.entity.get("icon")

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        return self.entity.get("attributes") or {}

    @property
    def entity_category(self) -> Optional[EntityCategory]:
        if self.entity.get("entity_category") == "config":
            return EntityCategory.CONFIG
        if self.entity.get("entity_category") == "diagnostic":
            return EntityCategory.DIAGNOSTIC
        return None

    @property
    def name(self) -> str:
        return self.entity.get("name")

    @property
    def suggested_area_id(self) -> Optional[str]:
        return self.entity.get("area_id")

    @property
    def labels(self) -> List[str]:
        return self.entity.get("labels")

    @property
    def available(self) -> bool:
        """
        - if the bridge is offline
        - if the entity opts into being unavail but still declared (ts side)
        """
        if self.entity.get("disabled") == True:
            return False
        return self.bridge.online

    @callback
    def _handle_entity_update(self, event: Any) -> None:
        # events target bridge, up to entities to filter for responses that apply to them
        #
        # mental note: this was done to reduce quantity of unique events flying around
        # this is probably worth changing to namespace/{unique_id}/update or something
        # easier to debug + less useless event handle executions
        if event.data.get("unique_id") == self.entity.get("unique_id"):
            self.logger.debug(f"{self.bridge.app_name}:{self.entity.get('name')} receive update")
            self.entity = event.data.get("data")
            self.async_write_ha_state()

    @callback
    def _handle_availability_update(self, event: Any) -> None:
        """Handle health status update."""
        self.async_schedule_update_ha_state(True)
