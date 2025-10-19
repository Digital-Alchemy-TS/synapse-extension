from __future__ import annotations

import logging
from typing import Any, List, Optional

from homeassistant.components.climate import ClimateEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback, HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .synapse.base_entity import SynapseBaseEntity
from .synapse.bridge import SynapseBridge
from .synapse.const import DOMAIN, SynapseClimateDefinition

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Setup the climate platform."""
    bridge: SynapseBridge = hass.data[DOMAIN][config_entry.entry_id]

    # Use dynamic configuration if available, otherwise fall back to static config
    entities: List[SynapseClimateDefinition] = []
    if bridge._current_configuration and "climate" in bridge._current_configuration:
        entities = bridge._current_configuration.get("climate", [])
        bridge.logger.info(f"Climate platform setup: Using dynamic configuration with {len(entities)} entities")
    else:
        entities = bridge.app_data.get("climate", [])
        bridge.logger.info(f"Climate platform setup: Using static configuration with {len(entities)} entities")

    if entities:
        bridge.logger.info(f"Adding {len(entities)} climate entities: {[e.get('name') for e in entities]}")
        async_add_entities(SynapseClimate(hass, bridge, entity) for entity in entities)
    else:
        bridge.logger.info("No climate entities to add")

    # Listen for registration events to add new entities dynamically
    async def handle_registration(event):
        """Handle registration events to add new climate entities."""
        bridge.logger.info(f"Climate platform received registration event: {event.data}")
        bridge.logger.info(f"Event unique_id: {event.data.get('unique_id')}, bridge.metadata_unique_id: {bridge.metadata_unique_id}")

        if event.data.get("unique_id") == bridge.metadata_unique_id:
            bridge.logger.info("Registration event received, checking for new climate entities")

            # Check if there are new climate entities in the dynamic configuration
            if bridge._current_configuration and "climate" in bridge._current_configuration:
                new_entities = bridge._current_configuration.get("climate", [])
                if new_entities:
                    bridge.logger.info(f"Adding {len(new_entities)} new climate entities: {[e.get('name') for e in new_entities]}")
                    async_add_entities(SynapseClimate(hass, bridge, entity) for entity in new_entities)
                else:
                    bridge.logger.debug("No new climate entities found in registration")
            else:
                bridge.logger.debug("No dynamic configuration found for climate entities")
        else:
            bridge.logger.debug(f"Registration event not for this bridge: {event.data.get('unique_id')} != {bridge.metadata_unique_id}")

    # Register the event listener
    bridge.logger.info(f"Registering climate platform event listener for: {bridge.event_name('register')}")
    bridge.logger.info(f"Bridge metadata_unique_id: {bridge.metadata_unique_id}")
    hass.bus.async_listen(bridge.event_name("register"), handle_registration)
    bridge.logger.info("Climate platform event listener registered successfully")

class SynapseClimate(SynapseBaseEntity, ClimateEntity):
    def __init__(
        self,
        hass: HomeAssistant,
        bridge: SynapseBridge,
        entity: SynapseClimateDefinition,
    ) -> None:
        super().__init__(hass, bridge, entity)
        self.logger: logging.Logger = logging.getLogger(__name__)

    @property
    def current_humidity(self) -> Optional[int]:
        return self.entity.get("current_humidity")

    @property
    def current_temperature(self) -> Optional[float]:
        return self.entity.get("current_temperature")

    @property
    def fan_mode(self) -> Optional[str]:
        return self.entity.get("fan_mode")

    @property
    def fan_modes(self) -> List[str]:
        return self.entity.get("fan_modes", [])

    @property
    def hvac_action(self) -> Optional[str]:
        return self.entity.get("hvac_action")

    @property
    def hvac_mode(self) -> Optional[str]:
        return self.entity.get("hvac_mode")

    @property
    def hvac_modes(self) -> List[str]:
        return self.entity.get("hvac_modes", [])

    @property
    def max_humidity(self) -> Optional[int]:
        return self.entity.get("max_humidity")

    @property
    def max_temp(self) -> Optional[float]:
        return self.entity.get("max_temp")

    @property
    def min_humidity(self) -> Optional[int]:
        return self.entity.get("min_humidity")

    @property
    def min_temp(self) -> Optional[float]:
        return self.entity.get("min_temp")

    @property
    def precision(self) -> float:
        return self.entity.get("precision", 0.1)

    @property
    def preset_mode(self) -> Optional[str]:
        return self.entity.get("preset_mode")

    @property
    def preset_modes(self) -> List[str]:
        return self.entity.get("preset_modes", [])

    @property
    def swing_mode(self) -> Optional[str]:
        return self.entity.get("swing_mode")

    @property
    def swing_modes(self) -> List[str]:
        return self.entity.get("swing_modes", [])

    @property
    def target_humidity(self) -> Optional[int]:
        return self.entity.get("target_humidity")

    @property
    def target_temperature_high(self) -> Optional[float]:
        return self.entity.get("target_temperature_high")

    @property
    def target_temperature_low(self) -> Optional[float]:
        return self.entity.get("target_temperature_low")

    @property
    def target_temperature_step(self) -> Optional[float]:
        return self.entity.get("target_temperature_step")

    @property
    def target_temperature(self) -> Optional[float]:
        return self.entity.get("target_temperature")

    @property
    def temperature_unit(self) -> str:
        return self.entity.get("temperature_unit", "°C")

    @callback
    async def async_set_hvac_mode(self, hvac_mode: str, **kwargs: Any) -> None:
        """Proxy the request to set HVAC mode."""
        await self.bridge.emit_event(
            "set_hvac_mode",
            {
                "unique_id": self.entity.get("unique_id"),
                "hvac_mode": hvac_mode,
                **kwargs,
            },
        )

    @callback
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Proxy the request to turn the entity on."""
        await self.bridge.emit_event(
            "turn_on", {"unique_id": self.entity.get("unique_id"), **kwargs}
        )

    @callback
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Proxy the request to turn the entity off."""
        await self.bridge.emit_event(
            "turn_off", {"unique_id": self.entity.get("unique_id"), **kwargs}
        )

    @callback
    async def async_toggle(self, **kwargs: Any) -> None:
        """Proxy the request to toggle the entity."""
        await self.bridge.emit_event(
            "toggle", {"unique_id": self.entity.get("unique_id"), **kwargs}
        )

    @callback
    async def async_set_preset_mode(self, preset_mode: str, **kwargs: Any) -> None:
        """Proxy the request to set preset mode."""
        await self.bridge.emit_event(
            "set_preset_mode",
            {
                "unique_id": self.entity.get("unique_id"),
                "preset_mode": preset_mode,
                **kwargs,
            },
        )

    @callback
    async def async_set_fan_mode(self, fan_mode: str, **kwargs: Any) -> None:
        """Proxy the request to set fan mode."""
        await self.bridge.emit_event(
            "set_fan_mode", {"unique_id": self.entity.get("unique_id"), "fan_mode": fan_mode, **kwargs}
        )

    @callback
    async def async_set_humidity(self, humidity: float, **kwargs: Any) -> None:
        """Proxy the request to set humidity."""
        await self.bridge.emit_event(
            "set_humidity", {"unique_id": self.entity.get("unique_id"), "humidity": humidity, **kwargs}
        )

    @callback
    async def async_set_swing_mode(self, swing_mode: str, **kwargs: Any) -> None:
        """Proxy the request to set swing mode."""
        await self.bridge.emit_event(
            "set_swing_mode",
            {
                "unique_id": self.entity.get("unique_id"),
                "swing_mode": swing_mode,
                **kwargs,
            },
        )

    @callback
    async def async_set_temperature(self, temperature: float, **kwargs: Any) -> None:
        """Proxy the request to set temperature."""
        await self.bridge.emit_event(
            "set_temperature",
            {
                "unique_id": self.entity.get("unique_id"),
                "temperature": temperature,
                **kwargs,
            },
        )
