from .bridge import SynapseBridge
from .const import DOMAIN

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback, HomeAssistant
from homeassistant.const import EntityCategory
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.components.number import NumberEntity
import logging


class SynapseAlarmControlPanelDefinition:
    attributes: object
    icon: str
    name: str
    suggested_object_id: str
    unique_id: str

    changed_by: str
    code_format: str
    supported_features: int
    code_arm_required: bool


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Setup the router platform."""
    bridge: SynapseBridge = hass.data[DOMAIN][config_entry.entry_id]
    entities = bridge.config_entry.get("number")
    async_add_entities(SynapseNumber(hass, bridge, entity) for entity in entities)


class SynapseNumber(NumberEntity):
    def __init__(
        self,
        hass: HomeAssistant,
        hub: SynapseBridge,
        entity: SynapseAlarmControlPanelDefinition,
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
    def changed_by(self):
        return self.entity.get("changed_by")

    @property
    def code_format(self):
        return self.entity.get("code_format")

    @property
    def supported_features(self):
        return self.entity.get("supported_features")

    @property
    def code_arm_required(self):
        return self.entity.get("code_arm_required")

    @callback
    async def async_arm_custom_bypass(self, **kwargs) -> None:
        self.hass.bus.async_fire(
            self.bridge.event_name("arm_custom_bypass"),
            {"unique_id": self.entity.get("unique_id"), **kwargs},
        )

    @callback
    async def async_trigger(self, **kwargs) -> None:
        self.hass.bus.async_fire(
            self.bridge.event_name("trigger"),
            {"unique_id": self.entity.get("unique_id"), **kwargs},
        )

    @callback
    async def async_arm_vacation(self, **kwargs) -> None:
        self.hass.bus.async_fire(
            self.bridge.event_name("arm_vacation"),
            {"unique_id": self.entity.get("unique_id"), **kwargs},
        )

    @callback
    async def async_arm_night(self, **kwargs) -> None:
        self.hass.bus.async_fire(
            self.bridge.event_name("arm_night"),
            {"unique_id": self.entity.get("unique_id"), **kwargs},
        )

    @callback
    async def async_arm_away(self, **kwargs) -> None:
        self.hass.bus.async_fire(
            self.bridge.event_name("arm_away"),
            {"unique_id": self.entity.get("unique_id"), **kwargs},
        )

    @callback
    async def async_arm_home(self, **kwargs) -> None:
        self.hass.bus.async_fire(
            self.bridge.event_name("arm_home"),
            {"unique_id": self.entity.get("unique_id"), **kwargs},
        )

    @callback
    async def async_disarm(self, **kwargs) -> None:
        self.hass.bus.async_fire(
            self.bridge.event_name("disarm"),
            {"unique_id": self.entity.get("unique_id"), **kwargs},
        )

    @callback
    async def async_toggle(self, **kwargs) -> None:
        """Handle the number press."""
        self.hass.bus.async_fire(
            self.bridge.event_name("toggle"),
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
