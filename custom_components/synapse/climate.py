from .bridge import SynapseBridge
from .const import DOMAIN

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback, HomeAssistant
from homeassistant.const import EntityCategory
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.components.climate import ClimateEntity
import logging


class SynapseClimateDefinition:
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
    entities = bridge.config_entry.get("climate")
    if entities is not None:
      async_add_entities(SynapseClimate(hass, bridge, entity) for entity in entities)


class SynapseClimate(ClimateEntity):
    def __init__(
        self,
        hass: HomeAssistant,
        hub: SynapseBridge,
        entity: SynapseClimateDefinition,
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
    def current_humidity(self):
        return self.entity.get("current_humidity")

    @property
    def current_temperature(self):
        return self.entity.get("current_temperature")

    @property
    def fan_mode(self):
        return self.entity.get("fan_mode")

    @property
    def fan_modes(self):
        return self.entity.get("fan_modes")

    @property
    def hvac_action(self):
        return self.entity.get("hvac_action")

    @property
    def hvac_mode(self):
        return self.entity.get("hvac_mode")

    @property
    def hvac_modes(self):
        return self.entity.get("hvac_modes")

    @property
    def max_humidity(self):
        return self.entity.get("max_humidity")

    @property
    def max_temp(self):
        return self.entity.get("max_temp")

    @property
    def min_humidity(self):
        return self.entity.get("min_humidity")

    @property
    def min_temp(self):
        return self.entity.get("min_temp")

    @property
    def precision(self):
        return self.entity.get("precision")

    @property
    def preset_mode(self):
        return self.entity.get("preset_mode")

    @property
    def preset_modes(self):
        return self.entity.get("preset_modes")

    @property
    def swing_mode(self):
        return self.entity.get("swing_mode")

    @property
    def swing_modes(self):
        return self.entity.get("swing_modes")

    @property
    def target_humidity(self):
        return self.entity.get("target_humidity")

    @property
    def target_temperature_high(self):
        return self.entity.get("target_temperature_high")

    @property
    def target_temperature_low(self):
        return self.entity.get("target_temperature_low")

    @property
    def target_temperature_step(self):
        return self.entity.get("target_temperature_step")

    @property
    def target_temperature(self):
        return self.entity.get("target_temperature")

    @property
    def temperature_unit(self):
        return self.entity.get("temperature_unit")

    @callback
    async def async_set_hvac_mode(self, hvac_mode: str, **kwargs) -> None:
        """Proxy the request to set HVAC mode."""
        self.hass.bus.async_fire(
            self.bridge.event_name("set_hvac_mode"),
            {
                "unique_id": self.entity.get("unique_id"),
                "hvac_mode": hvac_mode,
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
    async def async_set_fan_mode(self, fan_mode: str, **kwargs) -> None:
        """Proxy the request to set fan mode."""
        self.hass.bus.async_fire(
            self.bridge.event_name("set_fan_mode"),
            {"unique_id": self.entity.get("unique_id"), "fan_mode": fan_mode, **kwargs},
        )

    @callback
    async def async_set_humidity(self, humidity: float, **kwargs) -> None:
        """Proxy the request to set humidity."""
        self.hass.bus.async_fire(
            self.bridge.event_name("set_humidity"),
            {"unique_id": self.entity.get("unique_id"), "humidity": humidity, **kwargs},
        )

    @callback
    async def async_set_swing_mode(self, swing_mode: str, **kwargs) -> None:
        """Proxy the request to set swing mode."""
        self.hass.bus.async_fire(
            self.bridge.event_name("set_swing_mode"),
            {
                "unique_id": self.entity.get("unique_id"),
                "swing_mode": swing_mode,
                **kwargs,
            },
        )

    @callback
    async def async_set_temperature(self, temperature: float, **kwargs) -> None:
        """Proxy the request to set temperature."""
        self.hass.bus.async_fire(
            self.bridge.event_name("set_temperature"),
            {
                "unique_id": self.entity.get("unique_id"),
                "temperature": temperature,
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
