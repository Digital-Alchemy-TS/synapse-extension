from __future__ import annotations

import logging
from typing import Dict

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import service

from .synapse.bridge import SynapseBridge
from .synapse.const import DOMAIN, PLATFORMS
from .websocket import register_websocket_handlers

logger: logging.Logger = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Synapse component.

    Initializes the component by registering WebSocket handlers and services.
    This is called once when the integration is loaded.
    """
    # Register WebSocket command handlers for app communication
    register_websocket_handlers(hass)

    # Register service handlers
    async def async_handle_reload(call: ServiceCall) -> None:
        """Handle the reload service call.

        Supports reloading either a specific app (by name) or all connected apps.
        This triggers configuration updates from the target app(s).
        """
        app_name = call.data.get("app")

        if app_name:
            # Target specific app by name
            for entry_id, bridge in hass.data.get(DOMAIN, {}).items():
                if bridge.app_name == app_name:
                    logger.info(f"Reloading specific app: {app_name}")
                    await bridge.async_reload()
                    return
            logger.warning(f"App '{app_name}' not found for reload")
        else:
            # Target all connected apps
            logger.info("Reloading all connected apps")
            for entry_id, bridge in hass.data.get(DOMAIN, {}).items():
                await bridge.async_reload()

    hass.services.async_register(DOMAIN, "reload", async_handle_reload)

    return True

async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Set up Synapse app from a config entry.

    Creates or retrieves a bridge instance for the app and initializes
    all supported entity platforms. This is called for each configured app.
    """
    domain_data: Dict[str, SynapseBridge] = hass.data.setdefault(DOMAIN, {})
    bridge: SynapseBridge | None = None

    if config_entry.entry_id not in domain_data:
        bridge = SynapseBridge(hass, config_entry)
        domain_data[config_entry.entry_id] = bridge
    else:
        bridge = domain_data[config_entry.entry_id]

    await bridge.async_reload()

    # Bridge is ready to hand off data to entities:
    # - devices are up to date
    # - old entities have been removed
    await hass.config_entries.async_forward_entry_setups(
        config_entry,
        PLATFORMS
    )

    # Notify app that bridge is ready via event bus
    unique_id = bridge.metadata_unique_id
    logger.info(f"Bridge setup complete for app '{bridge.app_name}' (unique_id: {unique_id})")
    hass.bus.async_fire(
        "synapse/registration_ready",
        {
            "unique_id": unique_id,
            "message": "Bridge is ready - please register via WebSocket"
        }
    )
    logger.info(f"Sent registration_ready event for app '{unique_id}'")

    return True

async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Unload a config entry.

    Currently returns True without cleanup to avoid issues during development.
    TODO: Implement proper cleanup when stable.
    """
    # TODO: Implement proper cleanup when unload is stable
    # bridge: SynapseBridge = hass.data.setdefault(DOMAIN, {})[config_entry.entry_id]
    # await bridge.async_cleanup()
    # unload_ok = await hass.config_entries.async_unload_platforms(config_entry, PLATFORMS)
    # if unload_ok:
    #     hass.data[DOMAIN].pop(config_entry.entry_id)
    # return unload_ok
    return True
