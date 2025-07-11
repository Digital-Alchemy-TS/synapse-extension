# Code Quality & Standards

## Overview
Address code quality issues including missing type hints, error handling, global state, and duplicate imports.

## 🔴 Critical Issues

### 1. Missing Type Hints

#### 1.1 Files Requiring Type Hints
- `bridge.py`: Most methods lack proper type annotations
- `base_entity.py`: Event handlers need type hints
- All entity files need proper type annotations for properties
- `config_flow.py`: Event handlers need type hints

#### 1.2 Implementation Plan
```python
# Example: bridge.py with proper type hints
from __future__ import annotations
from typing import Any, Dict, List, Optional
import asyncio
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN, SynapseApplication, SynapseMetadata

class SynapseBridge:
    """Bridge for managing synapse app communication."""

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize the bridge."""
        self.logger: logging.Logger = logging.getLogger(__name__)
        self.config_entry: ConfigEntry = config_entry
        self.primary_device: Optional[DeviceInfo] = None
        self.via_primary_device: Dict[str, DeviceInfo] = {}
        self.hass: HomeAssistant = hass
        self.app_data: SynapseApplication = config_entry.data
        self.app_name: str = self.app_data.get("app", "")
        self.metadata_unique_id: str = self.app_data.get("unique_id", "")

        # ... rest of init

    async def async_cleanup(self) -> None:
        """Clean up resources when tearing down the bridge."""
        # Implementation

    @callback
    def handle_heartbeat(self, event: Any) -> None:
        """Handle heartbeat & 'coming back online' messages."""
        # Implementation

    def format_device_info(self, device: Optional[SynapseMetadata] = None) -> Dict[str, Any]:
        """Translate between synapse data objects and hass device info."""
        # Implementation

    async def async_reload(self) -> None:
        """Reload the bridge and update local info."""
        # Implementation
```

### 2. Error Handling

#### 2.1 Current Issues
- `bridge.py`: Missing try/catch blocks for critical operations
- `config_flow.py`: Generic exception handling (`except Exception`) is too broad
- Entity updates could fail silently

#### 2.2 Implementation Plan
```python
# Example: Proper error handling in bridge.py
import logging
from typing import Optional

class SynapseBridgeError(Exception):
    """Base exception for synapse bridge errors."""
    pass

class SynapseConnectionError(SynapseBridgeError):
    """Raised when connection to app fails."""
    pass

class SynapseValidationError(SynapseBridgeError):
    """Raised when data validation fails."""
    pass

class SynapseBridge:
    async def async_reload(self) -> None:
        """Reload the bridge and update local info."""
        self.logger.debug(f"{self.app_name} request reload")

        try:
            data = await self._async_fetch_state(self.app_name)
        except asyncio.TimeoutError:
            self.logger.error(f"{self.app_name} timeout during reload")
            raise SynapseConnectionError(f"Timeout connecting to {self.app_name}")
        except Exception as e:
            self.logger.error(f"{self.app_name} unexpected error during reload: {e}")
            raise SynapseBridgeError(f"Failed to reload {self.app_name}: {e}")

        if data is None:
            self.logger.warning("no response, is app connected?")
            raise SynapseConnectionError(f"No response from {self.app_name}")

        try:
            # Handle incoming data
            self.app_data = data
            self._hash_dict[self.metadata_unique_id] = data.get("hash")
            self.app_name = self.app_data.get("app", "")
            self._refresh_devices()
            self._refresh_entities()
        except KeyError as e:
            self.logger.error(f"Missing required field in app data: {e}")
            raise SynapseValidationError(f"Invalid app data format: {e}")
        except Exception as e:
            self.logger.error(f"Error processing app data: {e}")
            raise SynapseBridgeError(f"Failed to process app data: {e}")

        # this counts as a heartbeat
        self.online = True
```

#### 2.3 Config Flow Error Handling
```python
# Example: Proper error handling in config_flow.py
from typing import Any, Dict, List

class SynapseConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for synapse."""

    async def async_step_user(self, user_input: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Handle a flow initialized by the user."""
        errors: Dict[str, str] = {}

        if user_input is not None:
            try:
                selected_app_name = user_input[CONF_NAME]
                selected_app_info = next(
                    app for app in self.known_apps if app["app"] == selected_app_name
                )

                await self.async_set_unique_id(selected_app_info.get("unique_id"))
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=selected_app_info.get("title"),
                    data=selected_app_info
                )
            except KeyError as e:
                self.logger.error(f"Missing required field in app info: {e}")
                errors["base"] = "invalid_app_data"
            except StopIteration:
                self.logger.error(f"Selected app not found: {selected_app_name}")
                errors["base"] = "app_not_found"
            except Exception as e:
                self.logger.error(f"Unexpected error during config: {e}")
                errors["base"] = "unknown"

        # Get the list of known good things
        try:
            self.known_apps = await self.identify_all()
            app_choices = {app["app"]: app["title"] for app in self.known_apps}
        except asyncio.TimeoutError:
            self.logger.error("Timeout during app discovery")
            errors["base"] = "discovery_timeout"
        except Exception as e:
            self.logger.error(f"Error during app discovery: {e}")
            errors["base"] = "discovery_failed"

        if not app_choices:
            errors["base"] = "no_apps_found"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_NAME): vol.In(app_choices)}),
            errors=errors,
        )
```

### 3. Global State Issues

#### 3.1 Current Problem
```python
# Current problematic code in bridge.py
hashDict = {}  # Global variable - BAD!
```

#### 3.2 Solution: Instance-Based State
```python
# Fixed: Instance-based state management
class SynapseBridge:
    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        # ... existing init code ...
        self._hash_dict: Dict[str, str] = {}  # Instance variable - GOOD!

    async def async_reload(self) -> None:
        # ... existing code ...
        self._hash_dict[self.metadata_unique_id] = data.get("hash")  # Use instance variable

    @callback
    def handle_heartbeat(self, event: Any) -> None:
        # ... existing code ...
        if self.metadata_unique_id in self._hash_dict:  # Use instance variable
            entry_id = self.config_entry.entry_id
            incoming_hash = event.data.get("hash")
            if incoming_hash != self._hash_dict[self.metadata_unique_id]:  # Use instance variable
                # ... rest of code
```

### 4. Duplicate Imports

#### 4.1 Current Issues
```python
# Current problematic imports in bridge.py
import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback, HomeAssistant
# ... other imports ...
import logging  # DUPLICATE!
from homeassistant.config_entries import ConfigEntry  # DUPLICATE!
from homeassistant.core import callback, HomeAssistant  # DUPLICATE!
```

#### 4.2 Fixed Imports
```python
# Fixed: Clean, organized imports
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
    EVENT_NAMESPACE,
    SynapseApplication,
    SynapseMetadata,
    QUERY_TIMEOUT,
    RETRIES,
    RETRY_DELAY,
)
from .helpers import hex_to_object
```

### 5. Entity Type Hints

#### 5.1 Base Entity Improvements
```python
# Example: base_entity.py with proper type hints
from __future__ import annotations
from typing import Any, Dict, Optional

from homeassistant.const import EntityCategory
from homeassistant.core import callback, HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity

from .bridge import SynapseBridge
from .const import SynapseBaseEntity

class SynapseBaseEntity(Entity):
    """Base class for all synapse entities."""

    def __init__(
        self,
        hass: HomeAssistant,
        bridge: SynapseBridge,
        entity: SynapseBaseEntity
    ) -> None:
        """Initialize the base entity."""
        self.logger: logging.Logger = logging.getLogger(__name__)
        self.hass: HomeAssistant = hass
        self.bridge: SynapseBridge = bridge
        self.entity: SynapseBaseEntity = entity

        # ... rest of init

    @property
    def device_info(self) -> DeviceInfo:
        """Return device registry information for this entity."""
        # Implementation

    @property
    def unique_id(self) -> str:
        """Return the unique ID of the entity."""
        return self.entity.get("unique_id", "")

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        return self.entity.get("name", "")

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        if self.entity.get("disabled") == True:
            return False
        return self.bridge.online

    @callback
    def _handle_entity_update(self, event: Any) -> None:
        """Handle entity update events."""
        # Implementation

    @callback
    def _handle_availability_update(self, event: Any) -> None:
        """Handle health status update."""
        # Implementation
```

## 🧪 Testing

### 5.1 Type Checking Tests
```python
# tests/test_type_hints.py
import pytest
from mypy import api

def test_type_hints():
    """Test that all files have proper type hints."""
    # Run mypy on the codebase
    result = api.run([
        'custom_components/synapse/',
        '--ignore-missing-imports',
        '--disallow-untyped-defs',
        '--disallow-incomplete-defs',
    ])

    if result[0]:  # If there are errors
        pytest.fail(f"Type checking failed:\n{result[0]}")
```

### 5.2 Error Handling Tests
```python
# tests/test_error_handling.py
import pytest
from unittest.mock import AsyncMock, MagicMock

from custom_components.synapse.synapse.bridge import SynapseBridge, SynapseConnectionError

async def test_bridge_reload_timeout(hass):
    """Test that bridge handles timeout errors properly."""
    config_entry = MagicMock()
    config_entry.data = {"app": "test_app", "unique_id": "test_id"}

    bridge = SynapseBridge(hass, config_entry)

    # Mock the fetch method to raise timeout
    bridge._async_fetch_state = AsyncMock(side_effect=asyncio.TimeoutError())

    with pytest.raises(SynapseConnectionError, match="Timeout connecting to test_app"):
        await bridge.async_reload()

async def test_bridge_reload_invalid_data(hass):
    """Test that bridge handles invalid data properly."""
    config_entry = MagicMock()
    config_entry.data = {"app": "test_app", "unique_id": "test_id"}

    bridge = SynapseBridge(hass, config_entry)

    # Mock the fetch method to return invalid data
    bridge._async_fetch_state = AsyncMock(return_value={"invalid": "data"})

    with pytest.raises(SynapseValidationError, match="Invalid app data format"):
        await bridge.async_reload()
```

## 📋 Implementation Checklist

### Phase 1: Type Hints (Week 1)
- [ ] Add type hints to `bridge.py`
- [ ] Add type hints to `base_entity.py`
- [ ] Add type hints to all entity files
- [ ] Add type hints to `config_flow.py`
- [ ] Add type hints to `helpers.py`

### Phase 2: Error Handling (Week 1)
- [ ] Create custom exception classes
- [ ] Add proper error handling to `bridge.py`
- [ ] Add proper error handling to `config_flow.py`
- [ ] Add proper error handling to entity files
- [ ] Add logging for all error conditions

### Phase 3: Global State (Week 1)
- [ ] Remove global `hashDict` variable
- [ ] Convert to instance-based state management
- [ ] Update all references to use instance variables
- [ ] Test with multiple bridge instances

### Phase 4: Import Cleanup (Week 1)
- [ ] Remove duplicate imports
- [ ] Organize imports according to PEP 8
- [ ] Add `__future__` imports where needed
- [ ] Run `isort` to auto-organize imports

## 🎯 Success Criteria

- ✅ All functions have proper type hints
- ✅ All error conditions are properly handled
- ✅ No global variables exist
- ✅ No duplicate imports
- ✅ Code passes mypy type checking
- ✅ Code passes pylint with high score
- ✅ All error conditions are logged appropriately

## 📝 Notes

- Type hints are required for core acceptance
- Proper error handling improves reliability
- Global state can cause issues with multiple instances
- Clean imports improve code maintainability
- These changes will significantly improve code quality score
