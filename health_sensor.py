from homeassistant.core import callback, HomeAssistant
from homeassistant.components.binary_sensor import BinarySensorEntity
from .const import DOMAIN
from .bridge import SynapseBridge
import logging

_LOGGER = logging.getLogger(__name__)


class HealthCheckSensor:
    """Representation of a Health Check Binary Sensor."""

    def __init__(self, hub: SynapseBridge):
        """Initialize the health check sensor."""
        hass = hub._hass
        self.hass = hass

        if "health_status" not in hass.data[DOMAIN]:
            hass.data[DOMAIN]["health_status"] = {}

        self._hub = hub
        self.hass.data[DOMAIN]["health_status"][hub.app] = False
        _LOGGER.info(f"creating health check sensor for {hub.app}")

        self._name = f"{hub.app} is online"
        self._id = f"{hub.app}_is_online"
        self._heartbeat_timer = None

    @property
    def name(self):
        """Return the name of the binary sensor."""
        return self._name

    @property
    def unique_id(self):
        """Return a unique identifier for this button."""
        return self._id

    @property
    def is_on(self):
        """Return true if the binary sensor is on (indicating 'alive')."""
        return self.hass.data[DOMAIN]["health_status"][self._app]
