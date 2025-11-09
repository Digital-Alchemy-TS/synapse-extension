from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.const import EntityCategory
from homeassistant.core import callback, HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo

from .synapse.bridge import SynapseBridge

class SynapseHealthSensor(BinarySensorEntity):
    """Health sensor for monitoring Synapse app connectivity.

    This binary sensor indicates whether the connected NodeJS app is online
    and responding to heartbeats. Automatically generated for each app.
    """

    def __init__(
        self,
        bridge: SynapseBridge,
        hass: HomeAssistant
    ) -> None:
        """Initialize the health sensor."""
        self.logger: logging.Logger = logging.getLogger(__name__)
        self.hass: HomeAssistant = hass
        self.bridge: SynapseBridge = bridge

        # Listen for health events to update availability status
        self.async_on_remove(
            self.hass.bus.async_listen(
                self.bridge.event_name("health"),
                self._handle_availability_update,
            )
        )

    @property
    def device_info(self) -> DeviceInfo:
        """Return device registry information for this entity."""
        return self.bridge.primary_device

    @property
    def icon(self) -> str:
        """Return the icon based on online status."""
        if self.bridge.online:
            return "mdi:server"
        return "mdi:server-outline"

    @property
    def entity_category(self) -> EntityCategory:
        """Return the entity category (diagnostic)."""
        return EntityCategory.DIAGNOSTIC

    @property
    def name(self) -> str:
        """Return the name of the health sensor."""
        return f"{self.bridge.app_data.get('title')} Online"

    @property
    def unique_id(self) -> str:
        """Return the unique ID of the health sensor."""
        return f"{self.bridge.app_data.get('unique_id')}-online"

    @property
    def is_on(self) -> bool:
        """Return True if the app is online."""
        return self.bridge.online

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        return {
            "application_unique_id": self.bridge.app_data.get("unique_id"),
        }

    @callback
    def _handle_availability_update(self, event: Any) -> None:
        """Handle health status update.

        Called when the bridge's online status changes. Updates the sensor
        state to reflect the current connectivity status.
        """
        self.async_schedule_update_ha_state(True)
