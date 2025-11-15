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

from .synapse.const import DOMAIN, SynapseErrorCodes

DOMAIN_WS = f"{DOMAIN}_ws"

logger: logging.Logger = logging.getLogger(__name__)

# Rate limiting tracking
_rate_limit_tracking: Dict[str, Dict[str, Any]] = {}

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

    connection_id = id(connection)

    # Search through all bridges to find one with this connection
    for unique_id, bridge in domain_data.items():
        if hasattr(bridge, '_websocket_connections'):
            for uid, conn in bridge._websocket_connections.items():
                if conn == connection or id(conn) == id(connection):
                    return bridge, uid

    logger.warning(f"No bridge found for connection {id(connection)}")
    return None, None

def _send_re_registration_request(connection: websocket_api.ActiveConnection, unique_id: str = None) -> None:
    """
    Send a re-registration request event to the app when desync is detected.

    This tells the app to resend its registration message (application_online_ready).
    Used when the bridge doesn't recognize the connection (desync situation).

    Args:
        connection: The WebSocket connection to send the message to
        unique_id: Optional unique_id to include in the event (if known)
    """
    try:
        re_registration_message = {
            "type": "event",
            "event": {
                "event_type": "synapse/request_re_registration",
                "data": {
                    "message": "Connection desync detected - please re-register",
                    "action": "resend_registration"
                }
            }
        }
        # Include unique_id if provided (allows client to verify it's for them)
        if unique_id:
            re_registration_message["event"]["data"]["unique_id"] = unique_id

        connection.send_message(re_registration_message)
        logger.info(f"Sent re-registration request to connection {id(connection)}" + (f" (unique_id: {unique_id})" if unique_id else ""))
    except Exception as e:
        logger.error(f"Failed to send re-registration request: {e}")

def _handle_bridge_not_found(
    connection: websocket_api.ActiveConnection,
    msg: dict,
    operation: str
) -> None:
    """
    Handle the case where no bridge is found for a connection (desync detected).

    Sends a re-registration request to the app and returns an error response.

    Args:
        connection: The WebSocket connection
        msg: The original message (may contain unique_id)
        operation: Description of the operation being performed (for logging)
    """
    logger.warning(f"No bridge found for {operation} - connection desync detected, requesting re-registration")

    # Try to extract unique_id from message if available (helps client verify it's for them)
    unique_id = msg.get("unique_id")
    _send_re_registration_request(connection, unique_id)

    connection.send_result(msg["id"], {
        "success": False,
        "error_code": SynapseErrorCodes.BRIDGE_NOT_FOUND,
        "message": f"No bridge found for {operation} - connection may be stale. Re-registration requested.",
        "requires_reregistration": True
    })

@websocket_api.websocket_command({
    vol.Required("type"): "synapse/application_online_ready",
    vol.Required("unique_id"): vol.Length(min=1, max=255),
    vol.Required("app_metadata"): vol.Schema({
        vol.Required("app"): vol.Length(min=1, max=100),
        vol.Required("title"): vol.Length(min=1, max=200),
        vol.Required("hash"): vol.Length(min=1, max=64),
        vol.Required("device"): dict,
        vol.Required("secondary_devices"): list,
        vol.Required("hostname"): vol.Length(min=1, max=255),
        vol.Required("username"): vol.Length(min=1, max=100),
        vol.Optional("cleanup"): vol.In(["delete", "abandon"]),
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
        vol.Optional("service"): list,
    }),
})
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

        logger.info(f"App '{app_metadata.get('app')}' attempting to register with unique_id: {unique_id}")

        # Get the bridge instance for this unique_id
        bridge = get_bridge_for_unique_id(hass, unique_id)

        if bridge is None:
            logger.warning(f"No bridge found for unique_id: {unique_id}")
            logger.info("Tip: Ensure the app is properly configured in Home Assistant via the config flow")
            connection.send_result(msg["id"], {
                "success": False,
                "error_code": SynapseErrorCodes.BRIDGE_NOT_FOUND,
                "message": f"No bridge found for unique_id: {unique_id} - app must be configured via the integration config flow first",
                "unique_id": unique_id
            })
            return
        logger.info(f"Bridge found for unique_id: {unique_id}")

        # Handle the registration
        result = await bridge.handle_registration(unique_id, app_metadata)

        # If registration was successful, register the WebSocket connection
        if result.get("success", False):
            bridge.register_websocket_connection(unique_id, connection)
            # Cancel the connection timeout since registration was successful
            bridge._cancel_connection_timeout(unique_id)
            logger.info(f"App '{app_metadata.get('app')}' successfully registered and connected")

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

@websocket_api.websocket_command({
    vol.Required("type"): "synapse/heartbeat",
    vol.Required("hash"): vol.Length(min=1, max=64),
})
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

        # Find the bridge for this connection
        bridge, unique_id = get_bridge_for_connection(hass, connection)

        if bridge is None:
            _handle_bridge_not_found(connection, msg, "heartbeat")
            return

        # Handle the heartbeat (pass connection for re-registration when coming back online)
        result = await bridge.handle_heartbeat(unique_id, current_hash, connection)

        # If hash drift was detected, we might want to send additional commands
        if result.get("hash_drift_detected", False):
            logger.info(f"Configuration drift detected for app {unique_id}, requesting update")

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

@websocket_api.websocket_command({
    vol.Required("type"): "synapse/patch_entity",
    vol.Required("unique_id"): vol.Length(min=1, max=255),
    vol.Required("data"): dict,
})
@websocket_api.async_response
async def handle_synapse_patch_entity(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict
) -> None:
    """Handle simple entity patching from synapse apps."""
    try:
        # Check rate limiting
        connection_id = str(id(connection))
        if _check_rate_limit(connection_id, "patch_entity", max_per_minute=300):  # 5 per second max
            connection.send_error(
                msg["id"],
                SynapseErrorCodes.RATE_LIMIT_EXCEEDED,
                "Too many entity patches. Please reduce frequency."
            )
            return

        # Validate message size
        is_valid, error_msg = _validate_message_size(msg, max_size=10000)  # 10KB for entity patches
        if not is_valid:
            connection.send_error(msg["id"], SynapseErrorCodes.MESSAGE_TOO_LARGE, error_msg)
            return

        entity_unique_id = msg["unique_id"]
        patch_data = msg["data"]

        # Find the bridge for this connection
        bridge, unique_id = get_bridge_for_connection(hass, connection)

        if bridge is None:
            _handle_bridge_not_found(connection, msg, "entity patch")
            return

        # Handle the entity patch
        result = await bridge.handle_entity_patch(entity_unique_id, patch_data)

        connection.send_result(msg["id"], result)

    except vol.Invalid as e:
        logger.warning(f"Invalid entity patch message format: {e}")
        connection.send_error(
            msg["id"],
            SynapseErrorCodes.INVALID_MESSAGE_FORMAT,
            f"Invalid entity patch format: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error handling entity patch: {e}")
        connection.send_error(msg["id"], SynapseErrorCodes.UPDATE_FAILED, str(e))

@websocket_api.websocket_command({
    vol.Required("type"): "synapse/update_configuration",
    vol.Required("unique_id"): vol.Length(min=1, max=255),
    vol.Required("app_metadata"): dict,
})
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

        unique_id = msg["unique_id"]
        app_metadata = msg["app_metadata"]

        # Find the bridge for this connection
        bridge, bridge_unique_id = get_bridge_for_connection(hass, connection)

        if bridge is None:
            _handle_bridge_not_found(connection, msg, "configuration update")
            return

        # Handle the configuration update
        result = await bridge.handle_configuration_update(None, unique_id, app_metadata)

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

@websocket_api.websocket_command({
    vol.Required("type"): "synapse/going_offline",
})
@websocket_api.async_response
async def handle_synapse_going_offline(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict
) -> None:
    """Handle graceful app shutdown."""
    try:
        # Find the bridge for this connection
        bridge, unique_id = get_bridge_for_connection(hass, connection)

        if bridge is None:
            _handle_bridge_not_found(connection, msg, "going offline message")
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

@websocket_api.websocket_command({
    vol.Required("type"): "synapse/get_health",
    vol.Optional("unique_id"): vol.Length(min=1, max=255),
})
@websocket_api.async_response
async def handle_synapse_get_health(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict
) -> None:
    """Handle health check requests."""
    try:
        unique_id = msg.get("unique_id")

        # Find the bridge for this connection
        bridge, bridge_unique_id = get_bridge_for_connection(hass, connection)

        if bridge is None:
            _handle_bridge_not_found(connection, msg, "health check")
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

@websocket_api.websocket_command({
    vol.Required("type"): "synapse/abandoned_entities",
})
@websocket_api.async_response
async def handle_synapse_abandoned_entities(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict
) -> None:
    """Handle abandoned entities check requests."""
    try:
        # Find the bridge for this connection
        bridge, unique_id = get_bridge_for_connection(hass, connection)

        if bridge is None:
            _handle_bridge_not_found(connection, msg, "abandoned entities check")
            return

        # Get abandoned entities information
        result = await bridge.get_abandoned_entities(unique_id)

        connection.send_result(msg["id"], result)

    except vol.Invalid as e:
        logger.warning(f"Invalid abandoned entities message format: {e}")
        connection.send_error(
            msg["id"],
            SynapseErrorCodes.INVALID_MESSAGE_FORMAT,
            f"Invalid abandoned entities format: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error handling abandoned entities check: {e}")
        connection.send_error(msg["id"], SynapseErrorCodes.INTERNAL_ERROR, str(e))

@websocket_api.websocket_command({
    vol.Required("type"): "synapse/service_call_response",
    vol.Required("call_id"): str,
    vol.Required("success"): bool,
    vol.Optional("result"): dict,
    vol.Optional("error"): str,
})
@websocket_api.async_response
async def handle_synapse_service_call_response(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict
) -> None:
    """Handle service call responses from synapse apps."""
    try:
        # Find the bridge for this connection
        bridge, unique_id = get_bridge_for_connection(hass, connection)

        if bridge is None:
            _handle_bridge_not_found(connection, msg, "service call response")
            return

        # Log the service call response
        call_id = msg.get("call_id", "unknown")
        success = msg.get("success", False)
        result = msg.get("result", {})
        error = msg.get("error", "")

        if success:
            logger.info(f"Service call {call_id} completed successfully: {result}")
        else:
            logger.warning(f"Service call {call_id} failed: {error}")

        # For now, just acknowledge the response
        # In a more sophisticated implementation, you might want to store the result
        connection.send_result(msg["id"], {
            "success": True,
            "message": "Service call response received"
        })

    except vol.Invalid as e:
        logger.warning(f"Invalid service call response message format: {e}")
        connection.send_error(
            msg["id"],
            SynapseErrorCodes.INVALID_MESSAGE_FORMAT,
            f"Invalid service call response format: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error handling service call response: {e}")
        connection.send_error(msg["id"], SynapseErrorCodes.INTERNAL_ERROR, str(e))

_handlers_registered = False

def ensure_handlers_registered(hass: HomeAssistant) -> None:
    """Ensure websocket handlers are registered (lazy registration)."""
    global _handlers_registered
    if not _handlers_registered:
        logger.warning("WebSocket handlers not registered - registering now")
        register_websocket_handlers(hass)
        _handlers_registered = True

def register_websocket_handlers(hass: HomeAssistant) -> None:
    """Register all WebSocket command handlers."""
    global _handlers_registered
    if _handlers_registered:
        logger.debug("WebSocket handlers already registered, skipping")
        return
    logger.info("Registering Synapse WebSocket handlers...")
    try:
        websocket_api.async_register_command(hass, handle_synapse_register)
        logger.info("Registered: synapse/application_online_ready")
    except Exception as e:
        logger.error(f"Failed to register synapse/application_online_ready: {e}")

    try:
        websocket_api.async_register_command(hass, handle_synapse_heartbeat)
        logger.info("Registered: synapse/heartbeat")
    except Exception as e:
        logger.error(f"Failed to register synapse/heartbeat: {e}")

    try:
        websocket_api.async_register_command(hass, handle_synapse_patch_entity)
        logger.info("Registered: synapse/patch_entity")
    except Exception as e:
        logger.error(f"Failed to register synapse/patch_entity: {e}")

    try:
        websocket_api.async_register_command(hass, handle_synapse_update_configuration)
        logger.info("Registered: synapse/update_configuration")
    except Exception as e:
        logger.error(f"Failed to register synapse/update_configuration: {e}")

    try:
        websocket_api.async_register_command(hass, handle_synapse_going_offline)
        logger.info("Registered: synapse/going_offline")
    except Exception as e:
        logger.error(f"Failed to register synapse/going_offline: {e}")

    try:
        websocket_api.async_register_command(hass, handle_synapse_get_health)
        logger.info("Registered: synapse/get_health")
    except Exception as e:
        logger.error(f"Failed to register synapse/get_health: {e}")

    try:
        websocket_api.async_register_command(hass, handle_synapse_abandoned_entities)
        logger.info("Registered: synapse/abandoned_entities")
    except Exception as e:
        logger.error(f"Failed to register synapse/abandoned_entities: {e}")

    try:
        websocket_api.async_register_command(hass, handle_synapse_service_call_response)
        logger.info("Registered: synapse/service_call_response")
    except Exception as e:
        logger.error(f"Failed to register synapse/service_call_response: {e}")

    _handlers_registered = True
    logger.info("Synapse WebSocket handlers registration complete")
