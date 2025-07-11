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
    """Setup the router platform."""
    bridge: SynapseBridge = hass.data[DOMAIN][config_entry.entry_id]
    entities: List[SynapseClimateDefinition] = bridge.app_data.get("climate", [])
    if entities is not None:
      async_add_entities(SynapseClimate(hass, bridge, entity) for entity in entities)

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
        self.hass.bus.async_fire(
            self.bridge.event_name("set_hvac_mode"),
            {
                "unique_id": self.entity.get("unique_id"),
                "hvac_mode": hvac_mode,
                **kwargs,
            },
        )

    @callback
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Proxy the request to turn the entity on."""
        self.hass.bus.async_fire(
            self.bridge.event_name("turn_on"),
            {"unique_id": self.entity.get("unique_id"), **kwargs},
        )

    @callback
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Proxy the request to turn the entity off."""
        self.hass.bus.async_fire(
            self.bridge.event_name("turn_off"),
            {"unique_id": self.entity.get("unique_id"), **kwargs},
        )

    @callback
    async def async_toggle(self, **kwargs: Any) -> None:
        """Proxy the request to toggle the entity."""
        self.hass.bus.async_fire(
            self.bridge.event_name("toggle"),
            {"unique_id": self.entity.get("unique_id"), **kwargs},
        )

    @callback
    async def async_set_preset_mode(self, preset_mode: str, **kwargs: Any) -> None:
        """Proxy the request to set preset mode."""
        self.hass.bus.async_fire(
            self.bridge.event_name("set_preset_mode"),
            {
                "unique_id": self.entity.get("unique_id"),
                "preset_mode": preset_mode,
                **kwargs,
            },
        )

    @callback
    async def async_set_fan_mode(self, fan_mode: str, **kwargs: Any) -> None:
        """Proxy the request to set fan mode."""
        self.hass.bus.async_fire(
            self.bridge.event_name("set_fan_mode"),
            {"unique_id": self.entity.get("unique_id"), "fan_mode": fan_mode, **kwargs},
        )

    @callback
    async def async_set_humidity(self, humidity: float, **kwargs: Any) -> None:
        """Proxy the request to set humidity."""
        self.hass.bus.async_fire(
            self.bridge.event_name("set_humidity"),
            {"unique_id": self.entity.get("unique_id"), "humidity": humidity, **kwargs},
        )

    @callback
    async def async_set_swing_mode(self, swing_mode: str, **kwargs: Any) -> None:
        """Proxy the request to set swing mode."""
        self.hass.bus.async_fire(
            self.bridge.event_name("set_swing_mode"),
            {
                "unique_id": self.entity.get("unique_id"),
                "swing_mode": swing_mode,
                **kwargs,
            },
        )

    @callback
    async def async_set_temperature(self, temperature: float, **kwargs: Any) -> None:
        """Proxy the request to set temperature."""
        self.hass.bus.async_fire(
            self.bridge.event_name("set_temperature"),
            {
                "unique_id": self.entity.get("unique_id"),
                "temperature": temperature,
                **kwargs,
            },
        )
