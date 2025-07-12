"""
WebSocket API handlers for Synapse integration.

This module handles all WebSocket communication between NodeJS Synapse applications
and the Home Assistant Synapse extension.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv

from .synapse.const import DOMAIN, SynapseErrorCodes, CONNECTION_TIMEOUT, MAX_RECONNECT_ATTEMPTS

DOMAIN_WS = f"{DOMAIN}_ws"

logger: logging.Logger = logging.getLogger(__name__)

# Rate limiting tracking
_rate_limit_tracking: Dict[str, Dict[str, Any]] = {}

# WebSocket command schemas
REGISTER_SCHEMA = vol.Schema({
    vol.Required("type"): "synapse/register",
    vol.Required("unique_id"): vol.Length(min=1, max=255),  # Add length validation
    vol.Required("app_metadata"): vol.Schema({
        vol.Required("app"): vol.Length(min=1, max=100),
        vol.Required("title"): vol.Length(min=1, max=200),
        vol.Required("hash"): vol.Length(min=1, max=64),  # SHA-256 hash length
        vol.Required("device"): dict,
        vol.Required("secondary_devices"): list,
        vol.Required("hostname"): vol.Length(min=1, max=255),
        vol.Required("username"): vol.Length(min=1, max=100),
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
    vol.Required("hash"): vol.Length(min=1, max=64),
})

UPDATE_ENTITY_SCHEMA = vol.Schema({
    vol.Required("type"): "synapse/update_entity",
    vol.Required("unique_id"): vol.Length(min=1, max=255),
    vol.Required("changes"): vol.Length(max=10000),  # Limit changes size
})

UPDATE_CONFIGURATION_SCHEMA = vol.Schema({
    vol.Required("type"): "synapse/update_configuration",
    vol.Required("configuration"): vol.Length(max=1000000),  # 1MB limit for config
})

GOING_OFFLINE_SCHEMA = vol.Schema({
    vol.Required("type"): "synapse/going_offline",
    vol.Required("unique_id"): vol.Length(min=1, max=255),
})

GET_HEALTH_SCHEMA = vol.Schema({
    vol.Required("type"): "synapse/get_health",
    vol.Optional("unique_id"): vol.Length(min=1, max=255),  # Optional - if not provided, return all connections
})

def _check_rate_limit(connection_id: str, command_type: str, max_per_minute: int = 60) -> bool:
    """
    Check if a connection is rate limited for a specific command type.

    Args:
        connection_id: Unique identifier for the connection
        command_type: Type of command being executed
        max_per_minute: Maximum allowed requests per minute

    Returns:
        bool: True if rate limit exceeded, False otherwise
    """
    current_time = time.time()
    key = f"{connection_id}:{command_type}"

    if key not in _rate_limit_tracking:
        _rate_limit_tracking[key] = {"count": 0, "window_start": current_time}

    tracking = _rate_limit_tracking[key]

    # Reset window if more than 60 seconds have passed
    if current_time - tracking["window_start"] > 60:
        tracking["count"] = 0
        tracking["window_start"] = current_time

    # Check if rate limit exceeded
    if tracking["count"] >= max_per_minute:
        return True

    tracking["count"] += 1
    return False

def _validate_message_size(message: Dict[str, Any], max_size: int = 1000000) -> tuple[bool, str]:
    """
    Validate message size to prevent DoS attacks.

    Args:
        message: The message to validate
        max_size: Maximum allowed size in bytes

    Returns:
        tuple: (is_valid, error_message)
    """
    try:
        import json
        message_str = json.dumps(message)
        if len(message_str.encode('utf-8')) > max_size:
            return False, f"Message size exceeds maximum allowed size of {max_size} bytes"
        return True, ""
    except Exception as e:
        return False, f"Failed to validate message size: {str(e)}"

def _cleanup_rate_limit_tracking() -> None:
    """Clean up old rate limit tracking entries."""
    current_time = time.time()
    keys_to_remove = []

    for key, tracking in _rate_limit_tracking.items():
        if current_time - tracking["window_start"] > 120:  # Remove entries older than 2 minutes
            keys_to_remove.append(key)

    for key in keys_to_remove:
        del _rate_limit_tracking[key]

def get_bridge_for_unique_id(hass: HomeAssistant, unique_id: str):
    """Get bridge instance for a unique_id."""
    domain_data = hass.data.get(DOMAIN, {})
    return domain_data.get(unique_id)

def get_bridge_for_connection(hass: HomeAssistant, connection: Any):
    """Get bridge instance and unique_id for a WebSocket connection."""
    domain_data = hass.data.get(DOMAIN, {})

    # Search through all bridges to find one with this connection
    for bridge in domain_data.values():
        if hasattr(bridge, '_websocket_connections'):
            for uid, conn in bridge._websocket_connections.items():
                if conn == connection:
                    return bridge, uid

    return None, None

@websocket_api.websocket_command(REGISTER_SCHEMA)
@websocket_api.async_response
async def handle_synapse_register(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict
) -> None:
    """Handle synapse app registration."""
    try:
        # Clean up old rate limit tracking
        _cleanup_rate_limit_tracking()

        # Check rate limiting
        connection_id = str(id(connection))
        if _check_rate_limit(connection_id, "register", max_per_minute=10):
            connection.send_error(
                msg["id"],
                SynapseErrorCodes.RATE_LIMIT_EXCEEDED,
                "Too many registration attempts. Please wait before retrying."
            )
            return

        # Validate message size
        is_valid, error_msg = _validate_message_size(msg, max_size=50000)  # 50KB for registration
        if not is_valid:
            connection.send_error(msg["id"], SynapseErrorCodes.MESSAGE_TOO_LARGE, error_msg)
            return

        unique_id = msg["unique_id"]
        app_metadata = msg["app_metadata"]

        logger.info(f"Received registration from app: {app_metadata.get('app')} with unique_id: {unique_id}")

        # Get the bridge instance for this unique_id
        bridge = get_bridge_for_unique_id(hass, unique_id)

        if bridge is None:
            logger.warning(f"No bridge found for unique_id: {unique_id}")
            connection.send_result(msg["id"], {
                "success": False,
                "error_code": SynapseErrorCodes.BRIDGE_NOT_FOUND,
                "message": f"No bridge found for unique_id: {unique_id} - may still be initializing",
                "unique_id": unique_id
            })
            return

        # Handle the registration
        result = await bridge.handle_registration(unique_id, app_metadata)

        # If registration was successful, register the WebSocket connection
        if result.get("success", False):
            bridge.register_websocket_connection(unique_id, connection)

        connection.send_result(msg["id"], result)

    except vol.Invalid as e:
        logger.warning(f"Invalid registration message format: {e}")
        connection.send_error(
            msg["id"],
            SynapseErrorCodes.INVALID_MESSAGE_FORMAT,
            f"Invalid message format: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error handling registration: {e}")
        connection.send_error(msg["id"], SynapseErrorCodes.REGISTRATION_FAILED, str(e))

@websocket_api.websocket_command(HEARTBEAT_SCHEMA)
@websocket_api.async_response
async def handle_synapse_heartbeat(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict
) -> None:
    """Handle heartbeat from synapse apps."""
    try:
        # Check rate limiting (more lenient for heartbeats)
        connection_id = str(id(connection))
        if _check_rate_limit(connection_id, "heartbeat", max_per_minute=120):  # 2 per second max
            connection.send_error(
                msg["id"],
                SynapseErrorCodes.RATE_LIMIT_EXCEEDED,
                "Too many heartbeat messages. Please reduce frequency."
            )
            return

        current_hash = msg["hash"]

        logger.debug(f"Received heartbeat with hash: {current_hash}")

        # Find the bridge for this connection
        bridge, unique_id = get_bridge_for_connection(hass, connection)

        if bridge is None:
            logger.warning("No bridge found for heartbeat")
            connection.send_result(msg["id"], {
                "success": False,
                "error_code": SynapseErrorCodes.BRIDGE_NOT_FOUND,
                "message": "No bridge found for heartbeat - connection may be stale"
            })
            return

        # Handle the heartbeat
        result = await bridge.handle_heartbeat(unique_id, current_hash)

        # If hash drift was detected, we might want to send additional commands
        if result.get("hash_drift_detected", False):
            logger.info(f"Hash drift detected for {unique_id}, requesting configuration update")
            # The app should respond to this by sending a configuration update
            # We could also send a separate command here if needed

        connection.send_result(msg["id"], result)

    except vol.Invalid as e:
        logger.warning(f"Invalid heartbeat message format: {e}")
        connection.send_error(
            msg["id"],
            SynapseErrorCodes.INVALID_MESSAGE_FORMAT,
            f"Invalid heartbeat format: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error handling heartbeat: {e}")
        connection.send_error(msg["id"], SynapseErrorCodes.HEARTBEAT_FAILED, str(e))

@websocket_api.websocket_command(UPDATE_ENTITY_SCHEMA)
@websocket_api.async_response
async def handle_synapse_update_entity(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict
) -> None:
    """Handle entity updates from synapse apps."""
    try:
        # Check rate limiting
        connection_id = str(id(connection))
        if _check_rate_limit(connection_id, "update_entity", max_per_minute=300):  # 5 per second max
            connection.send_error(
                msg["id"],
                SynapseErrorCodes.RATE_LIMIT_EXCEEDED,
                "Too many entity updates. Please reduce frequency."
            )
            return

        # Validate message size
        is_valid, error_msg = _validate_message_size(msg, max_size=10000)  # 10KB for entity updates
        if not is_valid:
            connection.send_error(msg["id"], SynapseErrorCodes.MESSAGE_TOO_LARGE, error_msg)
            return

        entity_unique_id = msg["unique_id"]
        changes = msg["changes"]

        logger.debug(f"Received entity update for {entity_unique_id}: {changes}")

        # Find the bridge for this connection
        bridge, unique_id = get_bridge_for_connection(hass, connection)

        if bridge is None:
            logger.warning("No bridge found for entity update")
            connection.send_result(msg["id"], {
                "success": False,
                "error_code": SynapseErrorCodes.BRIDGE_NOT_FOUND,
                "message": "No bridge found for entity update - connection may be stale"
            })
            return

        # Handle the entity update
        result = await bridge.handle_entity_update(entity_unique_id, changes)

        connection.send_result(msg["id"], result)

    except vol.Invalid as e:
        logger.warning(f"Invalid entity update message format: {e}")
        connection.send_error(
            msg["id"],
            SynapseErrorCodes.INVALID_MESSAGE_FORMAT,
            f"Invalid entity update format: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error handling entity update: {e}")
        connection.send_error(msg["id"], SynapseErrorCodes.UPDATE_FAILED, str(e))

@websocket_api.websocket_command(UPDATE_CONFIGURATION_SCHEMA)
@websocket_api.async_response
async def handle_synapse_update_configuration(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict
) -> None:
    """Handle full configuration updates from synapse apps."""
    try:
        # Check rate limiting (very strict for config updates)
        connection_id = str(id(connection))
        if _check_rate_limit(connection_id, "update_configuration", max_per_minute=5):
            connection.send_error(
                msg["id"],
                SynapseErrorCodes.RATE_LIMIT_EXCEEDED,
                "Too many configuration updates. Please wait before retrying."
            )
            return

        # Validate message size
        is_valid, error_msg = _validate_message_size(msg, max_size=1000000)  # 1MB for config
        if not is_valid:
            connection.send_error(msg["id"], SynapseErrorCodes.CONFIGURATION_TOO_LARGE, error_msg)
            return

        configuration = msg["configuration"]

        logger.info("Received full configuration update")

        # Find the bridge for this connection
        bridge, unique_id = get_bridge_for_connection(hass, connection)

        if bridge is None:
            logger.warning("No bridge found for configuration update")
            connection.send_result(msg["id"], {
                "success": False,
                "error_code": SynapseErrorCodes.BRIDGE_NOT_FOUND,
                "message": "No bridge found for configuration update - connection may be stale"
            })
            return

        # Handle the configuration update
        result = await bridge.handle_configuration_update(configuration)

        connection.send_result(msg["id"], result)

    except vol.Invalid as e:
        logger.warning(f"Invalid configuration update message format: {e}")
        connection.send_error(
            msg["id"],
            SynapseErrorCodes.INVALID_MESSAGE_FORMAT,
            f"Invalid configuration update format: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error handling configuration update: {e}")
        connection.send_error(msg["id"], SynapseErrorCodes.CONFIGURATION_UPDATE_FAILED, str(e))

@websocket_api.websocket_command(GOING_OFFLINE_SCHEMA)
@websocket_api.async_response
async def handle_synapse_going_offline(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict
) -> None:
    """Handle graceful app shutdown."""
    try:
        unique_id = msg["unique_id"]

        logger.info(f"Received going offline message from app: {unique_id}")

        # Find the bridge for this connection
        bridge, bridge_unique_id = get_bridge_for_connection(hass, connection)

        if bridge is None:
            logger.warning("No bridge found for going offline message")
            connection.send_result(msg["id"], {
                "success": False,
                "error_code": SynapseErrorCodes.BRIDGE_NOT_FOUND,
                "message": "No bridge found for going offline message - connection may be stale"
            })
            return

        # Handle the going offline request
        result = await bridge.handle_going_offline(unique_id)

        connection.send_result(msg["id"], result)

    except vol.Invalid as e:
        logger.warning(f"Invalid going offline message format: {e}")
        connection.send_error(
            msg["id"],
            SynapseErrorCodes.INVALID_MESSAGE_FORMAT,
            f"Invalid going offline format: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error handling going offline: {e}")
        connection.send_error(msg["id"], SynapseErrorCodes.GOING_OFFLINE_FAILED, str(e))

@websocket_api.websocket_command(GET_HEALTH_SCHEMA)
@websocket_api.async_response
async def handle_synapse_get_health(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict
) -> None:
    """Handle health check requests."""
    try:
        unique_id = msg.get("unique_id")

        logger.debug(f"Received health check request for unique_id: {unique_id}")

        # Find the bridge for this connection
        bridge, bridge_unique_id = get_bridge_for_connection(hass, connection)

        if bridge is None:
            logger.warning("No bridge found for health check")
            connection.send_result(msg["id"], {
                "success": False,
                "error_code": SynapseErrorCodes.BRIDGE_NOT_FOUND,
                "message": "No bridge found for health check - connection may be stale"
            })
            return

        # Get health information
        if unique_id:
            # Specific connection health
            health_info = bridge.get_connection_health(unique_id)
            result = {
                "success": True,
                "health": health_info,
                "unique_id": unique_id
            }
        else:
            # All connections health
            all_health = {}
            for uid in bridge._websocket_connections.keys():
                all_health[uid] = bridge.get_connection_health(uid)

            result = {
                "success": True,
                "health": all_health,
                "total_connections": len(all_health)
            }

        connection.send_result(msg["id"], result)

    except vol.Invalid as e:
        logger.warning(f"Invalid health check message format: {e}")
        connection.send_error(
            msg["id"],
            SynapseErrorCodes.INVALID_MESSAGE_FORMAT,
            f"Invalid health check format: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error handling health check: {e}")
        connection.send_error(msg["id"], SynapseErrorCodes.INTERNAL_ERROR, str(e))

def register_websocket_handlers(hass: HomeAssistant) -> None:
    """Register all WebSocket command handlers."""
    websocket_api.async_register_command(hass, handle_synapse_register)
    websocket_api.async_register_command(hass, handle_synapse_heartbeat)
    websocket_api.async_register_command(hass, handle_synapse_update_entity)
    websocket_api.async_register_command(hass, handle_synapse_update_configuration)
    websocket_api.async_register_command(hass, handle_synapse_going_offline)
    websocket_api.async_register_command(hass, handle_synapse_get_health)

    logger.info("Synapse WebSocket handlers registered")
