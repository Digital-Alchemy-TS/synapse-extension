import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback, HomeAssistant

from .const import DOMAIN, EVENT_NAMESPACE, APP_OFFLINE_DELAY
from .app_adapter import ApplicationAdapter

hashDict = {}

class SynapseBridge(ApplicationAdapter):
    """
    - Handle comms with the app (base class)
    - Provide helper methods for entities
    - Create online sensor
    - Tracks app heartbeat
    """
    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize the bridge"""
        super().__init__(hass, config_entry)
        self.logger = logging.getLogger(__name__)
        if config_entry is None:
            self.logger.error("application not online, reload integration after connecting")
            return

        self.namespace = EVENT_NAMESPACE
        self.online = False
        self._heartbeat_timer = None
        self._removals = []

        hass.data.setdefault(DOMAIN, {})[self.app_data.get("unique_id")] = self
        self._listen()

    async def async_cleanup(self) -> None:
        self._heartbeat_timer.cancel()
        for remove in self._removals:
            remove()

    def event_name(self, event: str) -> str:
        """Standard format for event bus names to keep apps separate"""
        return f"{self.namespace}/{event}/{self.app_data.get("app")}"

    def _listen(self) -> None:
        self._removals.append(
          self.hass.bus.async_listen(
              self.event_name("heartbeat"),
              self.handle_heartbeat
          )
        )
        self._removals.append(
          self.hass.bus.async_listen(
              self.event_name("shutdown"),
              self._handle_shutdown
          )
        )
        self._reset_heartbeat_timer()

    @callback
    def _handle_shutdown(self, event) -> None:
        """Explicit shutdown events emitted by app"""
        self.logger.info(f"{self.app_data.get("app")} going offline")
        self.online = False
        self.hass.bus.async_fire(self.event_name("health"))
        if self._heartbeat_timer:
            self._heartbeat_timer.cancel()

    @callback
    def _mark_as_dead(self, event=None) -> None:
        """Timeout on heartbeat"""
        if self.online == False:
            return
        # RIP
        self.logger.warning(f"{self.app_data.get("app")} lost heartbeat")
        self.online = False
        self.hass.bus.async_fire(self.event_name("health"))

    def _reset_heartbeat_timer(self) -> None:
        """Detected a heartbeat, wait for next"""
        if self._heartbeat_timer:
            self._heartbeat_timer.cancel()
        self._heartbeat_timer = self.hass.loop.call_later(APP_OFFLINE_DELAY, self._mark_as_dead)

    @callback
    def handle_heartbeat(self, event) -> None:
        """
        Handle heartbeat events.
        Marks the app back online & kicks off bg timer for healthcheck
        """
        self._reset_heartbeat_timer()
        if self.online == True:
            return

        if event is not None:
            entry_id = self.config_entry.entry_id
            self.hass.async_create_task(
                self.hass.config_entries.async_reload(entry_id)
            )

        self.logger.debug(f"{self.app_data.get("app")} restored heartbeat")
        self.online = True
        self.hass.bus.async_fire(self.event_name("health"))
