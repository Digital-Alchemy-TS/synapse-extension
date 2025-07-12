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
        Send a WebSocket message to a connected app.

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
            # Add a unique message ID for tracking
            import uuid
            message["id"] = str(uuid.uuid4())

            await connection.send_json(message)
            self.logger.debug(f"Sent message to {unique_id}: {message.get('type', 'unknown')}")
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

    def get_last_known_hash(self, unique_id: str) -> str:
        """
        Get the last known hash for this app.

        Args:
            unique_id: The unique identifier to get hash for

        Returns:
            str: The last known hash or empty string if not found
        """
        return self._hash_dict.get(unique_id, "")

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

    async def handle_entity_update(self, entity_unique_id: str, changes: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle entity update from app via WebSocket.

        This processes runtime entity patches (state, icon, attributes, etc.)
        that don't change the configuration hash.
        """
        self.logger.debug(f"Handling entity update for {entity_unique_id}: {changes}")

        try:
            # Validate entity exists in our tracking
            entity_found = False
            for domain, entities in self._current_entities.items():
                if entity_unique_id in entities:
                    entity_found = True
                    break

            if not entity_found:
                self.logger.warning(f"Entity {entity_unique_id} not found in current entities")
                return {
                    "success": False,
                    "error_code": SynapseErrorCodes.UPDATE_FAILED,
                    "message": f"Entity {entity_unique_id} not found",
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

            # Update hash for this app
            self._hash_dict[self.metadata_unique_id] = configuration.get("hash", "")

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

        # TODO: Implement reload logic for WebSocket communication
        # For now, just log that reload was requested
        self.logger.info(f"{self.app_name} reload requested - WebSocket implementation pending")

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

        for entity_data in entities:
            try:
                # Validate entity data
                if not isinstance(entity_data, dict) or "unique_id" not in entity_data:
                    self.logger.warning(f"Invalid entity data for domain {domain}: {entity_data}")
                    continue

                unique_id = entity_data.get("unique_id")
                if not unique_id:
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

                self.logger.debug(f"Processed entity: {entity_id}")

            except Exception as e:
                self.logger.error(f"Error processing entity {entity_data.get('unique_id', 'unknown')}: {e}")

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
            Optional device ID string
        """
        # TODO: Implement device association logic
        # For now, return None (entities will be associated with the primary device)
        return None
