import asyncio
from .const import DOMAIN, PLATFORMS, EVENT_NAMESPACE
from .health import SynapseHealthSensor
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.const import EntityCategory
from homeassistant.helpers.entity_platform import async_get_platforms
import aiohttp
import logging
import gzip
import json
import io
import binascii

RETRIES = 5


class SynapseMetadata:
    """Entity device information for device registry."""
    configuration_url: str | None
    default_manufacturer: str
    default_model: str
    default_name: str
    unique_id: str | None
    manufacturer: str | None
    model: str | None
    name: str | None
    serial_number: str | None
    suggested_area: str | None
    sw_version: str | None
    hw_version: str | None

class SynapseApplication:
    """Description of application state"""
    hostname: str
    name: str
    unique_id: str
    username: str
    version: str
    app: str
    device: SynapseMetadata
    hash: str
    sensor: list[object]
    secondary_devices: list[SynapseMetadata]
    boot: str
    title: str

class SynapseBridge:
    """Manages a single synapse application"""

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize the system"""
        # variables
        self.logger = logging.getLogger(__name__)
        if config_entry is None:
            self.logger.error("application not online, reload integration after connecting")
            return
        self.config_entry: SynapseApplication = config_entry
        self.hass = hass
        self.namespace = EVENT_NAMESPACE

        if config_entry is not None:
          self.app = config_entry.get("app")

        self.health: SynapseHealthSensor = None
        self.device_list = {}

        device = config_entry.get("device")
        unique_id = config_entry.get("unique_id")

        # hass
        hass.data.setdefault(DOMAIN, {})[unique_id] = self
        name = device.get("name")

        # device for entities to consume
        self.device = DeviceInfo(
            identifiers={
                (DOMAIN, self.config_entry.get("unique_id"))
            },
            configuration_url=device.get("configuration_url"),
            manufacturer=device.get("manufacturer"),
            model=device.get("model"),
            name=name,
            hw_version=device.get("hw_version"),
            serial_number=device.get("serial_number"),
            suggested_area=device.get("suggested_area"),
            sw_version=device.get("sw_version"),
        )

        secondary_devices: list[SynapseMetadata] = self.config_entry.get("secondary_devices",[])

        for device in secondary_devices:
            self.logger.debug(f"secondary device {name} => {device.get("name")}")
            self.device_list[device.get("unique_id")] = DeviceInfo(
                via_device=(DOMAIN, self.config_entry.get("unique_id")),
                identifiers={
                    (DOMAIN, device.get("unique_id")),
                },
                configuration_url=device.get("configuration_url"),
                manufacturer=device.get("manufacturer"),
                model=device.get("model"),
                name=device.get("name"),
                hw_version=device.get("hw_version"),
                serial_number=device.get("serial_number"),
                suggested_area=device.get("suggested_area"),
                sw_version=device.get("sw_version"),
            )


    def event_name(self, event: str):
        """Standard format for event bus names to keep apps separate"""
        return f"{self.namespace}/{event}/{self.config_entry.get("app")}"

    @property
    def hub_id(self) -> str:
        """ID reported by service"""
        return self.config_entry.get("unique_id")

    def connected(self) -> bool:
        """Is the bridge currently online"""
        if self.health is not None:
            return self.health.online
        return False

    async def import_data(self):
        """Process the current entity data, generating new entities / removing old ones"""
        entity_registry = er.async_get(self.hass)
        # * Process entities
        for domain in PLATFORMS:
            incoming_list = self.config_entry.get(domain)
            if incoming_list is None:
                continue
            self.logger.info(f"{self.config_entry.get("app")}:{domain} => {len(incoming_list)} entries")

            for incoming in incoming_list:
                category = EntityCategory.CONFIG if incoming.get("entity_category", None) == "config" else EntityCategory.DIAGNOSTIC
                entity_registry.async_get_or_create(
                    domain=domain,
                    platform="synapse",
                    unique_id=incoming.get("id"),
                    suggested_object_id=incoming.get("suggested_object_id", None),
                    entity_category=category,
                    unit_of_measurement=incoming.get("unit_of_measurement"),
                    supported_features=incoming.get("supported_features"),
                    original_device_class=incoming.get("device_class"),
                    original_icon=incoming.get("icon"),
                    original_name=incoming.get("name")
                )


            # # * Remove entities not in the update
            # for entity_id in current_ids - updated_id_list:
            #     removal = hass.data[DOMAIN][service].pop(entity_id)
            #     self.logger.debug(f"{app}:{service} remove {removal._name}")
            #     hass.async_create_task(removal.async_remove())

    async def async_setup_health_sensor(self):
        """Setup the health sensor entity."""
        platform = async_get_platforms(self.hass, DOMAIN)
        if platform:
            self.health = SynapseHealthSensor(self.hass, self.namespace, self.device, self.config_entry)
            await platform[0].async_add_entities([self.health])

    async def reload(self):
        """Attach reload call to gather new metadata & update local info"""
        self.logger.debug("reloading")

        data = await self.identify(self.app)
        if data is None:
            self.logger.warn("no response, is app connected?")
            return
        # Update local info
        self.config_entry = data

    async def wait_for_reload_reply(self, event_name):
        """Wait for reload reply event with hex string data payload, with a timeout of 2 seconds"""
        future = asyncio.Future()

        def handle_event(event):
            if not future.done():
                future.set_result(event.data['compressed'])

        self.hass.loop.call_soon_threadsafe(
            self.hass.bus.async_listen_once,
            event_name,
            handle_event
        )

        try:
            return await asyncio.wait_for(future, timeout=0.5)
        except asyncio.TimeoutError:
            return None

    async def identify(self, app: str):
        """Attach reload call to gather new metadata & update local info"""

        # Send reload request
        self.hass.bus.async_fire(f"{EVENT_NAMESPACE}/discovery/{app}")

        # Wait for incoming reply
        hex_str = await self.wait_for_reload_reply(f"{EVENT_NAMESPACE}/identify/{app}")

        if hex_str is None:
            return None

        # Convert hex string to object
        return hex_to_object(hex_str)


def hex_to_object(hex_str: str):
    compressed_data = binascii.unhexlify(hex_str)
    with gzip.GzipFile(fileobj=io.BytesIO(compressed_data)) as f:
        json_str = f.read().decode('utf-8')
    return json.loads(json_str)
