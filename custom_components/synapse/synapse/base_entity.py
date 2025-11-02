"""
# Digital Alchemy Synapse base entity

This base class is used across the various entity domains:
- associates entity with device
- handles standard entity interactions
- availability
- live configuration updates

It is up to the helper domains to:
- extend this
- override logger
- implement domain specific properties & event callbacks
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from homeassistant.const import EntityCategory
from homeassistant.core import callback, HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity

from .bridge import SynapseBridge
from .const import SynapseBaseEntityData, ENTITY_DOMAINS

class SynapseBaseEntity(Entity):
    """Base entity class for all Synapse entities.

    Provides common functionality for entities from connected NodeJS apps,
    including device association, availability tracking, and live updates.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        bridge: SynapseBridge,
        entity: SynapseBaseEntityData
    ) -> None:
        """Initialize the base entity.

        Args:
            hass: Home Assistant instance
            bridge: Bridge instance for this app
            entity: Entity configuration data
        """
        self.logger: logging.Logger = logging.getLogger(__name__)
        self.hass: HomeAssistant = hass
        self.bridge: SynapseBridge = bridge
        self.entity: SynapseBaseEntityData = entity

        # Cache for configuration existence check
        self._config_exists_cache: Optional[bool] = None
        self._config_cache_valid = False

        # Set up event listeners for entity updates and availability changes
        self.async_on_remove(
            self.hass.bus.async_listen(
                self.bridge.event_name("update"),
                self._handle_entity_update,
            )
        )
        self.async_on_remove(
            self.hass.bus.async_listen(
                self.bridge.event_name("health"),
                self._handle_availability_update,
            )
        )
        self.async_on_remove(
            self.hass.bus.async_listen(
                self.bridge.event_name("register"),
                self._handle_registration_event,
            )
        )

    @property
    def device_info(self) -> DeviceInfo:
        """Return device registry information for this entity.

        First tries to find a specific device by device_id, then falls back
        to the primary app device. Returns None during startup if no devices
        are available yet.
        """
        declared_device = self.entity.get("device_id", "")
        if len(declared_device) > 0:
            device = self.bridge.via_primary_device.get(declared_device)
            if device is not None:
                return device

        # Everything is associated with the app device if all else fails
        if self.bridge.primary_device is not None:
            return self.bridge.primary_device

        # Return None if no device info is available yet (during startup)
        return None

    @property
    def unique_id(self) -> str:
        return self.entity.get("unique_id")

    @property
    def suggested_object_id(self) -> str:
        return self.entity.get("suggested_object_id")

    @property
    def translation_key(self) -> Optional[str]:
        return self.entity.get("translation_key")

    @property
    def icon(self) -> Optional[str]:
        return self.entity.get("icon")

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        return self.entity.get("attributes") or {}

    @property
    def entity_category(self) -> Optional[EntityCategory]:
        if self.entity.get("entity_category") == "config":
            return EntityCategory.CONFIG
        if self.entity.get("entity_category") == "diagnostic":
            return EntityCategory.DIAGNOSTIC
        return None

    @property
    def name(self) -> str:
        return self.entity.get("name")

    @property
    def suggested_area_id(self) -> Optional[str]:
        return self.entity.get("area_id")

    @property
    def labels(self) -> List[str]:
        return self.entity.get("labels")

    @property
    def available(self) -> bool:
        """Return True if the entity is available.

        An entity is unavailable if:
        - The bridge is offline
        - The entity is explicitly disabled
        - Cleanup mode is "abandon" and entity doesn't exist in current configuration
        """
        if self.entity.get("disabled") == True:
            return False

        # Check if cleanup mode is "abandon" and entity is not in current configuration
        cleanup_mode = self.bridge.get_cleanup_mode()
        if cleanup_mode == "abandon":
            # Use cached result for configuration existence check if available
            if self._config_cache_valid and self._config_exists_cache is not None:
                config_exists = self._config_exists_cache
            else:
                # Calculate configuration existence
                config_exists = self._check_configuration_exists()
                # Cache the result
                self._config_exists_cache = config_exists
                self._config_cache_valid = True

            if not config_exists:
                # Entity doesn't exist in current configuration - mark as unavailable
                return False

        return self.bridge.online

    def _check_configuration_exists(self) -> bool:
        """Check if this entity exists in the current configuration."""
        entity_unique_id = self.entity.get("unique_id")
        if not entity_unique_id:
            return False

        # Check if entity exists in the bridge's current entities tracking
        # This is populated during configuration updates
        if self.bridge._current_entities:
            for domain, domain_entities in self.bridge._current_entities.items():
                if entity_unique_id in domain_entities:
                    return True
            return False

        # If _current_entities is empty, check the current dynamic configuration
        if self.bridge._current_configuration:
            for domain in ENTITY_DOMAINS:
                entities = self.bridge._current_configuration.get(domain, [])
                if isinstance(entities, list):
                    for entity_data in entities:
                        if entity_data.get("unique_id") == entity_unique_id:
                            return True
            return False

        # If no current configuration has been received yet, assume entity does not exist
        # This handles the initial registration phase before configuration update
        return False

    @callback
    def _handle_entity_update(self, event: Any) -> None:
        # events target bridge, up to entities to filter for responses that apply to them
        #
        # mental note: this was done to reduce quantity of unique events flying around
        # this is probably worth changing to namespace/{unique_id}/update or something
        # easier to debug + less useless event handle executions
        if event.data.get("unique_id") == self.entity.get("unique_id"):
            # Merge the incoming changes with the existing entity data
            incoming_data = event.data.get("data", {})
            if isinstance(incoming_data, dict):
                # Update the entity data with the new values
                self.entity.update(incoming_data)

            # Trigger a state update to reflect the changes
            self.async_write_ha_state()

    @callback
    def _handle_availability_update(self, event: Any) -> None:
        """Handle health status update."""
        self.async_schedule_update_ha_state(True)

    @callback
    def _handle_registration_event(self, event: Any) -> None:
        """Handle registration events that may change entity configuration."""
        # Invalidate configuration existence cache since registration may change entity configuration
        self._invalidate_config_cache()
        self.async_schedule_update_ha_state(True)

    def _invalidate_config_cache(self) -> None:
        """Invalidate the configuration existence cache."""
        self._config_cache_valid = False
        self._config_exists_cache = None
