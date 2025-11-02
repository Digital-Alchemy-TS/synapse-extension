"""
# Digital Alchemy Synapse config flow

This flow is takes a unique strategy towards app discovery because of what it is intented to integrate with.
All of the target "devices" are nodejs applications that are ALREADY CONNECTED via websocket to this Home Assistant instance.
No authentication or configuration steps required here, those have all been handled elsewhere already.

Interactions between this Python integration and the target application take place over the HA event bus.
Discovery is performed via this workflow:

1. emit a discovery request message
2. wait short duration & aggregate replies
3. display list to user (or error if nothing replied)

## Discovery flows

Currently there is no discovery flow in the same way as ssdp.
The above config flow is pretty straightforward, but issues/concerns that came up in original implementation attempt:

- unclear if there is a code path to triggering discovery via event bus message
- the discovery should not trigger on ha instances app is not connected to (prod vs dev instances)
- should not involve additional dependencies on app side (such as requiring a webserver)

Would be nice to find a solution to this as a future upgrade.
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional

import asyncio
import logging
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow
from homeassistant.const import CONF_NAME

from .synapse.const import DOMAIN, EVENT_NAMESPACE, SynapseApplication, QUERY_TIMEOUT


class SynapseConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for synapse"""

    VERSION = 1
    MINOR_VERSION = 1

    def __init__(self) -> None:
        """Initialize the Synapse flow."""
        self.application: Optional[SynapseApplication] = None
        self.discovery_info: Optional[Dict[str, Any]] = None
        self.known_apps: List[SynapseApplication] = []
        self.logger: logging.Logger = logging.getLogger(__name__)

    async def async_step_user(self, user_input: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Handle a flow initialized by the user."""
        errors: Dict[str, str] = {}

        if user_input is not None:
            try:
                selected_app_name = user_input[CONF_NAME]
                selected_app_info = next(app for app in self.known_apps if app["app"] == selected_app_name)

                await self.async_set_unique_id(selected_app_info.get("unique_id"))
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=selected_app_info.get("title"), data=selected_app_info)
            except Exception as ex:  # pylint: disable=broad-except
                self.logger.error(ex)
                errors["base"] = "unknown"

        # Get the list of discovered apps
        try:
            all_apps = await self.identify_all()

            # Filter out apps that are already configured
            existing_config_entries = self.hass.config_entries.async_entries(DOMAIN)
            existing_unique_ids = {entry.data.get("unique_id") for entry in existing_config_entries}

            # Only show apps that aren't already configured
            self.known_apps = [
                app for app in all_apps
                if app.get("unique_id") not in existing_unique_ids
            ]

            app_choices = {app["app"]: app["title"] for app in self.known_apps}
            self.logger.info(f"Found {len(self.known_apps)} new apps (filtered from {len(all_apps)} total)")
        except Exception as ex:
            self.logger.error(f"Error during discovery: {ex}")
            errors["base"] = "unknown"
            app_choices = {}

        if not app_choices:
            errors["base"] = "No new applications found"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_NAME): vol.In(app_choices)}),
            errors=errors,
        )

    async def async_step_confirm(self, user_input: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Handle the confirmation step."""
        if user_input is not None:
            return self.async_create_entry(title=self.application["title"], data=self.application)

        return self.async_show_form(
            step_id="confirm",
            description_placeholders={"name": self.application["title"]},
            data_schema=vol.Schema({}),
        )

    async def identify_all(self) -> List[SynapseApplication]:
        """
        Request all connected apps identify themselves via event bus.
        Already registered apps will ignore the request.
        """
        self.logger.info("Starting discovery via event bus")

        # Set up listener for responses
        replies: List[Dict[str, Any]] = []
        event_handler_removed = False

        def handle_event(event: Any) -> None:
            """Handle identification responses from apps."""
            # Accept raw JSON data from event (MVP discovery data: app, title, unique_id)
            app_data = event.data
            if app_data and isinstance(app_data, dict) and app_data.get("unique_id"):
                replies.append(app_data)
                self.logger.debug(f"Received discovery response: {len(replies)} apps found so far")

        # Register event listener
        remove_listener = self.hass.bus.async_listen(f"{EVENT_NAMESPACE}/identify", handle_event)

        try:
            # Emit discovery request on event bus
            self.logger.info(f"Emitting discovery request: {EVENT_NAMESPACE}/discovery")
            self.hass.bus.async_fire(f"{EVENT_NAMESPACE}/discovery")

            # Wait 1 second for replies
            await asyncio.sleep(1.0)

            self.logger.info(f"Discovery complete: received {len(replies)} responses")
        finally:
            # Always clean up the event listener
            if not event_handler_removed:
                remove_listener()
                event_handler_removed = True
                self.logger.debug("Event listener removed")

        # Replies are already dict objects (no compression/hex conversion needed)
        apps = replies
        self.logger.info(f"Discovered {len(apps)} apps")

        return apps
