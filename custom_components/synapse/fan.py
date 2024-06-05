from .bridge import SynapseBridge
from .const import DOMAIN

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback, HomeAssistant
from homeassistant.const import EntityCategory
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.components.fan import FanEntity
import logging


class SynapseFanDefinition:
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
    entities = bridge.config_entry.get("fan")
    if entities is not None:
      async_add_entities(SynapseFan(hass, bridge, entity) for entity in entities)


class SynapseFan(FanEntity):
    def __init__(
        self,
        hass: HomeAssistant,
        hub: SynapseBridge,
        entity: SynapseFanDefinition,
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
        return self.bridge.connected

    # domain specific
    @property
    def current_direction(self):
        return self.entity.get("current_direction")

    @property
    def is_on(self):
        return self.entity.get("is_on")

    @property
    def oscillating(self):
        return self.entity.get("oscillating")

    @property
    def percentage(self):
        return self.entity.get("percentage")

    @property
    def preset_mode(self):
        return self.entity.get("preset_mode")

    @property
    def preset_modes(self):
        return self.entity.get("preset_modes")

    @property
    def speed_count(self):
        return self.entity.get("speed_count")

    @callback
    async def async_set_direction(self, direction: str, **kwargs) -> None:
        """Proxy the request to set direction."""
        self.hass.bus.async_fire(
            self.bridge.event_name("set_direction"),
            {
                "unique_id": self.entity.get("unique_id"),
                "direction": direction,
                **kwargs,
            },
        )

    @callback
    async def async_set_preset_mode(self, preset_mode: str, **kwargs) -> None:
        """Proxy the request to set preset mode."""
        self.hass.bus.async_fire(
            self.bridge.event_name("set_preset_mode"),
            {
                "unique_id": self.entity.get("unique_id"),
                "preset_mode": preset_mode,
                **kwargs,
            },
        )

    @callback
    async def async_set_percentage(self, percentage: int, **kwargs) -> None:
        """Proxy the request to set percentage."""
        self.hass.bus.async_fire(
            self.bridge.event_name("set_percentage"),
            {
                "unique_id": self.entity.get("unique_id"),
                "percentage": percentage,
                **kwargs,
            },
        )

    @callback
    async def async_turn_on(self, **kwargs) -> None:
        """Proxy the request to turn the entity on."""
        self.hass.bus.async_fire(
            self.bridge.event_name("turn_on"),
            {"unique_id": self.entity.get("unique_id"), **kwargs},
        )

    @callback
    async def async_turn_off(self, **kwargs) -> None:
        """Proxy the request to turn the entity off."""
        self.hass.bus.async_fire(
            self.bridge.event_name("turn_off"),
            {"unique_id": self.entity.get("unique_id"), **kwargs},
        )

    @callback
    async def async_toggle(self, **kwargs) -> None:
        """Proxy the request to toggle the entity."""
        self.hass.bus.async_fire(
            self.bridge.event_name("toggle"),
            {"unique_id": self.entity.get("unique_id"), **kwargs},
        )

    @callback
    async def async_oscillate(self, oscillating: bool, **kwargs) -> None:
        """Proxy the request to set oscillating."""
        self.hass.bus.async_fire(
            self.bridge.event_name("oscillate"),
            {
                "unique_id": self.entity.get("unique_id"),
                "oscillating": oscillating,
                **kwargs,
            },
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
