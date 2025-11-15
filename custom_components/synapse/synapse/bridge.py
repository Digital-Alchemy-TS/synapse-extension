"""
# Digital Alchemy Synapse Bridge

Bridges are constructed 1-1 with connected applications when they are registered.
All app level interactions are done here, leaving entity changes to other code.

## WebSocket Communication

Applications connect via Home Assistant's WebSocket API and communicate using
the synapse command namespace. The bridge handles:

1. App registration and validation
2. Hash-based configuration synchronization
3. Runtime entity updates
4. Heartbeat monitoring
5. Connection timeout and recovery

## Connection & Registration

1. NodeJS app connects to Home Assistant WebSocket API
2. App sends "hello world" message with app metadata
3. Bridge validates unique_id against existing connections
4. Bridge checks unique_id against registered apps
5. If registered, sends acknowledgment with last known hash
6. App compares hashes and syncs configuration if needed

## Runtime Operation

- Heartbeat every 30 seconds with current hash
- Hash drift detection triggers configuration resync
- Entity patches for state/visual/config changes
- No hash changes for runtime patches
- Connection timeout detection and recovery
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
import traceback
from typing import Any, Dict, List, Optional

from homeassistant.config_entries import ConfigEntry
from homeassistant.exceptions import HomeAssistantError
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
from homeassistant.core import callback, HomeAssistant, ServiceCall
from homeassistant.helpers import entity_registry as er, device_registry as dr, service
from homeassistant.helpers.device_registry import DeviceInfo

from homeassistant.components import websocket_api

from .const import (
    DOMAIN,
    PLATFORMS,
    ENTITY_DOMAINS,
    SERVICE_DOMAINS,
    SynapseApplication,
    SynapseMetadata,
    SynapseErrorCodes,
    APP_OFFLINE_DELAY,
    CONNECTION_TIMEOUT,
    HEARTBEAT_TIMEOUT,
)


class SynapseBridge:
    """
    - Handle WebSocket comms with the app
    - Provide helper methods for entities
    - Create online sensor
    - Tracks app heartbeat
    - Manages connection timeouts and recovery
    """
    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize the bridge.

        Creates a bridge instance for managing communication with a specific
        NodeJS app. Handles WebSocket connections, entity management, and
        configuration synchronization.

        Args:
            hass: Home Assistant instance
            config_entry: Configuration entry for this app
        """
        self.logger: logging.Logger = logging.getLogger(__name__)
        self.config_entry: ConfigEntry = config_entry
        self.primary_device: Optional[DeviceInfo] = None
        self.via_primary_device: Dict[str, DeviceInfo] = {}
        self.hass: HomeAssistant = hass
        self.app_data: SynapseApplication = config_entry.data
        self.app_name: str = self.app_data.get("app", "")
        self.metadata_unique_id: str = self.app_data.get("unique_id", "")
        # Temporary storage for device info from registration (since app_data is read-only)
        self._registration_device: Optional[Dict[str, Any]] = None
        self._registration_secondary_devices: List[Dict[str, Any]] = []

        # Instance-based state management (fixes global state issue)
        self._hash_dict: Dict[str, str] = {}
        self._entity_registry: Dict[str, Dict[str, Any]] = {}
        self._device_registry: Dict[str, DeviceInfo] = {}

        # Track current entities and devices for removal detection
        self._current_entities: Dict[str, set] = {}  # domain -> set of unique_ids
        self._current_devices: set = set()  # set of device unique_ids
        self._current_services: set = set()  # set of service unique_ids
        self._cleanup_mode: str = "delete"  # Default cleanup mode
        self._current_configuration: Dict[str, Any] = {}  # Current dynamic configuration

        # Track generated entities (created by Python code, not app registration)
        self._generated_entities: set = set()  # set of unique_ids for generated entities

        # Track registered services for removal: unique_id -> {name, domain}
        self._service_registry: Dict[str, Dict[str, Any]] = {}

        hass.data.setdefault(DOMAIN, {})[self.metadata_unique_id] = self

        # WebSocket connection tracking
        self._websocket_connections: Dict[str, Any] = {}
        self._connection_timestamps: Dict[str, float] = {}  # Track when connections were established
        self._connection_timeout_timers: Dict[str, asyncio.TimerHandle] = {}  # Connection timeout timers
        self.online: bool = False
        self._heartbeat_timer: Optional[asyncio.TimerHandle] = None
        self._last_heartbeat_time: Optional[float] = None

        # Load persisted hashes from config entry data
        self._load_persisted_hashes()

        self.logger.info(f"Bridge initialized for app '{self.app_name}' - ready for connections")

    def event_name(self, event_type: str) -> str:
        """
        Generate event names for this bridge instance.

        Args:
            event_type: The type of event (health, update, etc.)

        Returns:
            str: The full event name for this bridge
        """
        return f"{DOMAIN}/{event_type}"

    async def async_cleanup(self) -> None:
        """Clean up bridge resources when tearing down.

        Cancels all timers, clears WebSocket connections, and resets
        internal state. Called when the bridge is being destroyed.
        """
        self.logger.info(f"Cleaning up bridge for app '{self.app_name}'")
        if self._heartbeat_timer:
            self._heartbeat_timer.cancel()

        # Clean up all connection timers
        for timer in self._connection_timeout_timers.values():
            if timer:
                timer.cancel()
        self._connection_timeout_timers.clear()

        # Clean up WebSocket connections
        self._websocket_connections.clear()

        # Clean up generated entities tracking
        self._generated_entities.clear()

    def register_websocket_connection(self, unique_id: str, connection: Any) -> None:
        """Register a WebSocket connection for an app.

        Establishes a new WebSocket connection and sets up monitoring timers.
        Marks the bridge as online and fires health events for entity updates.

        Args:
            unique_id: Unique identifier for the app connection
            connection: WebSocket connection object
        """
        self.logger.info(f"WebSocket connection established for app '{unique_id}'")
        self._websocket_connections[unique_id] = connection
        self._connection_timestamps[unique_id] = time.time()

        # Set up connection timeout timer
        self._setup_connection_timeout(unique_id)

        self._reset_heartbeat_timer()

        # Mark bridge as online when a connection is registered
        was_offline = not self.online
        self.online = True

        if was_offline:
            self.logger.info(f"App '{self.app_name}' restored contact via registration")
            # Fire health event to update entity availability
            self.hass.bus.async_fire(self.event_name("health"))

    def unregister_websocket_connection(self, unique_id: str) -> None:
        """Unregister a WebSocket connection for an app."""
        self.logger.info(f"WebSocket connection closed for app '{unique_id}'")
        if unique_id in self._websocket_connections:
            del self._websocket_connections[unique_id]

        # Clean up connection tracking
        if unique_id in self._connection_timestamps:
            del self._connection_timestamps[unique_id]

        # Cancel connection timeout timer
        if unique_id in self._connection_timeout_timers:
            timer = self._connection_timeout_timers[unique_id]
            if timer:
                timer.cancel()
            del self._connection_timeout_timers[unique_id]

        if not self._websocket_connections:
            # No more connections, stop heartbeat monitoring
            if self._heartbeat_timer:
                self._heartbeat_timer.cancel()
                self._heartbeat_timer = None
            was_online = self.online
            self.online = False
            # Fire health event to update entity availability when going offline
            if was_online:
                self.hass.bus.async_fire(self.event_name("health"))

    def _setup_connection_timeout(self, unique_id: str) -> None:
        """Set up a connection timeout timer for a specific connection."""
        # Cancel existing timer if any
        if unique_id in self._connection_timeout_timers:
            timer = self._connection_timeout_timers[unique_id]
            if timer:
                timer.cancel()

        # Set new timeout timer
        timer = self.hass.loop.call_later(
            CONNECTION_TIMEOUT,
            lambda: self._handle_connection_timeout(unique_id)
        )
        self._connection_timeout_timers[unique_id] = timer

    def _handle_connection_timeout(self, unique_id: str) -> None:
        """Handle connection timeout for a specific connection."""
        if unique_id not in self._websocket_connections:
            return  # Connection already cleaned up

        self.logger.warning(f"Connection timeout for app '{unique_id}' - no registration within {CONNECTION_TIMEOUT} seconds")

        # Clean up the connection
        self.unregister_websocket_connection(unique_id)

        # Fire health event to update entity availability
        self.hass.bus.async_fire(self.event_name("health"))

    def _reset_connection_timeout(self, unique_id: str) -> None:
        """Reset the connection timeout timer for a specific connection."""
        if unique_id in self._websocket_connections:
            self._setup_connection_timeout(unique_id)

    def _cancel_connection_timeout(self, unique_id: str) -> None:
        """Cancel the connection timeout timer for a specific connection."""
        if unique_id in self._connection_timeout_timers:
            timer = self._connection_timeout_timers[unique_id]
            if timer:
                timer.cancel()
            del self._connection_timeout_timers[unique_id]

    async def send_to_app(self, unique_id: str, message: Dict[str, Any]) -> bool:
        """
        Send a WebSocket message to a connected app using the correct Home Assistant WebSocket API protocol.

        For push notifications (unsolicited messages from Home Assistant to app), we use event_message().
        For responses to app requests, we use result_message() with the app's message ID.

        Args:
            unique_id: The unique identifier for the app
            message: The message to send

        Returns:
            bool: True if message was sent successfully, False otherwise
        """
        if unique_id not in self._websocket_connections:
            self.logger.warning(f"Cannot send message to app '{unique_id}': not connected")
            return False

        try:
            connection = self._websocket_connections[unique_id]
            # Send message directly to the connection
            connection.send_message(message)
            return True
        except Exception as e:
            self.logger.error(f"Failed to send message to app '{unique_id}': {e}")
            # Mark connection as potentially broken
            await self._handle_connection_failure(unique_id, str(e))
            return False

    async def emit_event(self, event_type: str, data: Optional[Dict[str, Any]] = None) -> bool:
        """
        Emit an event to all connected apps via WebSocket.

        Args:
            event_type: The type of event to emit
            data: Optional data to merge into the event object

        Returns:
            bool: True if event was sent to at least one app successfully, False otherwise
        """
        if not self._websocket_connections:
            self.logger.warning("No WebSocket connections available to emit event")
            return False

        # Build the event message
        event_message = {
            "type": f"synapse/{event_type}",
            "event": {
            }
        }

        # Merge optional data into the event object
        if data:
            event_message["event"].update(data)

        # Send to all connected apps
        success_count = 0
        for unique_id in list(self._websocket_connections.keys()):
            try:
                success = await self.send_to_app(unique_id, event_message)
                if success:
                    success_count += 1
            except Exception as e:
                self.logger.error(f"Failed to emit event to {unique_id}: {e}")

        return success_count > 0

    async def _handle_connection_failure(self, unique_id: str, error: str) -> None:
        """
        Handle connection failure - immediately mark as offline.

        Args:
            unique_id: The unique identifier for the failed connection
            error: The error that caused the failure
        """
        self.logger.warning(f"Connection failure for app '{unique_id}': {error}")

        # Immediately mark as offline and unregister the broken connection
        if unique_id in self._websocket_connections:
            self.unregister_websocket_connection(unique_id)
            # Fire health event to update entity availability
            self.hass.bus.async_fire(self.event_name("health"))

    def is_unique_id_connected(self, unique_id: str) -> bool:
        """
        Check if a unique_id already has an active WebSocket connection.

        Args:
            unique_id: The unique identifier to check

        Returns:
            bool: True if already connected, False otherwise
        """
        return unique_id in self._websocket_connections

    def is_app_registered(self, unique_id: str) -> bool:
        """
        Check if the unique_id corresponds to a registered app in config.

        Args:
            unique_id: The unique identifier to check

        Returns:
            bool: True if app is registered, False otherwise
        """
        # Look through all config entries for this domain
        config_entries = self.hass.config_entries.async_entries(DOMAIN)

        for entry in config_entries:
            if entry.data.get("unique_id") == unique_id:
                return True

        return False

    def get_connection_health(self, unique_id: str) -> Dict[str, Any]:
        """
        Get health information for a specific connection.

        Args:
            unique_id: The unique identifier for the connection

        Returns:
            Dict containing connection health information
        """
        if unique_id not in self._websocket_connections:
            return {
                "connected": False,
                "error": "Connection not found"
            }

        connection_time = self._connection_timestamps.get(unique_id, 0)
        uptime = time.time() - connection_time if connection_time > 0 else 0

        return {
            "connected": True,
            "uptime_seconds": int(uptime),
            "online": self.online,
            "last_heartbeat": self._last_heartbeat_time
        }

    async def get_abandoned_entities(self, unique_id: str) -> Dict[str, Any]:
        """
        Find and log all entities that share a unique_id with the app but are not currently owned by the app.
        These entities would be in the unavailable condition due to not being in the current configuration.

        Args:
            unique_id: The unique identifier for the app

        Returns:
            Dict containing abandoned entities information
        """

        try:
            # Get the entity registry
            entity_registry = er.async_get(self.hass)

            # Get all entities for this platform (synapse)
            all_synapse_entities = []
            for entity_id, entity_entry in entity_registry.entities.items():
                if entity_entry.platform == DOMAIN and entity_entry.config_entry_id == self.config_entry.entry_id:
                    all_synapse_entities.append({
                        "entity_id": entity_id,
                        "unique_id": entity_entry.unique_id,
                        "domain": entity_entry.domain,
                        "name": entity_entry.name or entity_entry.original_name,
                        "disabled": entity_entry.disabled
                    })


            # Find entities that are not in the current configuration
            abandoned_entities = []
            current_entity_unique_ids = set()

            # Collect all unique_ids from current configuration
            for domain, entities in self._current_entities.items():
                current_entity_unique_ids.update(entities)

            # Also check current dynamic configuration
            if self._current_configuration:
                for domain in ENTITY_DOMAINS:
                    entities = self._current_configuration.get(domain, [])
                    if isinstance(entities, list):
                        for entity_data in entities:
                            if isinstance(entity_data, dict) and entity_data.get("unique_id"):
                                current_entity_unique_ids.add(entity_data.get("unique_id"))


            # Find abandoned entities (exist in registry but not in current configuration)
            for entity_info in all_synapse_entities:
                entity_unique_id = entity_info["unique_id"]

                # Skip generated entities (created by Python code, not app registration)
                if self.is_generated_entity(entity_unique_id):
                    continue

                if entity_unique_id not in current_entity_unique_ids:
                    # This entity exists in the registry but not in current configuration
                    abandoned_entities.append(entity_info)
                    self.logger.warning(f"ABANDONED ENTITY: {entity_info['entity_id']} ({entity_info['name']}) - unique_id: {entity_unique_id}, domain: {entity_info['domain']}")

            # Count generated entities for logging
            generated_entities_count = 0
            for entity_info in all_synapse_entities:
                if self.is_generated_entity(entity_info["unique_id"]):
                    generated_entities_count += 1

            # Log summary
            if abandoned_entities:
                self.logger.warning(f"Found {len(abandoned_entities)} abandoned entities for app '{unique_id}':")
                for entity in abandoned_entities:
                    self.logger.warning(f"  - {entity['entity_id']} ({entity['name']}) - {entity['unique_id']}")
            else:
                self.logger.info(f"No abandoned entities found for app '{unique_id}'")

            return {
                "success": True,
                "abandoned_entities": abandoned_entities,
                "total_abandoned": len(abandoned_entities),
                "total_registry_entities": len(all_synapse_entities),
                "generated_entities_count": generated_entities_count,
                "current_configuration_entities": len(current_entity_unique_ids),
                "app_unique_id": unique_id,
                "cleanup_mode": self.get_cleanup_mode()
            }

        except Exception as e:
            self.logger.error(f"Error checking for abandoned entities: {e}")
            return {
                "success": False,
                "error": f"Failed to check abandoned entities: {str(e)}",
                "app_unique_id": unique_id
            }

    async def handle_entity_patch(self, entity_unique_id: str, patch_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle simple entity patching - just update the entity data if it exists.

        Args:
            entity_unique_id: The unique identifier for the entity
            patch_data: The data to patch into the entity

        Returns:
            Dict containing success status and response data
        """

        try:
            # Validate patch data structure
            if not isinstance(patch_data, dict):
                return {
                    "success": False,
                    "error_code": SynapseErrorCodes.INVALID_MESSAGE_FORMAT,
                    "message": "Patch data must be a dictionary",
                    "entity_unique_id": entity_unique_id
                }

            # Find the entity in our tracking
            entity_found = False
            entity_domain = None
            for domain, entities in self._current_entities.items():
                if entity_unique_id in entities:
                    entity_found = True
                    entity_domain = domain
                    break

            if not entity_found:
                return {
                    "success": False,
                    "error_code": SynapseErrorCodes.ENTITY_VALIDATION_FAILED,
                    "message": f"Entity {entity_unique_id} not found - entity may not be loaded",
                    "entity_unique_id": entity_unique_id
                }

            # Fire entity update event for the specific entity
            self.hass.bus.async_fire(
                self.event_name("update"),
                {
                    "unique_id": entity_unique_id,
                    "data": patch_data,
                    "timestamp": self.hass.states.get("sensor.time").state if self.hass.states.get("sensor.time") else None
                }
            )


            return {
                "success": True,
                "patched": True,
                "message": f"Entity patch processed for {entity_unique_id}",
                "entity_unique_id": entity_unique_id,
                "domain": entity_domain
            }

        except Exception as e:
            self.logger.error(f"Error handling entity patch for {entity_unique_id}: {e}")
            return {
                "success": False,
                "error_code": SynapseErrorCodes.UPDATE_FAILED,
                "message": f"Entity patch failed: {str(e)}",
                "entity_unique_id": entity_unique_id
            }

    def _load_persisted_hashes(self) -> None:
        """Load persisted hashes from config entry data."""
        try:
            # Get hashes from config entry data
            persisted_hashes = self.config_entry.data.get("_persisted_hashes", {})
            if isinstance(persisted_hashes, dict):
                self._hash_dict.update(persisted_hashes)
            else:
                self.logger.warning("Invalid persisted hashes format in config entry")
        except Exception as e:
            self.logger.error(f"Error loading persisted hashes: {e}")

    async def _persist_hashes(self) -> None:
        """Persist hashes to config entry data."""
        try:
            # Create new data with persisted hashes
            new_data = dict(self.config_entry.data)
            new_data["_persisted_hashes"] = self._hash_dict

            # Update the config entry
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                data=new_data
            )
        except Exception as e:
            self.logger.error(f"Error persisting hashes: {e}")

    def get_last_known_hash(self, unique_id: str) -> str:
        """
        Get the last known hash for this app.

        Args:
            unique_id: The unique identifier to get hash for

        Returns:
            str: The last known hash or empty string if not found
        """
        return self._hash_dict.get(unique_id, "")

    def get_cleanup_mode(self) -> str:
        """
        Get the cleanup mode for this bridge.

        Returns:
            str: The cleanup mode ("delete" or "abandon"), defaults to "delete"
        """
        return self._cleanup_mode

    def register_generated_entity(self, unique_id: str) -> None:
        """
        Register an entity as generated by Python code (not by app registration).

        Args:
            unique_id: The unique identifier for the generated entity
        """
        self._generated_entities.add(unique_id)

    def unregister_generated_entity(self, unique_id: str) -> None:
        """
        Unregister a generated entity.

        Args:
            unique_id: The unique identifier for the generated entity
        """
        self._generated_entities.discard(unique_id)

    def is_generated_entity(self, unique_id: str) -> bool:
        """
        Check if an entity is generated by Python code (not by app registration).

        Args:
            unique_id: The unique identifier for the entity

        Returns:
            bool: True if the entity is generated by Python code, False otherwise
        """
        return unique_id in self._generated_entities

    async def _update_hash(self, unique_id: str, hash_value: str) -> None:
        """
        Update hash for an app and persist it.

        Args:
            unique_id: The unique identifier for the app
            hash_value: The new hash value
        """
        self._hash_dict[unique_id] = hash_value
        await self._persist_hashes()

    def _reset_heartbeat_timer(self) -> None:
        """Reset the heartbeat timer to wait for the next heartbeat."""
        if self._heartbeat_timer:
            self._heartbeat_timer.cancel()

        # Set timer for APP_OFFLINE_DELAY seconds
        self._heartbeat_timer = self.hass.loop.call_later(
            APP_OFFLINE_DELAY,
            self._handle_heartbeat_timeout
        )

    def _handle_heartbeat_timeout(self) -> None:
        """Handle heartbeat timeout - mark app as offline."""
        if not self._websocket_connections:
            return  # No connections to monitor

        self.logger.warning(f"App '{self.app_name}' heartbeat timeout - marking offline")
        self.online = False

        # Fire health event to update entity availability
        self.hass.bus.async_fire(self.event_name("health"))

    async def _send_re_registration_request(self, unique_id: str) -> bool:
        """
        Send a re-registration request to an app.

        This tells the app to resend its registration message. Used when:
        - Hash drift is detected (config changed)
        - Connection desync is detected
        - Manual reload is requested

        Args:
            unique_id: The unique identifier for the app

        Returns:
            bool: True if message was sent successfully, False otherwise
        """
        re_registration_message = {
            "type": "event",
            "event": {
                "event_type": "synapse/request_re_registration",
                "data": {
                    "unique_id": unique_id,
                    "message": "Re-registration requested - please resend registration",
                    "action": "resend_registration"
                }
            }
        }
        return await self.send_to_app(unique_id, re_registration_message)

    async def handle_registration(self, unique_id: str, app_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle app registration via WebSocket.

        This is the "hello world" message handler that validates the registration
        and returns the appropriate response.

        Args:
            unique_id: The unique identifier for the app
            app_metadata: The app metadata from the registration message

        Returns:
            Dict containing success status, error codes, and response data
        """

        # Step 1: Check if unique_id is already connected
        if self.is_unique_id_connected(unique_id):
            self.logger.warning(f"Registration failed: app '{unique_id}' is already connected")
            return {
                "success": False,
                "error_code": SynapseErrorCodes.ALREADY_CONNECTED,
                "message": f"Unique ID {unique_id} is already connected",
                "unique_id": unique_id
            }

        # Step 2: Check if app is registered in config
        if not self.is_app_registered(unique_id):
            self.logger.warning(f"Registration failed: app '{unique_id}' is not registered")
            return {
                "success": False,
                "error_code": SynapseErrorCodes.NOT_REGISTERED,
                "message": f"App with unique_id {unique_id} is not registered",
                "unique_id": unique_id
            }

        # Step 3: Get last known hash and check for changes
        last_known_hash = self.get_last_known_hash(unique_id)
        current_hash = app_metadata.get("hash", "")

        # Check if hash has changed since last connection
        hash_changed = False
        if last_known_hash and current_hash and last_known_hash != current_hash:
            self.logger.info(f"Configuration changed for app '{unique_id}', requesting re-registration")
            hash_changed = True

            # Request re-registration to sync configuration
            sent_successfully = await self._send_re_registration_request(unique_id)

            if not sent_successfully:
                self.logger.warning(f"Failed to send re-registration request during registration for app '{unique_id}'")
        elif not last_known_hash and current_hash:
            self.logger.info(f"First time registration for app '{unique_id}'")
        elif not current_hash:
            self.logger.warning(f"No hash provided in registration for app '{unique_id}'")

        # Step 4: Store cleanup metadata from registration
        cleanup_mode = app_metadata.get("cleanup", "delete")
        self._cleanup_mode = cleanup_mode

        # Step 5: Process app metadata (entities, hash, etc.)
        self.logger.info(f"Processing app metadata for reconnection of '{unique_id}'")
        metadata_result = await self._process_app_metadata(unique_id, app_metadata)
        if not metadata_result["success"]:
            self.logger.error(f"Failed to process app metadata during registration: {metadata_result.get('error')}")
            return {
                "success": False,
                "error_code": SynapseErrorCodes.REGISTRATION_FAILED,
                "message": f"Failed to process app metadata: {metadata_result.get('error')}",
                "unique_id": unique_id
            }

        # Step 6: Registration successful
        self.logger.info(f"Registration successful for app '{unique_id}'")

        return {
            "success": True,
            "registered": True,
            "last_known_hash": last_known_hash,
            "current_hash": current_hash,
            "hash_changed": hash_changed,
            "configuration_requested": hash_changed,
            "message": "Registration successful" + (" - configuration sync requested" if hash_changed else ""),
            "unique_id": unique_id
        }

    async def handle_heartbeat(self, unique_id: str, current_hash: str, connection: Any = None) -> Dict[str, Any]:
        """
        Handle heartbeat from app via WebSocket.

        Args:
            unique_id: The unique identifier for the app
            current_hash: The current configuration hash from the app
            connection: Optional WebSocket connection object (for re-registration when coming back online)

        Returns:
            Dict containing heartbeat response and any configuration requests
        """
        # Update heartbeat tracking
        self._last_heartbeat_time = time.time()
        self._reset_heartbeat_timer()

        # Check if this is the first heartbeat (going from offline to online)
        was_offline = not self.online
        self.online = True

        if was_offline:
            self.logger.info(f"App '{self.app_name}' restored contact via heartbeat")

            # Re-register the connection to ensure it's up-to-date (wipes out previous reference)
            if connection is not None:
                self.logger.info(f"Re-registering connection for '{unique_id}' after heartbeat restore")
                # Update the connection reference and reset timers
                self._websocket_connections[unique_id] = connection
                self._connection_timestamps[unique_id] = time.time()
                self._reset_connection_timeout(unique_id)

            # Fire health event to update entity availability
            self.hass.bus.async_fire(self.event_name("health"))

        # Get the last known hash for this app
        last_known_hash = self.get_last_known_hash(unique_id)

        # Check for hash drift
        if last_known_hash and current_hash != last_known_hash:
            self.logger.info(f"Configuration drift detected for app '{unique_id}', requesting re-registration")

            # Request re-registration to sync configuration
            sent_successfully = await self._send_re_registration_request(unique_id)

            if sent_successfully:
                return {
                    "success": True,
                    "heartbeat_received": True,
                    "hash_drift_detected": True,
                    "re_registration_requested": True,
                    "message": "Hash drift detected - re-registration requested",
                    "last_known_hash": last_known_hash,
                    "current_hash": current_hash
                }
            else:
                return {
                    "success": False,
                    "heartbeat_received": True,
                    "hash_drift_detected": True,
                    "re_registration_requested": False,
                    "message": "Hash drift detected but failed to send re-registration request",
                    "last_known_hash": last_known_hash,
                    "current_hash": current_hash
                }

        # Normal heartbeat - no hash drift
        return {
            "success": True,
            "heartbeat_received": True,
            "hash_drift_detected": False,
            "re_registration_requested": False,
            "message": "Heartbeat received - hash unchanged"
        }

    async def handle_going_offline(self, unique_id: str) -> Dict[str, Any]:
        """
        Handle graceful app shutdown via WebSocket.

        This is called when an app sends a "going offline" message before
        shutting down gracefully (e.g., on SIGINT).

        Args:
            unique_id: The unique identifier for the app

        Returns:
            Dict containing success status and response data
        """
        self.logger.info(f"App '{unique_id}' going offline gracefully")

        # Immediately mark as offline
        self.online = False

        # Clean up WebSocket connection
        self.unregister_websocket_connection(unique_id)

        # Cancel heartbeat timer since app is going offline
        if self._heartbeat_timer:
            self._heartbeat_timer.cancel()
            self._heartbeat_timer = None

        # Fire health event to update entity availability
        self.hass.bus.async_fire(self.event_name("health"))

        self.logger.info(f"App '{unique_id}' marked as offline - graceful shutdown complete")

        return {
            "success": True,
            "offline": True,
            "message": "App marked as offline - graceful shutdown complete",
            "unique_id": unique_id
        }

    async def handle_entity_update(self, entity_unique_id: str, changes: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle entity update from app via WebSocket.

        This processes runtime entity patches (state, icon, attributes, etc.)
        that don't change the configuration hash.
        """

        try:
            # Validate changes structure
            if not isinstance(changes, dict):
                return {
                    "success": False,
                    "error_code": SynapseErrorCodes.INVALID_MESSAGE_FORMAT,
                    "message": "Changes must be a dictionary",
                    "entity_unique_id": entity_unique_id
                }

            # Validate entity exists in our tracking
            entity_found = False
            entity_domain = None
            for domain, entities in self._current_entities.items():
                if entity_unique_id in entities:
                    entity_found = True
                    entity_domain = domain
                    break

            if not entity_found:
                return {
                    "success": False,
                    "error_code": SynapseErrorCodes.ENTITY_VALIDATION_FAILED,
                    "message": f"Entity {entity_unique_id} not found in current configuration",
                    "entity_unique_id": entity_unique_id
                }

            # Validate changes against allowed update fields
            allowed_update_fields = {
                "name", "icon", "attributes", "state", "device_class",
                "entity_category", "translation_key", "labels", "area_id"
            }

            invalid_fields = set(changes.keys()) - allowed_update_fields
            if invalid_fields:
                return {
                    "success": False,
                    "error_code": SynapseErrorCodes.ENTITY_VALIDATION_FAILED,
                    "message": f"Invalid update fields: {list(invalid_fields)}. Allowed fields: {list(allowed_update_fields)}",
                    "entity_unique_id": entity_unique_id
                }

            # Validate specific field types and values
            validation_errors = []

            for field, value in changes.items():
                if value is not None:  # Allow setting to None for removal
                    if field == "name":
                        if not isinstance(value, str):
                            validation_errors.append("name must be a string")
                        elif len(value.strip()) == 0:
                            validation_errors.append("name cannot be empty")
                        elif len(value) > 255:
                            validation_errors.append("name cannot exceed 255 characters")

                    elif field == "icon":
                        if not isinstance(value, str):
                            validation_errors.append("icon must be a string")
                        elif len(value.strip()) == 0:
                            validation_errors.append("icon cannot be empty")
                        elif not value.startswith("mdi:"):
                            validation_errors.append("icon must start with 'mdi:'")

                    elif field == "attributes":
                        if not isinstance(value, dict):
                            validation_errors.append("attributes must be a dictionary")
                        else:
                            # Validate individual attributes
                            for attr_key, attr_value in value.items():
                                if not isinstance(attr_key, str):
                                    validation_errors.append(f"Attribute key '{attr_key}' must be a string")
                                    break
                                if len(attr_key) > 255:
                                    validation_errors.append(f"Attribute key '{attr_key}' cannot exceed 255 characters")
                                    break

                                # Check for JSON serializable values
                                if isinstance(attr_value, (dict, list)):
                                    try:
                                        json.dumps(attr_value)
                                    except (TypeError, ValueError):
                                        validation_errors.append(f"Attribute value for '{attr_key}' is not JSON serializable")
                                        break

                    elif field == "labels":
                        if not isinstance(value, list):
                            validation_errors.append("labels must be a list")
                        else:
                            for label in value:
                                if not isinstance(label, str):
                                    validation_errors.append("All labels must be strings")
                                    break
                                if len(label) > 255:
                                    validation_errors.append(f"Label '{label}' cannot exceed 255 characters")
                                    break

                    elif field == "area_id":
                        if not isinstance(value, str):
                            validation_errors.append("area_id must be a string")
                        elif len(value.strip()) == 0:
                            validation_errors.append("area_id cannot be empty")

                    elif field == "state":
                        # State validation depends on entity domain
                        if entity_domain == "sensor":
                            # Sensors can have numeric or string states
                            if not isinstance(value, (str, int, float)):
                                validation_errors.append("sensor state must be a string, integer, or float")
                        elif entity_domain == "binary_sensor":
                            # Binary sensors typically have "on"/"off" states
                            if not isinstance(value, str) or value not in ["on", "off", "unavailable"]:
                                validation_errors.append("binary_sensor state must be 'on', 'off', or 'unavailable'")
                        elif entity_domain == "switch":
                            # Switches typically have "on"/"off" states
                            if not isinstance(value, str) or value not in ["on", "off", "unavailable"]:
                                validation_errors.append("switch state must be 'on', 'off', or 'unavailable'")
                        else:
                            # For other domains, allow string states
                            if not isinstance(value, str):
                                validation_errors.append("state must be a string")

            # Validate entity_category if present
            entity_category = changes.get("entity_category")
            if entity_category is not None:
                valid_categories = ["config", "diagnostic"]
                if entity_category not in valid_categories:
                    validation_errors.append(f"entity_category must be one of {valid_categories}")

            # Validate device_class if present
            device_class = changes.get("device_class")
            if device_class is not None:
                if not isinstance(device_class, str):
                    validation_errors.append("device_class must be a string")
                elif len(device_class.strip()) == 0:
                    validation_errors.append("device_class cannot be empty")

            # Check for validation errors
            if validation_errors:
                error_message = "; ".join(validation_errors)
                return {
                    "success": False,
                    "error_code": SynapseErrorCodes.ENTITY_VALIDATION_FAILED,
                    "message": f"Validation failed: {error_message}",
                    "entity_unique_id": entity_unique_id,
                    "validation_errors": validation_errors
                }

            # Fire entity update event for the specific entity
            self.hass.bus.async_fire(
                self.event_name("update"),
                {
                    "unique_id": entity_unique_id,
                    "data": changes,
                    "timestamp": self.hass.states.get("sensor.time").state if self.hass.states.get("sensor.time") else None
                }
            )


            return {
                "success": True,
                "updated": True,
                "message": f"Entity update processed for {entity_unique_id}",
                "entity_unique_id": entity_unique_id,
                "domain": entity_domain
            }

        except Exception as e:
            self.logger.error(f"Error handling entity update for {entity_unique_id}: {e}")
            return {
                "success": False,
                "error_code": SynapseErrorCodes.UPDATE_FAILED,
                "message": f"Entity update failed: {str(e)}",
                "entity_unique_id": entity_unique_id
            }

    async def _process_app_metadata(self, unique_id: str, app_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process app metadata (from registration or configuration update).

        This shared function handles the common logic for processing entity configuration
        and updating metadata from both registration and configuration update flows.

        Args:
            unique_id: The unique identifier for the app
            app_metadata: The app metadata containing entity configuration

        Returns:
            Dict containing processing results
        """

        # Extract entity configuration from metadata
        entity_config = {}
        for domain in ENTITY_DOMAINS:
            if domain in app_metadata:
                entity_config[domain] = app_metadata[domain]

        # Extract service configuration from metadata
        service_config = {}
        for domain in SERVICE_DOMAINS:
            if domain in app_metadata:
                service_config[domain] = app_metadata[domain]

        # Update current configuration (includes services for tracking)
        self._current_configuration = entity_config.copy()
        if service_config:
            self._current_configuration.update(service_config)

        # Store device info from registration metadata temporarily so devices can be created
        # Note: self.app_data is read-only (mappingproxy), so we store device info separately
        if "device" in app_metadata:
            self._registration_device = app_metadata["device"]
        else:
            self._registration_device = None
        if "secondary_devices" in app_metadata:
            self._registration_secondary_devices = app_metadata["secondary_devices"]
        else:
            self._registration_secondary_devices = []

        # Process entities if present
        if entity_config:
            self.logger.info(f"Processing {sum(len(entities) for entities in entity_config.values() if isinstance(entities, list))} entities from app metadata")
            try:
                await self._process_configuration(entity_config)
            except Exception as e:
                self.logger.error(f"Error processing entities from metadata: {e}")
                return {
                    "success": False,
                    "error": f"Entity processing failed: {str(e)}"
                }

        # Process services (including empty service_config to cleanup orphaned services)
        # Check if any service domains exist in app_metadata
        has_service_domains = any(domain in app_metadata for domain in SERVICE_DOMAINS)
        total_services = sum(len(services) for services in service_config.values() if isinstance(services, list))

        if has_service_domains:
            self.logger.info(f"Processing {total_services} services from app metadata (current tracked: {len(self._current_services)})")
            try:
                await self._process_services(service_config)
            except Exception as e:
                self.logger.error(f"Error processing services from metadata: {e}")
                return {
                    "success": False,
                    "error": f"Service processing failed: {str(e)}"
                }
        elif self._current_services:
            # If no services in config but we have tracked services, clean them up
            self.logger.info(f"No services in config but {len(self._current_services)} are tracked - cleaning up orphaned services")
            await self._remove_orphaned_services(self._current_services.copy())
            self._current_services.clear()

        # Update hash if provided
        current_hash = app_metadata.get("hash", "")
        if current_hash:
            await self._update_hash(unique_id, current_hash)

        # Fire registration event to invalidate entity configuration caches
        self.hass.bus.async_fire(self.event_name("register"), {
            "unique_id": unique_id,
            "entity_config": entity_config
        })

        return {
            "success": True,
            "entity_config": entity_config,
            "hash_updated": bool(current_hash)
        }

    async def handle_configuration_update(self, configuration: Dict[str, Any], unique_id: str = None, app_metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Handle full configuration update from app via WebSocket.

        This processes the storage.dump() response from the app, or app metadata
        if provided (for cases where the app sends metadata with configuration).

        Args:
            configuration: The configuration data (from storage.dump() or app_metadata)
            unique_id: Optional unique_id (if not provided, uses bridge's metadata_unique_id)
            app_metadata: Optional app metadata (if provided, processes metadata instead of configuration)
        """

        try:
            # Use provided unique_id or fall back to bridge's metadata_unique_id
            target_unique_id = unique_id or self.metadata_unique_id

            # If app_metadata is provided, process it directly
            if app_metadata:
                result = await self._process_app_metadata(target_unique_id, app_metadata)

                if result["success"]:
                    return {
                        "success": True,
                        "configuration_updated": True,
                        "message": "Configuration update with metadata completed successfully"
                    }
                else:
                    return {
                        "success": False,
                        "error_code": SynapseErrorCodes.CONFIGURATION_UPDATE_FAILED,
                        "message": result.get("error", "Configuration update failed")
                    }

            # Otherwise, process as traditional configuration update
            # Validate configuration structure
            if not isinstance(configuration, dict):
                raise ValueError("Configuration must be a dictionary")

            # Process the configuration update
            await self._process_configuration(configuration)

            # Update hash for this app with persistence
            new_hash = configuration.get("hash", "")
            if new_hash:
                await self._update_hash(target_unique_id, new_hash)

            # Fire registration event to invalidate entity configuration caches
            self.hass.bus.async_fire(self.event_name("register"))

            return {
                "success": True,
                "configuration_updated": True,
                "message": "Configuration update completed successfully"
            }

        except Exception as e:
            self.logger.error(f"Configuration update failed: {e}")
            return {
                "success": False,
                "error_code": SynapseErrorCodes.CONFIGURATION_UPDATE_FAILED,
                "message": f"Configuration update failed: {str(e)}"
            }

    async def _process_configuration(self, configuration: Dict[str, Any]) -> None:
        """
        Process the configuration update from storage.dump().

        Args:
            configuration: The configuration data from storage.dump()
        """
        # Log entity counts by domain
        total_entities = 0
        for domain, entities in configuration.items():
            if isinstance(entities, list):
                total_entities += len(entities)
            else:
                self.logger.warning(f"  {domain}: invalid format (expected list, got {type(entities).__name__})")

        self.logger.info(f"Processing configuration update with {total_entities} entities across {len(configuration)} domains")

        # Store the current configuration for entity availability checks
        self._current_configuration = configuration

        # Refresh devices first
        self.logger.debug("Refreshing devices before entity refresh")
        await self._refresh_devices()

        # Refresh entities for each domain
        self.logger.debug("Refreshing entities for all domains")
        await self._refresh_entities(configuration)

    def format_device_info(self, device: Optional[SynapseMetadata] = None) -> Dict[str, Any]:
        """Translate between synapse data objects and hass device info."""
        if device is None:
            device = self.app_data.get("device")

        # Use device unique_id if provided, otherwise use metadata_unique_id as fallback
        device_unique_id = device.get("unique_id") if device else None
        if not device_unique_id:
            device_unique_id = self.metadata_unique_id

        identifiers = {(DOMAIN, device_unique_id)}
        connections = set()

        return DeviceInfo(
            identifiers=identifiers,
            connections=connections,
            name=device.get("name") if device else None,
            manufacturer=(device.get("manufacturer") or device.get("default_manufacturer")) if device else None,
            model=(device.get("model") or device.get("default_model")) if device else None,
            hw_version=device.get("hw_version") if device else None,
            sw_version=device.get("sw_version") if device else None,
            serial_number=device.get("serial_number") if device else None,
            suggested_area=device.get("suggested_area") if device else None,
            configuration_url=device.get("configuration_url") if device else None,
        )

    async def async_reload(self) -> None:
        """Reload the bridge and update local info"""

        # Get the actual unique_id from the registered connection (use what app sent, not config entry)
        if not self._websocket_connections:
            self.logger.warning(f"App '{self.app_name}' has no active WebSocket connection for reload")
            return

        # Use the unique_id from the actual registered connection
        connected_unique_id = next(iter(self._websocket_connections.keys()))

        try:
            # Request re-registration from the app
            self.logger.info(f"Requesting re-registration for app '{self.app_name}' (unique_id: {connected_unique_id})")

            # Send re-registration request to the app using the connection's unique_id
            success = await self._send_re_registration_request(connected_unique_id)

            if not success:
                self.logger.warning(f"Failed to send re-registration request to app '{self.app_name}'")
                # Don't set online - connection is broken
                return

            # Don't override online status here - let heartbeat mechanism handle availability
            # The online status should only be set by:
            # 1. Successful registration (register_websocket_connection)
            # 2. Successful heartbeats (handle_heartbeat)
            # 3. Explicit offline messages (handle_going_offline)
            # 4. Connection failures (unregister_websocket_connection)

        except Exception as e:
            self.logger.error(f"Error during reload for app '{self.app_name}': {e}")
            # Don't set online on error

    async def _refresh_devices(self) -> None:
        """Refresh device registry entries"""
        self.logger.debug("Refreshing device registry")

        try:
            # Get device registry
            device_registry = dr.async_get(self.hass)

            # Track new devices
            new_devices = set()

            # Helper function to safely get or create device with config_entry_id migration
            def _safe_get_or_create_device(device_info: Dict[str, Any], device_unique_id: str) -> str:
                """Get or create device, handling config_entry_id migration if needed."""
                # Check if device already exists
                existing_device = device_registry.async_get_device(
                    identifiers=device_info.get("identifiers", {(DOMAIN, device_unique_id)})
                )

                # If device exists with old config_entry_id, migrate it
                if existing_device and existing_device.config_entries:
                    old_entry_id = None
                    for entry_id in existing_device.config_entries:
                        if entry_id != self.config_entry.entry_id:
                            old_entry_id = entry_id
                            break

                    if old_entry_id:
                        # Try to migrate device to new config_entry_id
                        self.logger.info(f"Migrating device {device_unique_id} from config_entry {old_entry_id} to {self.config_entry.entry_id}")
                        try:
                            # Update device to use new config_entry_id
                            device_registry.async_update_device(
                                existing_device.id,
                                add_config_entry_id=self.config_entry.entry_id
                            )
                            # Try to remove old config_entry_id (will fail silently if entry still exists)
                            try:
                                device_registry.async_update_device(
                                    existing_device.id,
                                    remove_config_entry_id=old_entry_id
                                )
                            except Exception:
                                # Old entry might still exist, that's okay
                                pass
                        except Exception as migrate_error:
                            self.logger.warning(f"Failed to migrate device {device_unique_id}: {migrate_error}")

                try:
                    return device_registry.async_get_or_create(
                        config_entry_id=self.config_entry.entry_id,
                        **device_info
                    )
                except HomeAssistantError as e:
                    if "unknown config entry" in str(e).lower() and existing_device:
                        self.logger.warning(f"Device {device_unique_id} has invalid config_entry_id, attempting to fix")
                        try:
                            # Remove invalid config_entry_ids
                            for entry_id in list(existing_device.config_entries):
                                if entry_id not in self.hass.config_entries.async_entry_ids():
                                    device_registry.async_update_device(
                                        existing_device.id,
                                        remove_config_entry_id=entry_id
                                    )
                            # Now try again
                            return device_registry.async_get_or_create(
                                config_entry_id=self.config_entry.entry_id,
                                **device_info
                            )
                        except Exception as fix_error:
                            self.logger.error(f"Failed to fix device {device_unique_id}: {fix_error}")
                            raise
                    else:
                        raise

            # Process primary device - ALWAYS create a primary device
            # Always use metadata_unique_id as the device unique_id (this is the app's unique_id)
            primary_device_unique_id = self.metadata_unique_id

            # Use registration device info if available, otherwise fall back to app_data
            primary_device = self._registration_device or self.app_data.get("device")

            if primary_device:
                # Use the device info from metadata
                device_info = self.format_device_info(primary_device)
            else:
                # Create default device info if no device metadata provided
                device_info = {
                    "identifiers": {(DOMAIN, primary_device_unique_id)},
                    "name": self.app_name,
                    "manufacturer": "Synapse",
                    "model": "Synapse App",
                }

            # Override the identifiers to always use the primary device unique_id
            device_info["identifiers"] = {(DOMAIN, primary_device_unique_id)}
            new_devices.add(primary_device_unique_id)
            device_id = _safe_get_or_create_device(device_info, primary_device_unique_id)
            self.primary_device = device_info
            self.logger.info(f"Created/updated primary device: {primary_device_unique_id}")

            # Process secondary devices
            # Use registration secondary devices if available, otherwise fall back to app_data
            secondary_devices = self._registration_secondary_devices or self.app_data.get("secondary_devices", [])
            for device_data in secondary_devices:
                device_unique_id = device_data.get("unique_id")
                if device_unique_id:
                    new_devices.add(device_unique_id)
                    device_info = self.format_device_info(device_data)
                    device_id = _safe_get_or_create_device(device_info, device_unique_id)
                    self.via_primary_device[device_unique_id] = device_info
                    self.logger.debug(f"Updated secondary device: {device_unique_id}")

            # Remove orphaned devices
            orphaned_devices = self._current_devices - new_devices
            for device_unique_id in orphaned_devices:
                device_entry = device_registry.async_get_device(
                    identifiers={(DOMAIN, device_unique_id)}
                )
                if device_entry:
                    device_registry.async_remove_device(device_entry.id)
                    self.logger.info(f"Removed orphaned device: {device_unique_id}")

            # Update current devices tracking
            self._current_devices = new_devices

            self.logger.debug(f"Device registry refreshed: {len(new_devices)} devices, removed {len(orphaned_devices)}")

        except Exception as e:
            self.logger.error(f"Error refreshing device registry: {e}")

    async def _refresh_entities(self, configuration: Dict[str, Any]) -> None:
        """
        Refresh entity registry entries based on the configuration.

        Args:
            configuration: The configuration data from storage.dump()
        """
        self.logger.info("Refreshing entity registry")

        try:
            # Get entity registry
            entity_registry = er.async_get(self.hass)

            # Track new entities by domain
            new_entities: Dict[str, set] = {}

            self.logger.debug(f"Current entities before refresh: {self._current_entities}")

            # Process each domain
            for domain in PLATFORMS:
                if domain in configuration:
                    entities = configuration[domain]
                    if isinstance(entities, list):
                        self.logger.info(f"Processing {len(entities)} entities for domain: {domain}")
                        new_entities[domain] = set()
                        await self._process_entity_domain(domain, entities, entity_registry, new_entities[domain])
                    else:
                        self.logger.warning(f"Invalid entities format for domain {domain}: expected list, got {type(entities).__name__}")
                else:
                    self.logger.debug(f"No entities found for domain: {domain}")

            # Remove orphaned entities
            self.logger.info("Removing orphaned entities")
            await self._remove_orphaned_entities(entity_registry, new_entities)

            # Update current entities tracking
            self._current_entities = new_entities

            # Log final entity counts
            total_entities = sum(len(entities) for entities in new_entities.values())
            self.logger.info(f"Entity registry refreshed: {total_entities} total entities across {len(new_entities)} domains")

            # Log detailed entity tracking for debugging
            self.logger.debug(f"_current_entities after refresh: {self._current_entities}")
            for domain, entities in self._current_entities.items():
                self.logger.debug(f"  {domain}: {entities}")

        except Exception as e:
            self.logger.error(f"Error refreshing entity registry: {e}")

    def _validate_entity_data(self, entity_data: Dict[str, Any], domain: str) -> tuple[bool, str]:
        """
        Validate entity data against expected structure.

        Args:
            entity_data: The entity configuration data to validate
            domain: The domain name for context

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Basic structure validation
        if not isinstance(entity_data, dict):
            return False, f"Entity data must be a dictionary, got {type(entity_data).__name__}"

        # Required fields validation
        required_fields = ["unique_id", "name"]
        for field in required_fields:
            if field not in entity_data:
                return False, f"Missing required field '{field}' in entity data"

            if not entity_data[field]:
                return False, f"Required field '{field}' cannot be empty"

        # Unique ID format validation
        unique_id = entity_data.get("unique_id", "")
        if not isinstance(unique_id, str):
            return False, f"unique_id must be a string, got {type(unique_id).__name__}"

        if len(unique_id.strip()) == 0:
            return False, "unique_id cannot be empty or whitespace only"

        # Check for invalid characters in unique_id (Home Assistant requirements)
        invalid_chars = ['<', '>', '&', '"', "'"]
        for char in invalid_chars:
            if char in unique_id:
                return False, f"unique_id contains invalid character '{char}'"

        # Name validation
        name = entity_data.get("name", "")
        if not isinstance(name, str):
            return False, f"name must be a string, got {type(name).__name__}"

        if len(name.strip()) == 0:
            return False, "name cannot be empty or whitespace only"

        # Optional field type validation
        optional_fields = {
            "suggested_object_id": str,
            "icon": str,
            "device_class": str,
            "entity_category": str,
            "translation_key": str,
            "attributes": dict,
            "labels": list,
            "area_id": str,
            "device_id": str
        }

        for field, expected_type in optional_fields.items():
            if field in entity_data and entity_data[field] is not None:
                if not isinstance(entity_data[field], expected_type):
                    return False, f"Field '{field}' must be {expected_type.__name__}, got {type(entity_data[field]).__name__}"

        # Domain-specific validation
        if domain == "sensor":
            # Validate sensor-specific fields
            sensor_fields = ["state_class", "native_unit_of_measurement", "unit_of_measurement"]
            for field in sensor_fields:
                if field in entity_data and entity_data[field] is not None:
                    if not isinstance(entity_data[field], str):
                        return False, f"Field '{field}' must be a string, got {type(entity_data[field]).__name__}"

        elif domain == "number":
            # Validate number-specific fields
            number_fields = ["min_value", "max_value", "step"]
            for field in number_fields:
                if field in entity_data and entity_data[field] is not None:
                    if not isinstance(entity_data[field], (int, float)):
                        return False, f"Field '{field}' must be a number, got {type(entity_data[field]).__name__}"

        # Entity category validation
        entity_category = entity_data.get("entity_category")
        if entity_category is not None:
            valid_categories = ["config", "diagnostic"]
            if entity_category not in valid_categories:
                return False, f"entity_category must be one of {valid_categories}, got '{entity_category}'"

        # Attributes validation
        attributes = entity_data.get("attributes")
        if attributes is not None:
            if not isinstance(attributes, dict):
                return False, f"attributes must be a dictionary, got {type(attributes).__name__}"

            # Validate attribute values (basic check)
            for key, value in attributes.items():
                if not isinstance(key, str):
                    return False, f"Attribute key must be a string, got {type(key).__name__}"

                    # Check for invalid attribute value types
                    if isinstance(value, (dict, list)):
                        try:
                            json.dumps(value)
                        except (TypeError, ValueError):
                            return False, f"Attribute value for '{key}' is not JSON serializable"

        return True, ""

    async def _process_entity_domain(self, domain: str, entities: List[Dict[str, Any]], entity_registry: er.EntityRegistry, new_entities_set: set) -> None:
        """
        Process entities for a specific domain.

        Args:
            domain: The domain name (sensor, switch, etc.)
            entities: List of entity configurations
            entity_registry: The entity registry instance
            new_entities_set: Set to track processed entity unique_ids
        """
        self.logger.info(f"Processing {len(entities)} entities for domain: {domain}")

        processed_count = 0
        skipped_count = 0

        for i, entity_data in enumerate(entities):
            entity_name = entity_data.get('name', f'entity-{i}')
            entity_unique_id = entity_data.get('unique_id', f'no-id-{i}')
            self.logger.debug(f"Processing entity {i+1}/{len(entities)}: {entity_name} ({entity_unique_id})")
            try:
                # Comprehensive entity validation
                is_valid, error_message = self._validate_entity_data(entity_data, domain)
                if not is_valid:
                    self.logger.warning(f"Invalid entity data for domain {domain}: {error_message}")
                    self.logger.debug(f"Invalid entity data: {entity_data}")
                    skipped_count += 1
                    continue

                unique_id = entity_data.get("unique_id")

                # Check for duplicate unique_ids within the same domain
                if unique_id in new_entities_set:
                    self.logger.warning(f"Duplicate unique_id '{unique_id}' found in domain {domain}, skipping")
                    skipped_count += 1
                    continue

                # Track this entity
                new_entities_set.add(unique_id)

                # Get device ID for entity
                self.logger.debug(f"Getting device ID for entity {unique_id}")
                device_id = self._get_device_id_for_entity(entity_data)
                self.logger.debug(f"Device ID for entity {unique_id}: {device_id}")

                # Check if entity already exists with potentially invalid config_entry_id
                existing_entity = entity_registry.async_get_entity_id(domain, DOMAIN, unique_id)

                # Create or update entity in registry
                self.logger.debug(f"Creating entity in registry: domain={domain}, unique_id={unique_id}")

                # If entity exists, check if it needs config_entry_id migration
                if existing_entity:
                    existing_entry = entity_registry.async_get(existing_entity)
                    if existing_entry and existing_entry.config_entry_id != self.config_entry.entry_id:
                        # Entity exists with old config_entry_id - migrate it
                        self.logger.info(f"Migrating entity {existing_entity} from config_entry {existing_entry.config_entry_id} to {self.config_entry.entry_id}")
                        try:
                            entity_registry.async_update_entity(
                                existing_entity,
                                config_entry_id=self.config_entry.entry_id
                            )
                        except Exception as migrate_error:
                            self.logger.warning(f"Failed to migrate entity {existing_entity} config_entry_id: {migrate_error}")
                            # Continue to try creating/updating normally

                try:
                    entity_id = entity_registry.async_get_or_create(
                        domain=domain,
                        platform=DOMAIN,
                        unique_id=unique_id,
                        config_entry=self.config_entry,
                        suggested_object_id=entity_data.get("suggested_object_id"),
                        device_id=device_id
                    )
                except ValueError as e:
                    # If validation fails due to config_entry_id, try to fix it
                    if "unknown config entry" in str(e).lower() and existing_entity:
                        self.logger.warning(f"Entity {existing_entity} has invalid config_entry_id, attempting to fix")
                        try:
                            # Remove the invalid config_entry_id first, then recreate
                            entity_registry.async_update_entity(
                                existing_entity,
                                config_entry_id=None
                            )
                            # Now try again
                            entity_id = entity_registry.async_get_or_create(
                                domain=domain,
                                platform=DOMAIN,
                                unique_id=unique_id,
                                config_entry=self.config_entry,
                                suggested_object_id=entity_data.get("suggested_object_id"),
                                device_id=device_id
                            )
                        except Exception as fix_error:
                            self.logger.error(f"Failed to fix entity {existing_entity}: {fix_error}")
                            raise
                    else:
                        raise

                # Update entity properties if provided
                update_data = {}
                if entity_data.get("name"):
                    update_data["name"] = entity_data.get("name")
                if entity_data.get("icon"):
                    update_data["icon"] = entity_data.get("icon")
                if entity_data.get("entity_category"):
                    update_data["entity_category"] = entity_data.get("entity_category")
                if entity_data.get("labels"):
                    update_data["labels"] = entity_data.get("labels")
                if entity_data.get("area_id"):
                    update_data["area_id"] = entity_data.get("area_id")

                if update_data:
                    self.logger.debug(f"Updating entity properties for {entity_id}: {update_data}")
                    entity_registry.async_update_entity(entity_id.entity_id, **update_data)

                # Store entity data for runtime updates
                self.logger.debug(f"Storing entity data for {unique_id}")
                self._entity_registry[unique_id] = {
                    "domain": domain,
                    "data": entity_data,
                    "config_entry_id": self.config_entry.entry_id
                }

                processed_count += 1
                self.logger.info(f"Successfully created/updated entity: {entity_id.entity_id} ({entity_name})")

            except Exception as e:
                self.logger.error(f"Error processing entity {entity_data.get('unique_id', 'unknown')}: {e}")
                self.logger.error(f"Full traceback: {traceback.format_exc()}")
                skipped_count += 1

        self.logger.info(f"Domain {domain}: {processed_count} entities processed, {skipped_count} skipped")

    async def _remove_orphaned_entities(self, entity_registry: er.EntityRegistry, new_entities: Dict[str, set]) -> None:
        """
        Remove entities that are no longer in the configuration.
        Only removes entities if cleanup mode is "delete".

        Args:
            entity_registry: The entity registry instance
            new_entities: Dict mapping domain to set of current entity unique_ids
        """
        cleanup_mode = self.get_cleanup_mode()

        if cleanup_mode != "delete":
            self.logger.debug(f"Cleanup mode is '{cleanup_mode}', skipping entity deletion")
            return

        total_removed = 0

        for domain in PLATFORMS:
            # Get current entities for this domain
            current_entities = self._current_entities.get(domain, set())
            # Get new entities for this domain
            domain_new_entities = new_entities.get(domain, set())

            # Find orphaned entities
            orphaned_entities = current_entities - domain_new_entities

            for unique_id in orphaned_entities:
                try:
                    # Find the entity in the registry
                    entity_entry = entity_registry.async_get_entity_id(domain, DOMAIN, unique_id)
                    if entity_entry:
                        entity_registry.async_remove(entity_entry)
                        self.logger.info(f"Removed orphaned entity: {domain}.{unique_id}")
                        total_removed += 1
                except Exception as e:
                    self.logger.error(f"Error removing orphaned entity {domain}.{unique_id}: {e}")

        if total_removed > 0:
            self.logger.info(f"Removed {total_removed} orphaned entities")

    async def _remove_orphaned_services(self, orphaned_service_unique_ids: set) -> None:
        """
        Remove services that are no longer in the configuration.

        Args:
            orphaned_service_unique_ids: Set of service unique_ids to remove
        """
        if not orphaned_service_unique_ids:
            return

        self.logger.info(f"Removing {len(orphaned_service_unique_ids)} orphaned services")

        for service_unique_id in orphaned_service_unique_ids:
            try:
                service_info = self._service_registry.get(service_unique_id)
                if service_info:
                    service_name = service_info.get("name")
                    service_domain = service_info.get("domain", DOMAIN)

                    if service_name:
                        # Unregister the service from Home Assistant
                        self.hass.services.async_remove(service_domain, service_name)
                        self.logger.info(f"Unregistered service: {service_domain}.{service_name} (unique_id: {service_unique_id})")

                    # Remove from registry
                    del self._service_registry[service_unique_id]
                else:
                    self.logger.warning(f"No service registry entry found for unique_id: {service_unique_id}")

            except Exception as e:
                self.logger.error(f"Error removing service {service_unique_id}: {e}")

    def _get_device_id_for_entity(self, entity_data: Dict[str, Any]) -> Optional[str]:
        """
        Get the device ID for an entity.

        Args:
            entity_data: The entity configuration data

        Returns:
            Optional device ID string to use for entity registration (device registry ID, not unique_id)
        """
        device_registry = dr.async_get(self.hass)
        valid_entry_ids = set(self.hass.config_entries.async_entry_ids())

        def _is_device_valid(device_entry) -> bool:
            """Check if device has at least one valid config_entry_id."""
            if not device_entry or not device_entry.config_entries:
                return False
            # Device is valid if it has at least one config_entry_id that still exists
            return any(entry_id in valid_entry_ids for entry_id in device_entry.config_entries)

        # Check if entity has a specific device_id declared
        declared_device_id = entity_data.get("device_id")
        if declared_device_id:
            # Look up the device in the registry by unique_id
            try:
                device_entry = device_registry.async_get_device(
                    identifiers={(DOMAIN, declared_device_id)}
                )
                if device_entry:
                    if _is_device_valid(device_entry):
                        self.logger.debug(f"Entity {entity_data.get('unique_id')} associated with device {declared_device_id} (registry ID: {device_entry.id})")
                        return device_entry.id
                    else:
                        self.logger.warning(f"Device {declared_device_id} has invalid config_entry_id(s), skipping device association for entity {entity_data.get('unique_id')}")
                        return None
                else:
                    self.logger.warning(f"Device {declared_device_id} not found in registry for entity {entity_data.get('unique_id')}")
                    return None
            except Exception as e:
                self.logger.error(f"Error looking up device {declared_device_id} for entity {entity_data.get('unique_id')}: {e}")
                return None

        # If no device_id specified, associate with primary device
        # The primary device always uses metadata_unique_id as its unique_id
        if self.primary_device:
            primary_device_unique_id = self.metadata_unique_id
            if primary_device_unique_id:
                try:
                    device_entry = device_registry.async_get_device(
                        identifiers={(DOMAIN, primary_device_unique_id)}
                    )
                    if device_entry:
                        if _is_device_valid(device_entry):
                            self.logger.debug(f"Entity {entity_data.get('unique_id')} associated with primary device {primary_device_unique_id}")
                            return device_entry.id
                        else:
                            self.logger.warning(f"Primary device {primary_device_unique_id} has invalid config_entry_id(s), skipping device association for entity {entity_data.get('unique_id')}")
                            return None
                except Exception as e:
                    self.logger.error(f"Error looking up primary device {primary_device_unique_id} for entity {entity_data.get('unique_id')}: {e}")

        # Fallback: no device association
        self.logger.debug(f"Entity {entity_data.get('unique_id')} has no device association")
        return None

    async def _process_services(self, service_config: Dict[str, Any]) -> None:
        """Process service configuration from app metadata.

        Args:
            service_config: Dictionary containing service definitions
        """
        self.logger.info(f"Processing service config: {service_config}")

        # Track new services
        new_services = set()

        for domain, services in service_config.items():
            if not isinstance(services, list):
                self.logger.warning(f"Services for domain {domain} is not a list: {services}")
                continue

            self.logger.info(f"Processing {len(services)} services for domain {domain}")

            for service_def in services:
                self.logger.info(f"Registering service: {service_def}")
                try:
                    await self._register_service(service_def)

                    # Track the service
                    service_unique_id = service_def.get("unique_id")
                    if service_unique_id:
                        new_services.add(service_unique_id)
                except Exception as e:
                    self.logger.error(f"Error registering service {service_def.get('name', 'unknown')}: {e}")

        # Remove orphaned services
        orphaned_services = self._current_services - new_services
        if orphaned_services:
            await self._remove_orphaned_services(orphaned_services)

        # Update current services tracking
        self._current_services = new_services

        self.logger.info(f"Service processing complete: {len(new_services)} active services, {len(orphaned_services)} removed")

    async def _register_service(self, service_def: Dict[str, Any]) -> None:
        """Register a single service with Home Assistant.

        Args:
            service_def: Service definition dictionary matching services.yaml format
        """
        service_name = service_def.get("name", "")
        unique_id = service_def.get("unique_id", "")
        service_domain = service_def.get("domain", DOMAIN)  # Allow custom domain, default to synapse

        if not service_name or not unique_id:
            self.logger.warning(f"Invalid service definition: missing name or unique_id")
            return

        # Check if service is already registered and unregister it first
        if unique_id in self._service_registry:
            existing_service = self._service_registry[unique_id]
            existing_name = existing_service.get("name")
            existing_domain = existing_service.get("domain", DOMAIN)
            self.logger.info(f"Service {existing_domain}.{existing_name} (unique_id: {unique_id}) already registered, unregistering old service")
            try:
                self.hass.services.async_remove(existing_domain, existing_name)
            except Exception as e:
                self.logger.warning(f"Could not unregister old service {existing_domain}.{existing_name}: {e}")

        # Create the service handler
        async def service_handler(call: ServiceCall) -> None:
            """Handle service calls by forwarding to the bridge."""
            try:
                # Forward the service call to the bridge for processing
                result = await self.handle_service_call(unique_id, service_name, call.data)

                # Log the result for debugging
                if result.get("success", False):
                    self.logger.debug(f"Service {service_name} executed successfully")
                else:
                    self.logger.warning(f"Service {service_name} failed: {result.get('error', 'Unknown error')}")

            except Exception as e:
                self.logger.error(f"Error executing service {service_name}: {e}")

        try:
            # Register the service schema first (this creates the UI and validation)
            service_schema = {
                "name": service_def.get("name", service_name),
                "description": service_def.get("description", ""),
            }

            # Add fields if they exist (this creates the UI elements)
            if service_def.get("fields"):
                service_schema["fields"] = service_def["fields"]

            # Add target if it exists (for entity targeting)
            if service_def.get("target"):
                service_schema["target"] = service_def["target"]

            self.logger.info(f"Attempting to register service schema: {service_schema}")

            # Register the service handler first
            self.hass.services.async_register(
                service_domain,
                service_name,
                service_handler
            )

            # Then register the service schema with Home Assistant
            service.async_set_service_schema(self.hass, service_domain, service_name, service_schema)

            # Store service metadata for cleanup
            self._service_registry[unique_id] = {
                "name": service_name,
                "domain": service_domain,
                "definition": service_def
            }

            self.logger.info(f"Successfully registered service: {service_domain}.{service_name} (unique_id: {unique_id})")

        except Exception as e:
            self.logger.error(f"Failed to register service {service_name}: {e}")
            self.logger.error(f"Full traceback: {traceback.format_exc()}")
            raise

    async def handle_service_call(self, service_unique_id: str, service_name: str, service_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle service calls from registered services.

        This method processes service calls that were registered dynamically
        by Synapse applications and forwards them to the appropriate app.

        Args:
            service_unique_id: The unique identifier for the service
            service_name: The name of the service being called
            service_data: The data passed to the service call

        Returns:
            Dict containing success status and response data
        """
        try:
            # Find the WebSocket connection for this app (use the bridge's unique_id)
            connection = None
            for conn_unique_id, conn in self._websocket_connections.items():
                if conn_unique_id == self.metadata_unique_id:
                    connection = conn
                    break

            if not connection:
                return {
                    "success": False,
                    "error_code": SynapseErrorCodes.BRIDGE_NOT_FOUND,
                    "message": f"No active connection found for service {service_name}",
                    "service_name": service_name,
                    "service_unique_id": service_unique_id
                }

            # Send service call to the app via WebSocket
            service_call_id = f"service_call_{int(time.time() * 1000)}"

            # Create the service call message
            service_message = {
                "id": service_call_id,
                "type": "synapse/service_call",
                "service_name": service_name,
                "service_data": service_data,
                "service_unique_id": service_unique_id
            }

            # Send the message
            connection.send_message(service_message)
            self.logger.info(f"Sent service call {service_name} to app: {service_message}")

            # For now, we'll return success immediately
            # In a more sophisticated implementation, you might want to wait for a response
            return {
                "success": True,
                "message": f"Service {service_name} call forwarded to app",
                "service_name": service_name,
                "service_unique_id": service_unique_id,
                "call_id": service_call_id
            }

        except Exception as e:
            self.logger.error(f"Error handling service call {service_name}: {e}")
            self.logger.error(f"Full traceback: {traceback.format_exc()}")
            return {
                "success": False,
                "error_code": SynapseErrorCodes.INTERNAL_ERROR,
                "message": f"Service call failed: {str(e)}",
                "service_name": service_name,
                "service_unique_id": service_unique_id
            }
