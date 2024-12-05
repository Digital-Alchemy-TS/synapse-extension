import asyncio
from .const import DOMAIN, PLATFORMS, EVENT_NAMESPACE, SynapseApplication, SynapseMetadata
from .health import SynapseHealthSensor
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er, device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.const import EntityCategory
from homeassistant.helpers.entity_platform import async_get_platforms
import aiohttp
import logging
import gzip
import json
import io
import binascii

from homeassistant.const import (
    ATTR_CONNECTIONS,
    ATTR_IDENTIFIERS,
    ATTR_MANUFACTURER,
    ATTR_MODEL,
    ATTR_NAME,
    ATTR_SUGGESTED_AREA,
    ATTR_SW_VERSION,
    ATTR_HW_VERSION,
    ATTR_CONFIGURATION_URL,
    ATTR_SERIAL_NUMBER,
    ATTR_VIA_DEVICE,
)

RETRIES = 5

class SynapseBridge:
    """Manages a single synapse application"""

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize the system"""
        # variables
        self.logger = logging.getLogger(__name__)
        if config_entry is None:
            self.logger.error("application not online, reload integration after connecting")
            return
        self.config_entry = config_entry
        self.config_data: SynapseApplication = config_entry.data

        device_registry = dr.async_get(hass)
        self.hass = hass
        self.namespace = EVENT_NAMESPACE

        if self.config_data is not None:
          self.app = self.config_data.get("app")

        self.health: SynapseHealthSensor = None
        self.device_list = {}

        params = self.format_info()
        self.device = DeviceInfo(**params)
        device_registry.async_get_or_create(
            config_entry_id=self.config_entry.entry_id,
            **params
        )
        hass.data.setdefault(DOMAIN, {})[self.config_data.get("unique_id")] = self

        secondary_devices: list[SynapseMetadata] = self.config_data.get("secondary_devices",[])

        for device in secondary_devices:
            self.logger.debug(f"secondary device {device.get("name")} => {device.get("name")}")
            params = self.format_info(device)
            params[ATTR_VIA_DEVICE] = (DOMAIN, self.config_data.get("unique_id"))

            self.device_list[device.get("unique_id")] = DeviceInfo(**params)
            device_registry.async_get_or_create(config_entry_id=self.config_entry.entry_id,**params)

    def format_info(self, device = None):
        device = device or self.config_data.get("device")
        return {
            ATTR_IDENTIFIERS: {
                (DOMAIN, self.config_data.get("unique_id"))
            },
            ATTR_CONFIGURATION_URL: device.get("configuration_url"),
            ATTR_MANUFACTURER: device.get("manufacturer"),
            ATTR_MODEL: device.get("model"),
            ATTR_NAME: device.get("name"),
            ATTR_HW_VERSION: device.get("hw_version"),
            ATTR_SERIAL_NUMBER: device.get("serial_number"),
            ATTR_SUGGESTED_AREA: device.get("suggested_area"),
            ATTR_SW_VERSION: device.get("sw_version"),
        }

    def event_name(self, event: str):
        """Standard format for event bus names to keep apps separate"""
        return f"{self.namespace}/{event}/{self.config_data.get("app")}"

    @property
    def hub_id(self) -> str:
        """ID reported by service"""
        return self.config_data.get("unique_id")

    def connected(self) -> bool:
        """Is the bridge currently online"""
        if self.health is not None:
            return self.health.online
        return False

    async def import_data(self, entry: ConfigEntry):
        """Process the current entity data, generating new entities / removing old ones"""
        entity_registry = er.async_get(self.hass)
        found = []
        # * Process entities
        for domain in PLATFORMS:
            incoming_list = self.config_data.get(domain)
            if incoming_list is None:
                continue
            self.logger.info(f"{self.config_data.get("app")}:{domain} => {len(incoming_list)} entries")

            for incoming in incoming_list:
                found.append(incoming.get("unique_id"))

            remove = []
            for entity_id, entry in entity_registry.entities.items():
                if entry.platform == "synapse" and entry.config_entry_id == self.config_entry.entry_id:
                    if entry.unique_id not in found:
                        remove.append(entry.entity_id)

            for entity_id in remove:
                entity_registry.async_remove(entity_id)

    async def async_setup_health_sensor(self):
        """Setup the health sensor entity."""
        platform = async_get_platforms(self.hass, DOMAIN)
        # if platform:
        #     self.health = SynapseHealthSensor(self.hass, self.namespace, self.device, self.config_entry)
        #     await platform[0].async_add_entities([self.health])

    async def reload(self):
        """Attach reload call to gather new metadata & update local info"""
        self.logger.debug("reloading")

        data = await self.identify(self.app)
        if data is None:
            self.logger.warn("no response, is app connected?")
            return
        # Update local info
        self.config_data = data

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
