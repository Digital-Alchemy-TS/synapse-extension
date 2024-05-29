from .bridge import SynapseBridge
from .const import DOMAIN

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback, HomeAssistant
from homeassistant.const import EntityCategory
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.components.valve import ValveEntity
import logging


class SynapseValveDefinition:
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
    entities = bridge.config_entry.get("valve")
    async_add_entities(SynapseValve(hass, bridge, entity) for entity in entities)


class SynapseValve(ValveEntity):
    def __init__(
        self,
        hass: HomeAssistant,
        hub: SynapseBridge,
        entity: SynapseValveDefinition,
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
    def current_valve_position(self):
        return self.entity.get("current_valve_position")

    @property
    def is_closed(self):
        return self.entity.get("is_closed")

    @property
    def is_opening(self):
        return self.entity.get("is_opening")

    @property
    def reports_position(self):
        return self.entity.get("reports_position")

    @property
    def device_class(self):
        return self.entity.get("device_class")

    @property
    def is_closing(self):
        return self.entity.get("is_closing")

    @property
    def supported_features(self):
        return self.entity.get("supported_features")

    @callback
    async def async_open_valve(self, **kwargs) -> None:
        """Proxy the request to open the valve."""
        self.hass.bus.async_fire(
            self.bridge.event_name("open_valve"),
            {"unique_id": self.entity.get("unique_id"), **kwargs},
        )

    @callback
    async def async_close_valve(self, **kwargs) -> None:
        """Proxy the request to close the valve."""
        self.hass.bus.async_fire(
            self.bridge.event_name("close_valve"),
            {"unique_id": self.entity.get("unique_id"), **kwargs},
        )

    @callback
    async def async_set_valve_position(self, position: float, **kwargs) -> None:
        """Proxy the request to set the valve position."""
        self.hass.bus.async_fire(
            self.bridge.event_name("set_valve_position"),
            {"unique_id": self.entity.get("unique_id"), "position": position, **kwargs},
        )

    @callback
    async def async_stop_valve(self, **kwargs) -> None:
        """Proxy the request to stop the valve."""
        self.hass.bus.async_fire(
            self.bridge.event_name("stop_valve"),
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
