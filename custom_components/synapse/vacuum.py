from .bridge import SynapseBridge
from .const import DOMAIN

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback, HomeAssistant
from homeassistant.const import EntityCategory
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.components.vacuum import VacuumEntity
import logging


class SynapseVacuumDefinition:
    attributes: object
    device_class: str
    entity_category: str
    icon: str
    unique_id: str
    name: str
    state: str | int
    suggested_object_id: str
    supported_features: int
    translation_key: str


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Setup the router platform."""
    bridge: SynapseBridge = hass.data[DOMAIN][config_entry.entry_id]
    entities = bridge.config_entry.get("vacuum")
    if entities is not None:
      async_add_entities(SynapseVacuum(hass, bridge, entity) for entity in entities)


class SynapseVacuum(VacuumEntity):
    def __init__(
        self,
        hass: HomeAssistant,
        hub: SynapseBridge,
        entity: SynapseVacuumDefinition,
    ):
        self.hass = hass
        self.bridge = hub
        self.entity = entity
        self.logger = logging.getLogger(__name__)
        self._listen()

    # common to all
    @property
    def device_info(self) -> DeviceInfo:
        """Return device registry information for this entity."""
        declared = self.get("device_id")
        if len(declared) > 0:
            return self.bridge.device_list[declared]
        return self.bridge.device

    @property
    def unique_id(self):
        return self.entity.get("unique_id")

    @property
    def suggested_object_id(self):
        return self.entity.get("suggested_object_id")

    @property
    def translation_key(self):
        return self.entity.get("translation_key")

    @property
    def icon(self):
        return self.entity.get("icon")

    @property
    def extra_state_attributes(self):
        return self.entity.get("attributes") or {}

    @property
    def entity_category(self):
        if self.entity.get("entity_category") == "config":
            return EntityCategory.config
        if self.entity.get("entity_category") == "diagnostic":
            return EntityCategory.DIAGNOSTIC
        return None

    @property
    def name(self):
        return self.entity.get("name")

    @property
    def suggested_area_id(self):
        return self.entity.get("area_id")

    @property
    def labels(self):
        return self.entity.get("labels")

    @property
    def available(self):
        return self.bridge.connected

    # domain specific
    @property
    def battery_level(self):
        return self.entity.get("battery_level")

    @property
    def fan_speed(self):
        return self.entity.get("fan_speed")

    @property
    def fan_speed_list(self):
        return self.entity.get("fan_speed_list")

    @property
    def supported_features(self):
        return self.entity.get("supported_features")

    @callback
    async def async_clean_spot(self, **kwargs) -> None:
        """Proxy the request to clean a spot."""
        self.hass.bus.async_fire(
            self.bridge.event_name("clean_spot"),
            {"unique_id": self.entity.get("unique_id"), **kwargs},
        )

    @callback
    async def async_locate(self, **kwargs) -> None:
        """Proxy the request to locate."""
        self.hass.bus.async_fire(
            self.bridge.event_name("locate"),
            {"unique_id": self.entity.get("unique_id"), **kwargs},
        )

    @callback
    async def async_pause(self, **kwargs) -> None:
        """Proxy the request to pause."""
        self.hass.bus.async_fire(
            self.bridge.event_name("pause"),
            {"unique_id": self.entity.get("unique_id"), **kwargs},
        )

    @callback
    async def async_return_to_base(self, **kwargs) -> None:
        """Proxy the request to return to base."""
        self.hass.bus.async_fire(
            self.bridge.event_name("return_to_base"),
            {"unique_id": self.entity.get("unique_id"), **kwargs},
        )

    @callback
    async def async_send_command(self, command: str, **kwargs) -> None:
        """Proxy the request to send a command."""
        self.hass.bus.async_fire(
            self.bridge.event_name("send_command"),
            {"unique_id": self.entity.get("unique_id"), "command": command, **kwargs},
        )

    @callback
    async def async_set_fan_speed(self, fan_speed: str, **kwargs) -> None:
        """Proxy the request to set fan speed."""
        self.hass.bus.async_fire(
            self.bridge.event_name("set_fan_speed"),
            {
                "unique_id": self.entity.get("unique_id"),
                "fan_speed": fan_speed,
                **kwargs,
            },
        )

    @callback
    async def async_start(self, **kwargs) -> None:
        """Proxy the request to start."""
        self.hass.bus.async_fire(
            self.bridge.event_name("start"),
            {"unique_id": self.entity.get("unique_id"), **kwargs},
        )

    @callback
    async def async_stop(self, **kwargs) -> None:
        """Proxy the request to stop."""
        self.hass.bus.async_fire(
            self.bridge.event_name("stop"),
            {"unique_id": self.entity.get("unique_id"), **kwargs},
        )

    def _listen(self):
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

    @callback
    def _handle_entity_update(self, event):
        if event.data.get("unique_id") == self.entity.get("unique_id"):
            self.entity = event.data.get("data")
            self.async_write_ha_state()

    @callback
    async def _handle_availability_update(self, event):
        """Handle health status update."""
        self.async_schedule_update_ha_state(True)
