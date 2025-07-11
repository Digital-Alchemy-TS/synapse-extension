# Testing Framework

## Overview
Create comprehensive unit and integration tests to achieve 80%+ test coverage required for Home Assistant core submission.

## 🔴 Current State
- **No unit tests exist**
- **No integration tests exist**
- **No test framework set up**
- **No CI/CD pipeline**

## 📋 Required Test Coverage

### 1. Unit Tests (80%+ coverage required)

#### 1.1 Bridge Tests
```python
# tests/test_bridge.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from custom_components.synapse.synapse.bridge import SynapseBridge
from custom_components.synapse.synapse.const import SynapseApplication

@pytest.fixture
def mock_config_entry():
    """Create a mock config entry."""
    entry = MagicMock(spec=ConfigEntry)
    entry.data = {
        "app": "test_app",
        "unique_id": "test_unique_id",
        "title": "Test App",
        "version": "1.0.0"
    }
    return entry

@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = MagicMock(spec=HomeAssistant)
    hass.data = {}
    return hass

@pytest.fixture
def bridge(mock_hass, mock_config_entry):
    """Create a bridge instance for testing."""
    return SynapseBridge(mock_hass, mock_config_entry)

class TestSynapseBridge:
    """Test the SynapseBridge class."""

    async def test_init(self, bridge, mock_hass, mock_config_entry):
        """Test bridge initialization."""
        assert bridge.hass == mock_hass
        assert bridge.config_entry == mock_config_entry
        assert bridge.app_name == "test_app"
        assert bridge.metadata_unique_id == "test_unique_id"
        assert bridge.online is False

    async def test_async_cleanup(self, bridge):
        """Test bridge cleanup."""
        # Mock the heartbeat timer
        bridge._heartbeat_timer = MagicMock()
        bridge._removals = [MagicMock()]

        await bridge.async_cleanup()

        bridge._heartbeat_timer.cancel.assert_called_once()
        for removal in bridge._removals:
            removal.assert_called_once()

    async def test_format_device_info(self, bridge):
        """Test device info formatting."""
        device_data = {
            "name": "Test Device",
            "manufacturer": "Test Manufacturer",
            "model": "Test Model",
            "unique_id": "device_unique_id"
        }

        result = bridge.format_device_info(device_data)

        assert result["name"] == "Test Device"
        assert result["manufacturer"] == "Test Manufacturer"
        assert result["model"] == "Test Model"

    async def test_async_reload_success(self, bridge):
        """Test successful bridge reload."""
        mock_data = {
            "app": "test_app",
            "unique_id": "test_unique_id",
            "hash": "test_hash",
            "sensor": [],
            "switch": []
        }

        with patch.object(bridge, '_async_fetch_state', return_value=mock_data):
            await bridge.async_reload()

        assert bridge.app_data == mock_data
        assert bridge.online is True

    async def test_async_reload_timeout(self, bridge):
        """Test bridge reload with timeout."""
        with patch.object(bridge, '_async_fetch_state', return_value=None):
            await bridge.async_reload()

        assert bridge.online is False

    async def test_handle_heartbeat(self, bridge):
        """Test heartbeat handling."""
        event = MagicMock()
        event.data = {"hash": "new_hash"}

        bridge.online = False
        bridge._hash_dict = {"test_unique_id": "old_hash"}

        bridge.handle_heartbeat(event)

        assert bridge.online is True
        assert bridge._heartbeat_timer is not None
```

#### 1.2 Entity Tests
```python
# tests/test_entities.py
import pytest
from unittest.mock import MagicMock

from homeassistant.core import HomeAssistant
from custom_components.synapse.synapse.base_entity import SynapseBaseEntity
from custom_components.synapse.synapse.bridge import SynapseBridge

@pytest.fixture
def mock_entity_data():
    """Create mock entity data."""
    return {
        "unique_id": "test_entity",
        "name": "Test Entity",
        "state": "on",
        "attributes": {"friendly_name": "Test Entity"},
        "device_id": "test_device"
    }

@pytest.fixture
def mock_bridge():
    """Create a mock bridge."""
    bridge = MagicMock(spec=SynapseBridge)
    bridge.app_name = "test_app"
    bridge.online = True
    bridge.primary_device = MagicMock()
    return bridge

@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    return MagicMock(spec=HomeAssistant)

@pytest.fixture
def entity(mock_hass, mock_bridge, mock_entity_data):
    """Create an entity instance for testing."""
    return SynapseBaseEntity(mock_hass, mock_bridge, mock_entity_data)

class TestSynapseBaseEntity:
    """Test the SynapseBaseEntity class."""

    def test_init(self, entity, mock_hass, mock_bridge, mock_entity_data):
        """Test entity initialization."""
        assert entity.hass == mock_hass
        assert entity.bridge == mock_bridge
        assert entity.entity == mock_entity_data

    def test_unique_id(self, entity):
        """Test unique_id property."""
        assert entity.unique_id == "test_entity"

    def test_name(self, entity):
        """Test name property."""
        assert entity.name == "Test Entity"

    def test_available_online(self, entity):
        """Test available property when online."""
        entity.bridge.online = True
        entity.entity["disabled"] = False

        assert entity.available is True

    def test_available_offline(self, entity):
        """Test available property when offline."""
        entity.bridge.online = False

        assert entity.available is False

    def test_available_disabled(self, entity):
        """Test available property when disabled."""
        entity.bridge.online = True
        entity.entity["disabled"] = True

        assert entity.available is False

    def test_device_info(self, entity, mock_bridge):
        """Test device_info property."""
        result = entity.device_info

        assert result == mock_bridge.primary_device

    def test_extra_state_attributes(self, entity):
        """Test extra_state_attributes property."""
        result = entity.extra_state_attributes

        assert result == {"friendly_name": "Test Entity"}
```

#### 1.3 Config Flow Tests
```python
# tests/test_config_flow.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from custom_components.synapse.config_flow import SynapseConfigFlow

@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = MagicMock(spec=HomeAssistant)
    hass.bus = MagicMock()
    return hass

@pytest.fixture
def config_flow(mock_hass):
    """Create a config flow instance."""
    flow = SynapseConfigFlow()
    flow.hass = mock_hass
    return flow

class TestSynapseConfigFlow:
    """Test the SynapseConfigFlow class."""

    async def test_async_step_user_no_input(self, config_flow):
        """Test user step with no input."""
        with patch.object(config_flow, 'identify_all', return_value=[]):
            result = await config_flow.async_step_user()

        assert result["type"] == "form"
        assert result["step_id"] == "user"
        assert "errors" in result

    async def test_async_step_user_with_valid_input(self, config_flow):
        """Test user step with valid input."""
        mock_apps = [
            {
                "app": "test_app",
                "unique_id": "test_unique_id",
                "title": "Test App"
            }
        ]

        with patch.object(config_flow, 'identify_all', return_value=mock_apps):
            result = await config_flow.async_step_user({
                "name": "test_app"
            })

        assert result["type"] == "create_entry"
        assert result["title"] == "Test App"
        assert result["data"]["app"] == "test_app"

    async def test_async_step_user_app_not_found(self, config_flow):
        """Test user step with app not found."""
        mock_apps = [
            {
                "app": "other_app",
                "unique_id": "other_unique_id",
                "title": "Other App"
            }
        ]

        with patch.object(config_flow, 'identify_all', return_value=mock_apps):
            result = await config_flow.async_step_user({
                "name": "nonexistent_app"
            })

        assert result["type"] == "form"
        assert "errors" in result

    async def test_identify_all_success(self, config_flow):
        """Test successful app identification."""
        mock_replies = ["compressed_data_1", "compressed_data_2"]

        with patch.object(config_flow.hass.bus, 'async_listen') as mock_listen, \
             patch.object(config_flow.hass.bus, 'async_fire') as mock_fire, \
             patch('asyncio.sleep') as mock_sleep:

            mock_listen.return_value = MagicMock()

            result = await config_flow.identify_all()

            mock_fire.assert_called_once()
            mock_sleep.assert_called_once()
            assert len(result) == 2
```

#### 1.4 WebSocket Tests
```python
# tests/test_websocket.py
import pytest
from unittest.mock import AsyncMock, MagicMock

from homeassistant.components import websocket_api
from custom_components.synapse.websocket import (
    handle_synapse_register,
    handle_synapse_update_entity,
    handle_synapse_heartbeat
)

@pytest.fixture
def mock_connection():
    """Create a mock WebSocket connection."""
    connection = MagicMock(spec=websocket_api.ActiveConnection)
    connection.send_result = AsyncMock()
    connection.send_error = AsyncMock()
    return connection

@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    return MagicMock()

class TestWebSocketHandlers:
    """Test WebSocket command handlers."""

    async def test_handle_synapse_register_success(self, mock_hass, mock_connection):
        """Test successful app registration."""
        msg = {
            "id": 1,
            "type": "synapse/register",
            "app_name": "test_app",
            "unique_id": "test_unique_id",
            "data": {"title": "Test App"}
        }

        await handle_synapse_register(mock_hass, mock_connection, msg)

        mock_connection.send_result.assert_called_once_with(
            1, {"success": True, "registered": True}
        )

    async def test_handle_synapse_register_error(self, mock_hass, mock_connection):
        """Test app registration with error."""
        msg = {
            "id": 1,
            "type": "synapse/register",
            "app_name": "test_app",
            "unique_id": "test_unique_id",
            "data": None  # This will cause an error
        }

        await handle_synapse_register(mock_hass, mock_connection, msg)

        mock_connection.send_error.assert_called_once()

    async def test_handle_synapse_update_entity_success(self, mock_hass, mock_connection):
        """Test successful entity update."""
        msg = {
            "id": 2,
            "type": "synapse/update_entity",
            "unique_id": "test_entity",
            "entity_data": {"state": "on"}
        }

        await handle_synapse_update_entity(mock_hass, mock_connection, msg)

        mock_connection.send_result.assert_called_once_with(
            2, {"success": True, "updated": True}
        )

    async def test_handle_synapse_heartbeat_success(self, mock_hass, mock_connection):
        """Test successful heartbeat."""
        msg = {
            "id": 3,
            "type": "synapse/heartbeat",
            "app_name": "test_app",
            "hash": "test_hash"
        }

        await handle_synapse_heartbeat(mock_hass, mock_connection, msg)

        mock_connection.send_result.assert_called_once_with(
            3, {"success": True, "heartbeat_received": True}
        )
```

### 2. Integration Tests

#### 2.1 Full Setup/Teardown Tests
```python
# tests/test_integration.py
import pytest
from unittest.mock import AsyncMock, MagicMock

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from custom_components.synapse import async_setup_entry, async_unload_entry

@pytest.fixture
def mock_config_entry():
    """Create a mock config entry."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry_id"
    entry.data = {
        "app": "test_app",
        "unique_id": "test_unique_id",
        "title": "Test App"
    }
    return entry

@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = MagicMock(spec=HomeAssistant)
    hass.data = {}
    return hass

class TestIntegration:
    """Test full integration setup and teardown."""

    async def test_async_setup_entry_success(self, mock_hass, mock_config_entry):
        """Test successful integration setup."""
        with patch('custom_components.synapse.SynapseBridge') as mock_bridge_class:
            mock_bridge = MagicMock()
            mock_bridge.async_reload = AsyncMock()
            mock_bridge_class.return_value = mock_bridge

            result = await async_setup_entry(mock_hass, mock_config_entry)

            assert result is True
            mock_bridge.async_reload.assert_called_once()

    async def test_async_unload_entry_success(self, mock_hass, mock_config_entry):
        """Test successful integration unload."""
        # Setup bridge in hass data
        mock_bridge = MagicMock()
        mock_bridge.async_cleanup = AsyncMock()
        mock_hass.data["synapse"] = {mock_config_entry.entry_id: mock_bridge}

        result = await async_unload_entry(mock_hass, mock_config_entry)

        assert result is True
        mock_bridge.async_cleanup.assert_called_once()

    async def test_entity_creation_and_removal(self, mock_hass, mock_config_entry):
        """Test entity creation and removal during reload."""
        # This would test the full entity lifecycle
        pass
```

### 3. Test Configuration

#### 3.1 pytest Configuration
```ini
# pytest.ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    --strict-markers
    --strict-config
    --cov=custom_components/synapse
    --cov-report=term-missing
    --cov-report=html
    --cov-fail-under=80
markers =
    integration: marks tests as integration tests
    unit: marks tests as unit tests
    slow: marks tests as slow
```

#### 3.2 conftest.py
```python
# tests/conftest.py
import pytest
from unittest.mock import AsyncMock, MagicMock

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

@pytest.fixture
def hass():
    """Create a mock Home Assistant instance."""
    hass = MagicMock(spec=HomeAssistant)
    hass.data = {}
    return hass

@pytest.fixture
def config_entry():
    """Create a mock config entry."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry_id"
    entry.data = {
        "app": "test_app",
        "unique_id": "test_unique_id",
        "title": "Test App",
        "version": "1.0.0"
    }
    return entry

@pytest.fixture
def websocket_client(hass):
    """Create a WebSocket client for testing."""
    # Implementation for WebSocket client
    pass
```

### 4. CI/CD Pipeline

#### 4.1 GitHub Actions Workflow
```yaml
# .github/workflows/test.yml
name: Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.9, 3.10, 3.11]

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install pytest pytest-cov pytest-asyncio
        pip install homeassistant

    - name: Run tests
      run: |
        pytest tests/ --cov=custom_components/synapse --cov-report=xml

    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
        fail_ci_if_error: true
```

## 📋 Implementation Checklist

### Phase 1: Test Framework Setup (Week 1)
- [ ] Create `tests/` directory structure
- [ ] Create `conftest.py` with fixtures
- [ ] Set up `pytest.ini` configuration
- [ ] Create GitHub Actions workflow
- [ ] Set up coverage reporting

### Phase 2: Unit Tests (Week 2)
- [ ] Write bridge tests
- [ ] Write entity tests
- [ ] Write config flow tests
- [ ] Write WebSocket tests
- [ ] Write helper function tests

### Phase 3: Integration Tests (Week 2)
- [ ] Write setup/teardown tests
- [ ] Write entity lifecycle tests
- [ ] Write WebSocket integration tests
- [ ] Write error condition tests

### Phase 4: Coverage and CI (Week 3)
- [ ] Achieve 80%+ test coverage
- [ ] Set up automated testing
- [ ] Add test documentation
- [ ] Performance testing

## 🎯 Success Criteria

- ✅ 80%+ test coverage achieved
- ✅ All critical paths tested
- ✅ Error conditions tested
- ✅ Integration tests pass
- ✅ CI/CD pipeline working
- ✅ Tests run in reasonable time
- ✅ Mock usage is appropriate

## 📝 Notes

- 80% coverage is required for core acceptance
- Focus on critical paths and error conditions
- Use appropriate mocks to isolate units
- Integration tests should test real scenarios
- CI/CD ensures quality on every change
