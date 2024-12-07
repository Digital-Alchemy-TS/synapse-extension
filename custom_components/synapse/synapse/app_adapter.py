import asyncio
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_CONFIGURATION_URL,
    ATTR_HW_VERSION,
    ATTR_IDENTIFIERS,
    ATTR_MANUFACTURER,
    ATTR_MODEL,
    ATTR_NAME,
    ATTR_SERIAL_NUMBER,
    ATTR_SUGGESTED_AREA,
    ATTR_SW_VERSION,
    ATTR_VIA_DEVICE,
)
from homeassistant.core import callback, HomeAssistant
from homeassistant.helpers import entity_registry as er, device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo

from .const import (
    DOMAIN,
    PLATFORMS,
    EVENT_NAMESPACE,
    SynapseApplication,
    SynapseMetadata,
    QUERY_TIMEOUT,
    RETRIES,
    RETRY_DELAY,
)
from .helpers import hex_to_object

class ApplicationAdapter:
    """Handle the communications with a single connected app"""
    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        # Mental note: property managed by health sensor 🤦‍♀️
        # Need to figure out how to move the code here and respect async_on_remove
        self.logger = logging.getLogger(__name__)
        self.app = None
        self.config_entry = config_entry
        self.device = None
        self.device_list = None
        self.hass = hass
        self.health = None
        self.app_data: SynapseApplication = config_entry.data
        if self.app_data is not None:
          self.app = self.app_data.get("app")


    def format_device_info(self, device = None):
        """Translate between synapse data objects and hass device info"""
        device = device or self.app_data.get("device")
        return {
            ATTR_CONFIGURATION_URL: device.get("configuration_url"),
            ATTR_HW_VERSION: device.get("hw_version"),
            ATTR_IDENTIFIERS: {
                (DOMAIN, self.app_data.get("unique_id"))
            },
            ATTR_MANUFACTURER: device.get("manufacturer"),
            ATTR_MODEL: device.get("model"),
            ATTR_NAME: device.get("name"),
            ATTR_SERIAL_NUMBER: device.get("serial_number"),
            ATTR_SUGGESTED_AREA: device.get("suggested_area"),
            ATTR_SW_VERSION: device.get("sw_version"),
        }

    async def async_reload(self) -> None:
        """Attach reload call to gather new metadata & update local info"""
        self.logger.debug("info")

        # retry a few times - apps attempt reconnect on an interval
        # recent boots will have a short delay before the app can successfully reconnect
        data = await self._async_fetch_state(self.app)
        for x in range(0, RETRIES):
            if data is not None:
                self.logger.debug(f"{self.app} success")
                break
            self.logger.debug(f"{self.app} wait {RETRY_DELAY}s & retry: {x}")
            await asyncio.sleep(RETRY_DELAY)
            data = await self._async_fetch_state(self.app)

        if data is None:
            self.logger.warning("no response, is app connected?")
            return

        self.app_data = data
        self._refresh_devices()
        self._refresh_entities()

        # this counts as a heartbeat
        self.handle_heartbeat(None)

    def _refresh_devices(self) -> None:
        """Parse through the incoming payload, and set up devices to match"""
        self.device_list = {}
        device_registry = dr.async_get(self.hass)

        # create / update base device
        params = self.format_device_info()
        self.device = DeviceInfo(**params)
        device = device_registry.async_get_or_create(
            config_entry_id=self.config_entry.entry_id,
            **params
        )

        # if the app declares secondary devices, register them also
        # use via_device to create an association with the base
        secondary_devices: list[SynapseMetadata] = self.app_data.get("secondary_devices",[])

        found = []
        for device in secondary_devices:
            self.logger.debug(f"secondary device {device.get("name")} => {device.get("name")}")

            # create params
            params = self.format_device_info(device)
            params[ATTR_VIA_DEVICE] = (DOMAIN, self.app_data.get("unique_id"))

            # work with registry
            self.device_list[device.get("unique_id")] = DeviceInfo(**params)
            device = device_registry.async_get_or_create(config_entry_id=self.config_entry.entry_id,**params)

            # track as valid id
            found.append(device.id)

        remove = []
        for _, entry in device_registry.devices.items():
            if entry.primary_config_entry == self.config_entry.entry_id:
                if entry.id not in found:
                    remove.append(entry.id)

        for device_id in remove:
            device_registry.async_remove_device(device_id)

    def _refresh_entities(self) -> None:
        """
        Search out entities to remove: take the list of entities in the incoming payload, diff against current list
        Any unique id that currently exists that shouldn't gets a remove
        """
        entity_registry = er.async_get(self.hass)
        # repeat logic for all domains
        for domain in PLATFORMS:
            incoming_list = self.app_data.get(domain)
            if incoming_list is None:
                continue

            found = []
            for incoming in incoming_list:
                found.append(incoming.get("unique_id"))

            # removing from inside the loop blows things up
            # create list to run as follow up
            remove = []
            for entity_id, entry in entity_registry.entities.items():
                if entry.platform == "synapse" and entry.config_entry_id == self.config_entry.entry_id:
                    # match based on unique_id, rm by entity_id
                    if entry.unique_id not in found:
                        remove.append(entry.entity_id)

            for entity_id in remove:
                entity_registry.async_remove(entity_id)

    async def _async_fetch_state(self, app: str) -> SynapseApplication:
        """Attach reload call to gather new metadata & update local info"""
        self.hass.bus.async_fire(f"{EVENT_NAMESPACE}/discovery/{app}")
        hex_str = await self._wait_for_reload_reply(f"{EVENT_NAMESPACE}/identify/{app}")
        if hex_str is None:
            return None
        return hex_to_object(hex_str)

    async def handle_heartbeat(self) -> None:
        """Overridden by bridge"""

    async def _wait_for_reload_reply(self, event_name) -> str:
        """
        Wait for the app to reply, then return.
        Contains short timeout to race reply and return None
        """
        future = asyncio.Future()
        @callback
        def handle_event(event):
            if not future.done():
                future.set_result(event.data["compressed"]) # <<< success value
        self.hass.loop.call_soon_threadsafe(
            self.hass.bus.async_listen_once,
            event_name,
            handle_event
        )
        try:
            return await asyncio.wait_for(future, timeout=QUERY_TIMEOUT)
        except asyncio.TimeoutError:
            return None # <<< error value
