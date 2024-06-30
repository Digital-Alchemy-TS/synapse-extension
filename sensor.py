from .bridge import SynapseBridge
from .const import DOMAIN

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import callback, HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
import logging


class SynapseSensorDefinition:
    attributes: object
    capability_attributes: int
    device_class: str
    entity_category: str
    icon: str
    unique_id: str
    name: str
    state: str | int
    state_class: str
    native_unit_of_measurement: str
    suggested_object_id: str
    supported_features: int
    translation_key: str
    suggested_display_precision: int
    last_reset: str
    options: list[str]
    unit_of_measurement: str


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Setup the router platform."""
    bridge: SynapseBridge = hass.data[DOMAIN][config_entry.entry_id]
    entities = bridge.config_entry.get("sensor")
    if entities is not None:
      async_add_entities(SynapseSensor(hass, bridge, entity) for entity in entities)


class SynapseSensor(SensorEntity):
    def __init__(
        self, hass: HomeAssistant, hub: SynapseBridge, entity: SynapseSensorDefinition
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
        declared = self.entity.get("device_id", "")
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
            return EntityCategory.CONFIG
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
        return self.bridge.connected()

    # domain specific
    @property
    def state(self):
        return self.entity.get("state")

    @property
    def state_class(self):
        return self.entity.get("state_class")

    @property
    def suggested_display_precision(self):
        return self.entity.get("suggested_display_precision")

    @property
    def capability_attributes(self):
        return self.entity.get("capability_attributes")

    @property
    def native_unit_of_measurement(self):
        return self.entity.get("native_unit_of_measurement")

    @property
    def supported_features(self):
        return self.entity.get("supported_features")

    @property
    def device_class(self):
        return self.entity.get("device_class")

    @property
    def unit_of_measurement(self):
        return self.entity.get("unit_of_measurement")

    @property
    def options(self):
        return self.entity.get("options")

    @property
    def last_reset(self):
        return self.entity.get("last_reset")

    # helper methods
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
