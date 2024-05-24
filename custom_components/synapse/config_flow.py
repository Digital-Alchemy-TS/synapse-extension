"""Config flow for Digital Alchemy Synapse."""

from __future__ import annotations
from typing import Any
import voluptuous as vol

from homeassistant.components import dhcp
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
    CONF_MAC,
    CONF_MODEL,
    CONF_PASSWORD,
    CONF_USERNAME,
)
from homeassistant.core import callback
from homeassistant.data_entry_flow import AbortFlow, FlowResult
from homeassistant.helpers import device_registry as dr
from homeassistant.components import zeroconf
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

    async def _async_handle_discovery(
        self, host: str, data: SynapseApplication, config: dict | None = None
    ) -> FlowResult:
        """Handle any discovery."""
        _LOGGER.warn("_async_handle_discovery", host, data)
        await self.async_set_unique_id(data.unique_id, raise_on_progress=False)
        self._abort_if_unique_id_configured(updates={CONF_UNIQUE_ID: data.unique_id})

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""
        errors = {}
        if user_input is not None:
            try:
                info = await get_synapse_description(user_input[CONF_HOST])
                return self.async_create_entry(title=info.get("title"), data=info)

            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_HOST): str}),
            errors=errors,
        )
