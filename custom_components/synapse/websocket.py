"""
WebSocket API handlers for Synapse integration.

This module handles all WebSocket communication between NodeJS Synapse applications
and the Home Assistant Synapse extension.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv

from .synapse.const import DOMAIN

DOMAIN_WS = f"{DOMAIN}_ws"

logger: logging.Logger = logging.getLogger(__name__)

# WebSocket command schemas
REGISTER_SCHEMA = vol.Schema({
    vol.Required("type"): "synapse/register",
    vol.Required("unique_id"): str,
    vol.Required("app_metadata"): vol.Schema({
        vol.Required("app"): str,
        vol.Required("title"): str,
        vol.Required("hash"): str,
        vol.Required("device"): dict,
        vol.Required("secondary_devices"): list,
        vol.Required("hostname"): str,
        vol.Required("username"): str,
        # Additional fields from storage dump
        vol.Optional("sensor"): list,
        vol.Optional("switch"): list,
        vol.Optional("binary_sensor"): list,
        vol.Optional("button"): list,
        vol.Optional("climate"): list,
        vol.Optional("lock"): list,
        vol.Optional("number"): list,
        vol.Optional("select"): list,
        vol.Optional("text"): list,
        vol.Optional("date"): list,
        vol.Optional("time"): list,
        vol.Optional("datetime"): list,
        vol.Optional("scene"): list,
    }),
})

HEARTBEAT_SCHEMA = vol.Schema({
    vol.Required("type"): "synapse/heartbeat",
    vol.Required("hash"): str,
})

UPDATE_ENTITY_SCHEMA = vol.Schema({
    vol.Required("type"): "synapse/update_entity",
    vol.Required("unique_id"): str,
    vol.Required("changes"): dict,
})

UPDATE_CONFIGURATION_SCHEMA = vol.Schema({
    vol.Required("type"): "synapse/update_configuration",
    vol.Required("configuration"): dict,
})


def get_bridge_for_unique_id(hass: HomeAssistant, unique_id: str):
    """Get the bridge instance for a given unique_id."""
    domain_data = hass.data.get(DOMAIN, {})
    return domain_data.get(unique_id)


@websocket_api.websocket_command(REGISTER_SCHEMA)
@websocket_api.async_response
async def handle_synapse_register(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict
) -> None:
    """Handle synapse app registration."""
    try:
        unique_id = msg["unique_id"]
        app_metadata = msg["app_metadata"]

        logger.info(f"Received registration from app: {app_metadata.get('app')} with unique_id: {unique_id}")

        # Get the bridge instance for this unique_id
        bridge = get_bridge_for_unique_id(hass, unique_id)

        if bridge is None:
            # TODO: Handle case where bridge doesn't exist yet
            # This might happen during initial discovery
            logger.warning(f"No bridge found for unique_id: {unique_id}")
            connection.send_result(msg["id"], {
                "success": False,
                "error": "bridge_not_found",
                "message": f"No bridge found for unique_id: {unique_id}"
            })
            return

        # Handle the registration
        result = await bridge.handle_registration(unique_id, app_metadata)

        # Register the WebSocket connection with the bridge
        bridge.register_websocket_connection(unique_id, connection)

        connection.send_result(msg["id"], result)

    except Exception as e:
        logger.error(f"Error handling registration: {e}")
        connection.send_error(msg["id"], "registration_failed", str(e))


@websocket_api.websocket_command(HEARTBEAT_SCHEMA)
@websocket_api.async_response
async def handle_synapse_heartbeat(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict
) -> None:
    """Handle heartbeat from synapse apps."""
    try:
        current_hash = msg["hash"]

        logger.debug(f"Received heartbeat with hash: {current_hash}")

        # TODO: Determine which bridge this heartbeat belongs to
        # For now, we'll need to find the bridge by connection or other means
        # This is a temporary implementation

        # Find bridge by connection
        domain_data = hass.data.get(DOMAIN, {})
        bridge = None
        unique_id = None

        for uid, br in domain_data.items():
            if uid in br._websocket_connections:
                # This is a simplified check - we'll need a better way to map connections
                bridge = br
                unique_id = uid
                break

        if bridge is None:
            logger.warning("No bridge found for heartbeat")
            connection.send_result(msg["id"], {
                "success": False,
                "error": "bridge_not_found",
                "message": "No bridge found for heartbeat"
            })
            return

        # Handle the heartbeat
        result = await bridge.handle_heartbeat(unique_id, current_hash)

        connection.send_result(msg["id"], result)

    except Exception as e:
        logger.error(f"Error handling heartbeat: {e}")
        connection.send_error(msg["id"], "heartbeat_failed", str(e))


@websocket_api.websocket_command(UPDATE_ENTITY_SCHEMA)
@websocket_api.async_response
async def handle_synapse_update_entity(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict
) -> None:
    """Handle entity updates from synapse apps."""
    try:
        entity_unique_id = msg["unique_id"]
        changes = msg["changes"]

        logger.debug(f"Received entity update for {entity_unique_id}: {changes}")

        # TODO: Determine which bridge this update belongs to
        # Similar to heartbeat, we need to find the bridge

        domain_data = hass.data.get(DOMAIN, {})
        bridge = None

        for uid, br in domain_data.items():
            if uid in br._websocket_connections:
                bridge = br
                break

        if bridge is None:
            logger.warning("No bridge found for entity update")
            connection.send_result(msg["id"], {
                "success": False,
                "error": "bridge_not_found",
                "message": "No bridge found for entity update"
            })
            return

        # Handle the entity update
        result = await bridge.handle_entity_update(entity_unique_id, changes)

        connection.send_result(msg["id"], result)

    except Exception as e:
        logger.error(f"Error handling entity update: {e}")
        connection.send_error(msg["id"], "update_failed", str(e))


@websocket_api.websocket_command(UPDATE_CONFIGURATION_SCHEMA)
@websocket_api.async_response
async def handle_synapse_update_configuration(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict
) -> None:
    """Handle full configuration updates from synapse apps."""
    try:
        configuration = msg["configuration"]

        logger.info("Received full configuration update")

        # TODO: Determine which bridge this update belongs to
        domain_data = hass.data.get(DOMAIN, {})
        bridge = None

        for uid, br in domain_data.items():
            if uid in br._websocket_connections:
                bridge = br
                break

        if bridge is None:
            logger.warning("No bridge found for configuration update")
            connection.send_result(msg["id"], {
                "success": False,
                "error": "bridge_not_found",
                "message": "No bridge found for configuration update"
            })
            return

        # Handle the configuration update
        result = await bridge.handle_configuration_update(configuration)

        connection.send_result(msg["id"], result)

    except Exception as e:
        logger.error(f"Error handling configuration update: {e}")
        connection.send_error(msg["id"], "configuration_update_failed", str(e))


def register_websocket_handlers(hass: HomeAssistant) -> None:
    """Register all WebSocket command handlers."""
    websocket_api.async_register_command(hass, handle_synapse_register)
    websocket_api.async_register_command(hass, handle_synapse_heartbeat)
    websocket_api.async_register_command(hass, handle_synapse_update_entity)
    websocket_api.async_register_command(hass, handle_synapse_update_configuration)

    logger.info("Synapse WebSocket handlers registered")
