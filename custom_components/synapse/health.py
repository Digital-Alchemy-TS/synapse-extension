from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.const import EntityCategory
from homeassistant.core import callback, HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo

from .synapse.bridge import SynapseBridge

class SynapseHealthSensor(BinarySensorEntity):
    def __init__(
        self,
        bridge: SynapseBridge,
        hass: HomeAssistant
    ) -> None:
        self.logger: logging.Logger = logging.getLogger(__name__)
        self.hass: HomeAssistant = hass
        self.bridge: SynapseBridge = bridge
        self.async_on_remove(
            self.hass.bus.async_listen(
                self.bridge.event_name("health"),
                self._handle_availability_update,
            )
        )

    @property
    def device_info(self) -> DeviceInfo:
        return self.bridge.primary_device

    @property
    def icon(self) -> str:
        if self.bridge.online:
            return "mdi:server"
        return "mdi:server-outline"

    @property
    def entity_category(self) -> EntityCategory:
        return EntityCategory.DIAGNOSTIC

    @property
    def name(self) -> str:
        return f"{self.bridge.app_data.get('title')} Online"

    @property
    def unique_id(self) -> str:
        return f"{self.bridge.app_data.get('unique_id')}-online"

    @property
    def is_on(self) -> bool:
        return self.bridge.online

    @callback
    def _handle_availability_update(self, event: Any) -> None:
        """Handle health status update."""
        self.async_schedule_update_ha_state(True)
