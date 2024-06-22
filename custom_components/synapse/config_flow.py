"""Config flow for Digital Alchemy Synapse."""

from __future__ import annotations
from typing import Any
import voluptuous as vol

from homeassistant.components import dhcp, ssdp
from homeassistant.config_entries import (
    SOURCE_REAUTH,
    ConfigFlow,
    ConfigEntry,
    ConfigEntryState,
)
from homeassistant.const import (
    CONF_ALIAS,
    CONF_DEVICE,
    CONF_HOST,
    CONF_UNIQUE_ID,
    CONF_PORT,
    CONF_MODEL,
    CONF_PASSWORD,
    CONF_USERNAME,
)
from homeassistant.core import callback
from homeassistant.data_entry_flow import AbortFlow, FlowResult
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.typing import DiscoveryInfoType
from .const import DOMAIN
from .bridge import get_synapse_description, SynapseApplication
import asyncio
import logging

_LOGGER = logging.getLogger(__name__)


class SynapseConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for synapse"""

    VERSION = 1
    MINOR_VERSION = 1

    def __init__(self) -> None:
        """Initialize the Synapse flow."""
        self.application: SynapseApplication | None = None
        self.discovery_info: dict | None = None

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""
        errors = {}
        if user_input is not None:
            try:
                info = await get_synapse_description(user_input[CONF_HOST])
                await self.async_set_unique_id(info.get("unique_id"))
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=info.get("title"), data=info)
            except Exception:  # pylint: disable=broad-except
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_HOST): str}),
            errors=errors,
        )

    async def async_step_ssdp(self, discovery_info: ssdp.SsdpServiceInfo) -> FlowResult:
        """Handle a flow initialized by SSDP discovery."""
        self.discovery_info = discovery_info
        host = discovery_info.ssdp_location.split("/")[2]
        try:
            info = await get_synapse_description(host)
            await self.async_set_unique_id(info.get("unique_id"))

            self._abort_if_unique_id_configured()
            self.context["title_placeholders"] = {"name": info["title"]}
            self.application = info
            return await self.async_step_confirm()
        except Exception:  # pylint: disable=broad-except
            return self.async_abort(reason="unknown_error")

    async def async_step_confirm(self, user_input=None):
        """Handle the confirmation step."""
        if user_input is not None:
            return self.async_create_entry(title=self.application["title"], data=self.application)

        return self.async_show_form(
            step_id="confirm",
            description_placeholders={"name": self.application["title"]},
            data_schema=vol.Schema({}),
        )
