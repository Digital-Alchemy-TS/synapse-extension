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
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional

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

from homeassistant.components import websocket_api

from .const import (
    DOMAIN,
    PLATFORMS,
    SynapseApplication,
    SynapseMetadata,
    SynapseErrorCodes,
    APP_OFFLINE_DELAY,
)


class SynapseBridge:
    """
    - Handle WebSocket comms with the app
    - Provide helper methods for entities
    - Create online sensor
    - Tracks app heartbeat
    """
    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize the bridge"""

        self.logger: logging.Logger = logging.getLogger(__name__)
        self.config_entry: ConfigEntry = config_entry
        self.primary_device: Optional[DeviceInfo] = None
        self.via_primary_device: Dict[str, DeviceInfo] = {}
        self.hass: HomeAssistant = hass
        self.app_data: SynapseApplication = config_entry.data
        self.app_name: str = self.app_data.get("app", "")
        self.metadata_unique_id: str = self.app_data.get("unique_id", "")
        # Instance-based state management (fixes global state issue)
        self._hash_dict: Dict[str, str] = {}
        self._entity_registry: Dict[str, Dict[str, Any]] = {}
        self._device_registry: Dict[str, DeviceInfo] = {}

        # Track current entities and devices for removal detection
        self._current_entities: Dict[str, set] = {}  # domain -> set of unique_ids
        self._current_devices: set = set()  # set of device unique_ids
        hass.data.setdefault(DOMAIN, {})[self.metadata_unique_id] = self

        self.logger.debug(f"{self.app_name} init bridge")

        # WebSocket connection tracking
        self._websocket_connections: Dict[str, Any] = {}
        self.online: bool = False
        self._heartbeat_timer: Optional[asyncio.TimerHandle] = None
        self._last_heartbeat_time: Optional[float] = None

        # Load persisted hashes from config entry data
        self._load_persisted_hashes()

        self.logger.info(f"{self.app_name} bridge initialized - WebSocket ready")

    def event_name(self, event_type: str) -> str:
        """
        Generate event names for this bridge instance.

        Args:
            event_type: The type of event (health, update, etc.)

        Returns:
            str: The full event name for this bridge
        """
        return f"{DOMAIN}/{event_type}/{self.app_name}"

    async def async_cleanup(self) -> None:
        """Called when tearing down the bridge, clean up resources and prepare to go away"""
        self.logger.info(f"{self.app_name} cleanup bridge")
        if self._heartbeat_timer:
            self._heartbeat_timer.cancel()

        # Clean up WebSocket connections
        self._websocket_connections.clear()

    def register_websocket_connection(self, unique_id: str, connection: Any) -> None:
        """Register a WebSocket connection for an app."""
        self.logger.info(f"Registering WebSocket connection for {unique_id}")
        self._websocket_connections[unique_id] = connection
        self._reset_heartbeat_timer()

    def unregister_websocket_connection(self, unique_id: str) -> None:
        """Unregister a WebSocket connection for an app."""
        self.logger.info(f"Unregistering WebSocket connection for {unique_id}")
        if unique_id in self._websocket_connections:
            del self._websocket_connections[unique_id]
            if not self._websocket_connections:
                # No more connections, stop heartbeat monitoring
                if self._heartbeat_timer:
                    self._heartbeat_timer.cancel()
                    self._heartbeat_timer = None
                self.online = False

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
            self.logger.warning(f"Cannot send message to {unique_id}: not connected")
            return False

        try:
            connection = self._websocket_connections[unique_id]
            # For push notifications, use event_message() - no ID needed
            connection.send_message(websocket_api.event_message(message))
            self.logger.debug(f"Sent push notification to {unique_id}: {message.get('type', 'unknown')}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to send message to {unique_id}: {e}")
            return False

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

    def _load_persisted_hashes(self) -> None:
        """Load persisted hashes from config entry data."""
        try:
            # Get hashes from config entry data
            persisted_hashes = self.config_entry.data.get("_persisted_hashes", {})
            if isinstance(persisted_hashes, dict):
                self._hash_dict.update(persisted_hashes)
                self.logger.debug(f"Loaded {len(persisted_hashes)} persisted hashes")
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
            self.logger.debug(f"Persisted {len(self._hash_dict)} hashes to config entry")
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

    async def _update_hash(self, unique_id: str, hash_value: str) -> None:
        """
        Update hash for an app and persist it.

        Args:
            unique_id: The unique identifier for the app
            hash_value: The new hash value
        """
        self._hash_dict[unique_id] = hash_value
        await self._persist_hashes()
        self.logger.debug(f"Updated and persisted hash for {unique_id}: {hash_value}")

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

        self.logger.warning(f"{self.app_name} heartbeat timeout - marking offline")
        self.online = False

        # Fire health event to update entity availability
        self.hass.bus.async_fire(f"{DOMAIN}/health/{self.app_name}")

    def request_configuration(self, unique_id: str) -> Dict[str, Any]:
        """
        Format a configuration request message to send to an app.

        Args:
            unique_id: The unique identifier for the app

        Returns:
            Dict containing the request message
        """
        return {
            "type": "synapse/request_configuration",
            "unique_id": unique_id
        }

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
        self.logger.info(f"Handling registration for {unique_id}")

        # Step 1: Check if unique_id is already connected
        if self.is_unique_id_connected(unique_id):
            self.logger.warning(f"Registration failed: {unique_id} is already connected")
            return {
                "success": False,
                "error_code": SynapseErrorCodes.ALREADY_CONNECTED,
                "message": f"Unique ID {unique_id} is already connected",
                "unique_id": unique_id
            }

        # Step 2: Check if app is registered in config
        if not self.is_app_registered(unique_id):
            self.logger.warning(f"Registration failed: {unique_id} is not registered")
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
            self.logger.info(f"Hash changed during registration for {unique_id}: {last_known_hash} -> {current_hash}")
            hash_changed = True

            # Trigger immediate configuration sync
            request_message = self.request_configuration(unique_id)
            sent_successfully = await self.send_to_app(unique_id, request_message)

            if not sent_successfully:
                self.logger.warning(f"Failed to send configuration request during registration for {unique_id}")

        # Step 4: Registration successful
        self.logger.info(f"Registration successful for {unique_id}")
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

    async def handle_heartbeat(self, unique_id: str, current_hash: str) -> Dict[str, Any]:
        """
        Handle heartbeat from app via WebSocket.

        Args:
            unique_id: The unique identifier for the app
            current_hash: The current configuration hash from the app

        Returns:
            Dict containing heartbeat response and any configuration requests
        """
        import time

        self.logger.debug(f"Handling heartbeat for {unique_id} with hash: {current_hash}")

        # Update heartbeat tracking
        self._last_heartbeat_time = time.time()
        self._reset_heartbeat_timer()

        # Check if this is the first heartbeat (going from offline to online)
        was_offline = not self.online
        self.online = True

        if was_offline:
            self.logger.info(f"{self.app_name} restored contact via heartbeat")
            # Fire health event to update entity availability
            self.hass.bus.async_fire(f"{DOMAIN}/health/{self.app_name}")

        # Get the last known hash for this app
        last_known_hash = self.get_last_known_hash(unique_id)

        # Check for hash drift
        if last_known_hash and current_hash != last_known_hash:
            self.logger.info(f"Hash drift detected for {unique_id}: {last_known_hash} -> {current_hash}")

            # Send configuration request to the app
            request_message = self.request_configuration(unique_id)
            sent_successfully = await self.send_to_app(unique_id, request_message)

            if sent_successfully:
                return {
                    "success": True,
                    "heartbeat_received": True,
                    "hash_drift_detected": True,
                    "request_configuration": True,
                    "message": "Hash drift detected - configuration request sent",
                    "last_known_hash": last_known_hash,
                    "current_hash": current_hash
                }
            else:
                return {
                    "success": False,
                    "heartbeat_received": True,
                    "hash_drift_detected": True,
                    "request_configuration": False,
                    "message": "Hash drift detected but failed to send configuration request",
                    "last_known_hash": last_known_hash,
                    "current_hash": current_hash
                }

        # Normal heartbeat - no hash drift
        return {
            "success": True,
            "heartbeat_received": True,
            "hash_drift_detected": False,
            "request_configuration": False,
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
        self.logger.info(f"App {unique_id} going offline gracefully")

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

        self.logger.info(f"App {unique_id} marked as offline - graceful shutdown complete")

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
        self.logger.debug(f"Handling entity update for {entity_unique_id}: {changes}")

        try:
            # Validate changes structure
            if not isinstance(changes, dict):
                return {
                    "success": False,
                    "error_code": SynapseErrorCodes.UPDATE_FAILED,
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
                self.logger.warning(f"Entity {entity_unique_id} not found in current entities")
                return {
                    "success": False,
                    "error_code": SynapseErrorCodes.UPDATE_FAILED,
                    "message": f"Entity {entity_unique_id} not found",
                    "entity_unique_id": entity_unique_id
                }

            # Validate changes against allowed update fields
            allowed_update_fields = {
                "name", "icon", "attributes", "state", "device_class",
                "entity_category", "translation_key", "labels", "area_id"
            }

            invalid_fields = set(changes.keys()) - allowed_update_fields
            if invalid_fields:
                self.logger.warning(f"Invalid update fields for {entity_unique_id}: {invalid_fields}")
                return {
                    "success": False,
                    "error_code": SynapseErrorCodes.UPDATE_FAILED,
                    "message": f"Invalid update fields: {list(invalid_fields)}",
                    "entity_unique_id": entity_unique_id
                }

            # Validate specific field types
            for field, value in changes.items():
                if value is not None:  # Allow setting to None for removal
                    if field == "name" and not isinstance(value, str):
                        return {
                            "success": False,
                            "error_code": SynapseErrorCodes.UPDATE_FAILED,
                            "message": "name must be a string",
                            "entity_unique_id": entity_unique_id
                        }
                    elif field == "icon" and not isinstance(value, str):
                        return {
                            "success": False,
                            "error_code": SynapseErrorCodes.UPDATE_FAILED,
                            "message": "icon must be a string",
                            "entity_unique_id": entity_unique_id
                        }
                    elif field == "attributes" and not isinstance(value, dict):
                        return {
                            "success": False,
                            "error_code": SynapseErrorCodes.UPDATE_FAILED,
                            "message": "attributes must be a dictionary",
                            "entity_unique_id": entity_unique_id
                        }
                    elif field == "labels" and not isinstance(value, list):
                        return {
                            "success": False,
                            "error_code": SynapseErrorCodes.UPDATE_FAILED,
                            "message": "labels must be a list",
                            "entity_unique_id": entity_unique_id
                        }
                    elif field == "area_id" and not isinstance(value, str):
                        return {
                            "success": False,
                            "error_code": SynapseErrorCodes.UPDATE_FAILED,
                            "message": "area_id must be a string",
                            "entity_unique_id": entity_unique_id
                        }

            # Validate entity_category if present
            entity_category = changes.get("entity_category")
            if entity_category is not None:
                valid_categories = ["config", "diagnostic"]
                if entity_category not in valid_categories:
                    return {
                        "success": False,
                        "error_code": SynapseErrorCodes.UPDATE_FAILED,
                        "message": f"entity_category must be one of {valid_categories}",
                        "entity_unique_id": entity_unique_id
                    }

            # Validate attributes if present
            attributes = changes.get("attributes")
            if attributes is not None:
                for key, value in attributes.items():
                    if not isinstance(key, str):
                        return {
                            "success": False,
                            "error_code": SynapseErrorCodes.UPDATE_FAILED,
                            "message": "Attribute key must be a string",
                            "entity_unique_id": entity_unique_id
                        }

                    # Check for JSON serializable values
                    if isinstance(value, (dict, list)):
                        try:
                            import json
                            json.dumps(value)
                        except (TypeError, ValueError):
                            return {
                                "success": False,
                                "error_code": SynapseErrorCodes.UPDATE_FAILED,
                                "message": f"Attribute value for '{key}' is not JSON serializable",
                                "entity_unique_id": entity_unique_id
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

            self.logger.debug(f"Entity update event fired for {entity_unique_id}")

            return {
                "success": True,
                "updated": True,
                "message": f"Entity update processed for {entity_unique_id}",
                "entity_unique_id": entity_unique_id
            }

        except Exception as e:
            self.logger.error(f"Error handling entity update for {entity_unique_id}: {e}")
            return {
                "success": False,
                "error_code": SynapseErrorCodes.UPDATE_FAILED,
                "message": f"Entity update failed: {str(e)}",
                "entity_unique_id": entity_unique_id
            }

    async def handle_configuration_update(self, configuration: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle full configuration update from app via WebSocket.

        This processes the storage.dump() response from the app.
        """
        self.logger.info("Handling full configuration update")

        try:
            # Validate configuration structure
            if not isinstance(configuration, dict):
                raise ValueError("Configuration must be a dictionary")

            # Process the configuration update
            await self._process_configuration(configuration)

            # Update hash for this app with persistence
            new_hash = configuration.get("hash", "")
            if new_hash:
                await self._update_hash(self.metadata_unique_id, new_hash)

            self.logger.info("Configuration update completed successfully")

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
        self.logger.debug("Processing configuration update")

        # Refresh devices first
        await self._refresh_devices()

        # Refresh entities for each domain
        await self._refresh_entities(configuration)

        self.logger.debug("Configuration processing completed")

    def format_device_info(self, device: Optional[SynapseMetadata] = None) -> Dict[str, Any]:
        """Translate between synapse data objects and hass device info."""
        if device is None:
            device = self.app_data.get("device")

        identifiers = {(DOMAIN, device.get("unique_id"))}
        connections = set()

        return DeviceInfo(
            identifiers=identifiers,
            connections=connections,
            name=device.get("name"),
            manufacturer=device.get("manufacturer") or device.get("default_manufacturer"),
            model=device.get("model") or device.get("default_model"),
            hw_version=device.get("hw_version"),
            sw_version=device.get("sw_version"),
            serial_number=device.get("serial_number"),
            suggested_area=device.get("suggested_area"),
            configuration_url=device.get("configuration_url"),
        )

    async def async_reload(self) -> None:
        """Reload the bridge and update local info"""
        self.logger.debug(f"{self.app_name} request reload")

        # Check if we have an active WebSocket connection
        if not self.is_unique_id_connected(self.metadata_unique_id):
            self.logger.warning(f"{self.app_name} no active WebSocket connection for reload")
            # Still mark as online since this is a manual reload request
            self.online = True
            return

        try:
            # Request configuration update from the app
            self.logger.info(f"{self.app_name} requesting configuration update for reload")

            # Send configuration request to the app
            request_message = {
                "type": "event",
                "event_type": "synapse/request_configuration"
            }

            success = await self.send_to_app(self.metadata_unique_id, request_message)

            if success:
                self.logger.info(f"{self.app_name} configuration request sent successfully")
                # The app should respond with a synapse/update_configuration command
                # which will be handled by handle_configuration_update()
            else:
                self.logger.warning(f"{self.app_name} failed to send configuration request")

        except Exception as e:
            self.logger.error(f"{self.app_name} error during reload: {e}")

        # this counts as a heartbeat
        self.online = True

    async def _refresh_devices(self) -> None:
        """Refresh device registry entries"""
        self.logger.debug("Refreshing device registry")

        try:
            # Get device registry
            device_registry = dr.async_get(self.hass)

            # Track new devices
            new_devices = set()

            # Process primary device
            primary_device = self.app_data.get("device")
            if primary_device:
                device_unique_id = primary_device.get("unique_id")
                if device_unique_id:
                    new_devices.add(device_unique_id)
                    device_info = self.format_device_info(primary_device)
                    device_id = device_registry.async_get_or_create(
                        config_entry_id=self.config_entry.entry_id,
                        **device_info
                    )
                    self.primary_device = device_info
                    self.logger.debug(f"Updated primary device: {device_unique_id}")

            # Process secondary devices
            secondary_devices = self.app_data.get("secondary_devices", [])
            for device_data in secondary_devices:
                device_unique_id = device_data.get("unique_id")
                if device_unique_id:
                    new_devices.add(device_unique_id)
                    device_info = self.format_device_info(device_data)
                    device_id = device_registry.async_get_or_create(
                        config_entry_id=self.config_entry.entry_id,
                        **device_info
                    )
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
        self.logger.debug("Refreshing entity registry")

        try:
            # Get entity registry
            entity_registry = er.async_get(self.hass)

            # Track new entities by domain
            new_entities: Dict[str, set] = {}

            # Process each domain
            for domain in PLATFORMS:
                if domain in configuration:
                    entities = configuration[domain]
                    if isinstance(entities, list):
                        new_entities[domain] = set()
                        await self._process_entity_domain(domain, entities, entity_registry, new_entities[domain])

            # Remove orphaned entities
            await self._remove_orphaned_entities(entity_registry, new_entities)

            # Update current entities tracking
            self._current_entities = new_entities

            self.logger.debug("Entity registry refreshed")

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
                    # These are valid but should be JSON serializable
                    try:
                        import json
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
        self.logger.debug(f"Processing {len(entities)} entities for domain: {domain}")

        processed_count = 0
        skipped_count = 0

        for entity_data in entities:
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

                # Create or update entity in registry
                entity_id = entity_registry.async_get_or_create(
                    domain=domain,
                    platform=DOMAIN,
                    unique_id=unique_id,
                    config_entry=self.config_entry,
                    suggested_object_id=entity_data.get("suggested_object_id"),
                    name=entity_data.get("name"),
                    device_id=self._get_device_id_for_entity(entity_data)
                )

                # Store entity data for runtime updates
                self._entity_registry[unique_id] = {
                    "domain": domain,
                    "data": entity_data,
                    "config_entry_id": self.config_entry.entry_id
                }

                processed_count += 1
                self.logger.debug(f"Processed entity: {entity_id}")

            except Exception as e:
                self.logger.error(f"Error processing entity {entity_data.get('unique_id', 'unknown')}: {e}")
                skipped_count += 1

        self.logger.info(f"Domain {domain}: {processed_count} entities processed, {skipped_count} skipped")

    async def _remove_orphaned_entities(self, entity_registry: er.EntityRegistry, new_entities: Dict[str, set]) -> None:
        """
        Remove entities that are no longer in the configuration.

        Args:
            entity_registry: The entity registry instance
            new_entities: Dict mapping domain to set of current entity unique_ids
        """
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

    def _get_device_id_for_entity(self, entity_data: Dict[str, Any]) -> Optional[str]:
        """
        Get the device ID for an entity.

        Args:
            entity_data: The entity configuration data

        Returns:
            Optional device ID string from the device registry
        """
        # Check if entity has a specific device_id declared
        declared_device_id = entity_data.get("device_id")
        if declared_device_id:
            # Validate that the declared device exists
            if declared_device_id in self._current_devices:
                # Get the device registry to find the actual device ID
                device_registry = dr.async_get(self.hass)
                device_entry = device_registry.async_get_device(
                    identifiers={(DOMAIN, declared_device_id)}
                )
                if device_entry:
                    self.logger.debug(f"Entity {entity_data.get('unique_id')} associated with device {declared_device_id}")
                    return device_entry.id
                else:
                    self.logger.warning(f"Device {declared_device_id} not found in registry for entity {entity_data.get('unique_id')}")
            else:
                self.logger.warning(f"Declared device {declared_device_id} not in current devices for entity {entity_data.get('unique_id')}")

        # If no device_id specified or device not found, associate with primary device
        if self.primary_device:
            device_registry = dr.async_get(self.hass)
            primary_device_unique_id = self.app_data.get("device", {}).get("unique_id")
            if primary_device_unique_id:
                device_entry = device_registry.async_get_device(
                    identifiers={(DOMAIN, primary_device_unique_id)}
                )
                if device_entry:
                    self.logger.debug(f"Entity {entity_data.get('unique_id')} associated with primary device {primary_device_unique_id}")
                    return device_entry.id

        # Fallback: no device association
        self.logger.debug(f"Entity {entity_data.get('unique_id')} has no device association")
        return None
