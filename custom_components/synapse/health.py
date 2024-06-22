from .bridge import SynapseBridge
from .const import DOMAIN

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback, HomeAssistant
from homeassistant.const import EntityCategory
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.components.binary_sensor import BinarySensorEntity
import logging


class SynapseHealthSensor(BinarySensorEntity):
    def __init__(
        self,
        hass: HomeAssistant,
        hub: SynapseBridge,
    ):
        self.hass = hass
        self.bridge = hub
        self.logger = logging.getLogger(__name__)
        self._listen()

    @property
    def device_info(self) -> DeviceInfo:
        return self.bridge.device

    @property
    def entity_category(self):
        return EntityCategory.DIAGNOSTIC

    @property
    def name(self):
        return f"${self.bridge.config_entry.get("title")} Online"

    @property
    def is_on(self):
        return self.bridge.connected

    def _listen(self):
        self.async_on_remove(
          self.hass.bus.async_listen(
              self.event_name("heartbeat"),
              self._handle_heartbeat
          )
        )
        self.async_on_remove(
          self.hass.bus.async_listen(
              self.event_name("shutdown"),
              self._handle_shutdown
          )
        )
        self._reset_heartbeat_timer()

    @callback
    def _handle_shutdown(self, event):
        """Explicit shutdown events emitted by app"""
        self.logger.debug(f"{self.config_entry.get("app")} going offline")
        self.bridge.connected = False
        self.hass.bus.async_fire(self.event_name("health"))
        if self._heartbeat_timer:
            self._heartbeat_timer.cancel()
        self.async_schedule_update_ha_state(True)

    @callback
    def _mark_as_dead(self, event):
        """Timeout on heartbeat. Unexpected shutdown by app?"""
        if self.bridge.connected == False:
            return
        # He's dead Jim
        self.logger.info(f"{self.config_entry.get("app")} no heartbeat")
        self.bridge.connected = False
        self.hass.bus.async_fire(self.event_name("health"))
        self.async_schedule_update_ha_state(True)

    def _reset_heartbeat_timer(self):
        """Detected a heartbeat, wait for next"""
        if self._heartbeat_timer:
            self._heartbeat_timer.cancel()
        self._heartbeat_timer = self.hass.loop.call_later(30, self._mark_as_dead)

    @callback
    def _handle_heartbeat(self, event):
        """Handle heartbeat events."""
        self._reset_heartbeat_timer()
        if self.bridge.connected == True:
            return
        self.logger.debug(f"{self.config_entry.get("app")} online")
        self.bridge.connected = True
        self.hass.bus.async_fire(self.event_name("health"))
        self.async_schedule_update_ha_state(True)
