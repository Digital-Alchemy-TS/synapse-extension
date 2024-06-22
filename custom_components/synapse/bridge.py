import asyncio
from .const import DOMAIN, PLATFORMS
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.const import EntityCategory
from homeassistant.helpers.entity_platform import async_get_platforms
import aiohttp
import logging

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
        self.config_entry: SynapseApplication = config_entry
        self.hass = hass
        self.connected = False
        self.namespace = "digital_alchemy"
        self.app = self.config_entry.get("app")
        self._heartbeat_timer = None
        self.host = self.config_entry.get("host")
        self.device_list = {}

        # prefix http if not present
        if not self.host.startswith("http"):
            self.host = f"http://{self.host}"

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

    @property
    def hub_id(self) -> str:
        """ID reported by service"""
        return self.config_entry.get("unique_id")

    def event_name(self, event: str):
        """Standard format for event bus names to keep apps separate"""
        return f"{self.namespace}/{event}/{self.app}"

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
            await platform[0].async_add_entities([SynapseHealthSensor(self.hass, self)])

    async def reload(self):
        """Attach reload call to gather new metadata & update local info"""
        self.logger.debug("reloading")
        self.config_entry = await get_synapse_description(self.host)
        self.host = self.config_entry.get("host")

    async def refresh_data(self) -> SynapseApplication:
        """Reach back out w/ retries to the app and request new data"""
        for attempt in range(RETRIES):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"{self.host}/synapse") as response:
                        data = await response.json()
                        return data
            except Exception as e:
                if attempt < RETRIES - 1:
                    self.logger.debug("refresh retrying in 5 seconds")
                    await asyncio.sleep(5)
                else:
                    raise e

async def get_synapse_description(ip_port: str) -> SynapseApplication:
    if not ip_port.startswith("http"):
        ip_port = "http://" + ip_port

    url = f"{ip_port}/synapse"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            data = await response.json()
            return data
