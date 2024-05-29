from .bridge import SynapseBridge
from .const import DOMAIN

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback, HomeAssistant
from homeassistant.const import EntityCategory
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.components.camera import CameraEntity
import logging


class SynapseCameraDefinition:
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
    entities = bridge.config_entry.get("camera")
    async_add_entities(SynapseCamera(hass, bridge, entity) for entity in entities)


class SynapseCamera(CameraEntity):
    def __init__(
        self,
        hass: HomeAssistant,
        hub: SynapseBridge,
        entity: SynapseCameraDefinition,
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
    def brand(self):
        return self.entity.get("brand")

    @property
    def frame_interval(self):
        return self.entity.get("frame_interval")

    @property
    def frontend_stream_type(self):
        return self.entity.get("frontend_stream_type")

    @property
    def is_on(self):
        return self.entity.get("is_on")

    @property
    def is_recording(self):
        return self.entity.get("is_recording")

    @property
    def is_streaming(self):
        return self.entity.get("is_streaming")

    @property
    def model(self):
        return self.entity.get("model")

    @property
    def motion_detection_enabled(self):
        return self.entity.get("motion_detection_enabled")

    @property
    def use_stream_for_stills(self):
        return self.entity.get("use_stream_for_stills")

    @callback
    async def async_turn_on(self, **kwargs) -> None:
        """Turn the entity on."""
        self.hass.bus.async_fire(
            self.bridge.event_name("turn_on"),
            {"unique_id": self.entity.get("unique_id"), **kwargs},
        )

    @callback
    async def async_turn_off(self, **kwargs) -> None:
        """Turn the entity off."""
        self.hass.bus.async_fire(
            self.bridge.event_name("turn_off"),
            {"unique_id": self.entity.get("unique_id"), **kwargs},
        )

    @callback
    async def async_enable_motion_detection(self, **kwargs) -> None:
        """Enable motion detection."""
        self.hass.bus.async_fire(
            self.bridge.event_name("enable_motion_detection"),
            {"unique_id": self.entity.get("unique_id"), **kwargs},
        )

    @callback
    async def async_disable_motion_detection(self, **kwargs) -> None:
        """Disable motion detection."""
        self.hass.bus.async_fire(
            self.bridge.event_name("disable_motion_detection"),
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
