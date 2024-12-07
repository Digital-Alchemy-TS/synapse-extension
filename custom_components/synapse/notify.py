import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback, HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.components.notify import NotifyEntity

from .synapse.base_entity import SynapseBaseEntity
from .synapse.bridge import SynapseBridge
from .synapse.const import DOMAIN, SynapseNotifyDefinition

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Setup the router platform."""
    bridge: SynapseBridge = hass.data[DOMAIN][config_entry.entry_id]
    entities = bridge.app_data.get("notify")
    if entities is not None:
      async_add_entities(SynapseNotify(hass, bridge, entity) for entity in entities)

class SynapseNotify(SynapseBaseEntity, NotifyEntity):
    def __init__(
        self,
        hass: HomeAssistant,
        bridge: SynapseBridge,
        entity: SynapseNotifyDefinition,
    ):
        super().__init__(hass, bridge, entity)
        self.logger = logging.getLogger(__name__)

    @callback
    async def async_send_message(self, message: str, **kwargs) -> None:
        """Proxy the request to send a message."""
        self.hass.bus.async_fire(
            self.bridge.event_name("send_message"),
            {"unique_id": self.entity.get("unique_id"), "message": message, **kwargs},
        )
