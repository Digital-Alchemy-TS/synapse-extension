from .bridge import SynapseBridge
from .const import DOMAIN, PLATFORMS
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
import logging

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Synapse app from a config entry."""
    bridge = SynapseBridge(hass, entry.data)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = bridge

    await bridge.reload()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await bridge.async_setup_health_sensor()
    await bridge.import_data()
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
