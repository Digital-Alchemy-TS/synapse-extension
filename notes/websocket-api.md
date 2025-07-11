# WebSocket API Implementation

## Overview
Replace the current event bus abuse with Home Assistant's proper WebSocket API for external communication.

## 🔴 Current Problem

The integration currently abuses the Home Assistant event bus for external communication:
- **Not intended purpose**: Event bus is for internal HA communication
- **Performance issues**: Overhead from event processing
- **Security concerns**: No authentication or validation
- **Scalability problems**: Doesn't handle multiple connections well
- **Non-standard pattern**: Goes against HA design principles

## ✅ Solution: WebSocket API

Home Assistant provides a proper WebSocket API specifically designed for external communication.

### Key Benefits
- **Bidirectional communication**: Apps can send commands AND receive responses
- **Proper authentication**: Can implement API keys, tokens, etc.
- **Better performance**: Direct communication without event bus overhead
- **Standard pattern**: This is how other integrations handle external communication
- **Scalable**: Handles multiple connections efficiently
- **Error handling**: Proper error responses and status codes

## 📋 Implementation Plan

### Phase 1: Create WebSocket Command Handlers

#### 1.1 Create `websocket.py` file
```python
# custom_components/synapse/websocket.py
from __future__ import annotations
from typing import Any
import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv

from .synapse.const import DOMAIN

DOMAIN_WS = f"{DOMAIN}_ws"

@websocket_api.websocket_command({
    vol.Required("type"): "synapse/register",
    vol.Required("app_name"): str,
    vol.Required("unique_id"): str,
    vol.Required("data"): dict,
})
@websocket_api.async_response
async def handle_synapse_register(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict
) -> None:
    """Handle synapse app registration."""
    try:
        # Validate the incoming data
        # Register the app
        # Return success response
        connection.send_result(msg["id"], {"success": True, "registered": True})
    except Exception as e:
        connection.send_error(msg["id"], "registration_failed", str(e))

@websocket_api.websocket_command({
    vol.Required("type"): "synapse/update_entity",
    vol.Required("unique_id"): str,
    vol.Required("entity_data"): dict,
})
@websocket_api.async_response
async def handle_synapse_update_entity(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict
) -> None:
    """Handle entity updates from synapse apps."""
    try:
        # Update the entity
        # Return success response
        connection.send_result(msg["id"], {"success": True, "updated": True})
    except Exception as e:
        connection.send_error(msg["id"], "update_failed", str(e))

@websocket_api.websocket_command({
    vol.Required("type"): "synapse/heartbeat",
    vol.Required("app_name"): str,
    vol.Optional("hash"): str,
})
@websocket_api.async_response
async def handle_synapse_heartbeat(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict
) -> None:
    """Handle heartbeat from synapse apps."""
    try:
        # Process heartbeat
        # Check for hash changes
        # Return success response
        connection.send_result(msg["id"], {"success": True, "heartbeat_received": True})
    except Exception as e:
        connection.send_error(msg["id"], "heartbeat_failed", str(e))

@websocket_api.websocket_command({
    vol.Required("type"): "synapse/discovery",
})
@websocket_api.async_response
async def handle_synapse_discovery(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict
) -> None:
    """Handle discovery requests from synapse apps."""
    try:
        # Return list of registered apps
        apps = []  # Get from bridge registry
        connection.send_result(msg["id"], {"apps": apps})
    except Exception as e:
        connection.send_error(msg["id"], "discovery_failed", str(e))
```

#### 1.2 Register WebSocket Commands
```python
# In custom_components/synapse/__init__.py
async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Synapse component."""
    # Register WebSocket commands
    websocket_api.async_register_command(hass, handle_synapse_register)
    websocket_api.async_register_command(hass, handle_synapse_update_entity)
    websocket_api.async_register_command(hass, handle_synapse_heartbeat)
    websocket_api.async_register_command(hass, handle_synapse_discovery)

    return True
```

### Phase 2: Update Bridge to Use WebSocket

#### 2.1 Modify Bridge Class
```python
# custom_components/synapse/synapse/bridge.py
class SynapseBridge:
    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        # ... existing init code ...

        # Add WebSocket connection tracking
        self._websocket_connections: dict[str, websocket_api.ActiveConnection] = {}

    async def register_websocket_connection(self, app_name: str, connection: websocket_api.ActiveConnection) -> None:
        """Register a WebSocket connection for an app."""
        self._websocket_connections[app_name] = connection

    async def send_to_app(self, app_name: str, message: dict) -> None:
        """Send a message to a specific app via WebSocket."""
        if app_name in self._websocket_connections:
            connection = self._websocket_connections[app_name]
            connection.send_message(websocket_api.result_message(0, message))
```

#### 2.2 Remove Event Bus Usage
- Remove all `self.hass.bus.async_fire()` calls
- Remove all `self.hass.bus.async_listen()` calls
- Replace with WebSocket communication

### Phase 3: Update Node.js Client

#### 3.1 Basic WebSocket Connection
```typescript
// Your Node.js app
class SynapseWebSocketClient {
    private connection: WebSocket;
    private messageId = 0;

    constructor(host: string, port: number = 8123) {
        this.connection = new WebSocket(`ws://${host}:${port}/api/websocket`);
        this.setupEventHandlers();
    }

    private setupEventHandlers() {
        this.connection.onopen = () => {
            console.log('Connected to Home Assistant WebSocket API');
        };

        this.connection.onmessage = (event) => {
            const response = JSON.parse(event.data);
            this.handleResponse(response);
        };

        this.connection.onerror = (error) => {
            console.error('WebSocket error:', error);
        };

        this.connection.onclose = () => {
            console.log('Disconnected from Home Assistant');
        };
    }

    private handleResponse(response: any) {
        if (response.type === 'result') {
            // Handle successful response
            console.log('Response:', response.result);
        } else if (response.type === 'error') {
            // Handle error response
            console.error('Error:', response.error);
        }
    }

    private sendMessage(type: string, data: any): number {
        const id = ++this.messageId;
        const message = {
            id,
            type,
            ...data
        };
        this.connection.send(JSON.stringify(message));
        return id;
    }

    // Public API methods
    async register(appName: string, uniqueId: string, data: any): Promise<any> {
        return this.sendMessage('synapse/register', {
            app_name: appName,
            unique_id: uniqueId,
            data
        });
    }

    async updateEntity(uniqueId: string, entityData: any): Promise<any> {
        return this.sendMessage('synapse/update_entity', {
            unique_id: uniqueId,
            entity_data: entityData
        });
    }

    async sendHeartbeat(appName: string, hash?: string): Promise<any> {
        return this.sendMessage('synapse/heartbeat', {
            app_name: appName,
            hash
        });
    }

    async requestDiscovery(): Promise<any> {
        return this.sendMessage('synapse/discovery', {});
    }
}
```

#### 3.2 Usage Example
```typescript
const client = new SynapseWebSocketClient('homeassistant.local');

// Register the app
await client.register('my_app', 'unique_app_id', {
    title: 'My App',
    version: '1.0.0',
    // ... other app data
});

// Update an entity
await client.updateEntity('switch_1', {
    state: 'on',
    attributes: { friendly_name: 'My Switch' }
});

// Send heartbeat
setInterval(() => {
    client.sendHeartbeat('my_app', 'current_hash');
}, 30000);
```

### Phase 4: Add Authentication

#### 4.1 API Key Authentication
```python
# In websocket.py
@websocket_api.require_admin
@websocket_api.websocket_command({
    vol.Required("type"): "synapse/register",
    vol.Required("app_name"): str,
    vol.Required("unique_id"): str,
    vol.Required("api_key"): str,  # Add API key requirement
    vol.Required("data"): dict,
})
@websocket_api.async_response
async def handle_synapse_register(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict
) -> None:
    """Handle synapse app registration with API key validation."""
    try:
        # Validate API key
        api_key = msg.get("api_key")
        if not await validate_api_key(hass, api_key):
            connection.send_error(msg["id"], "invalid_api_key", "Invalid API key")
            return

        # Continue with registration
        connection.send_result(msg["id"], {"success": True, "registered": True})
    except Exception as e:
        connection.send_error(msg["id"], "registration_failed", str(e))
```

#### 4.2 Configuration for API Keys
```yaml
# In configuration.yaml
synapse:
  api_keys:
    - name: "My App"
      key: "your-secret-api-key-here"
```

## 🧪 Testing

### 4.1 Unit Tests
```python
# tests/test_websocket.py
import pytest
from unittest.mock import AsyncMock, MagicMock

from homeassistant.components import websocket_api
from custom_components.synapse.websocket import handle_synapse_register

async def test_websocket_register_success(hass):
    """Test successful app registration via WebSocket."""
    connection = MagicMock()
    connection.send_result = AsyncMock()

    msg = {
        "id": 1,
        "type": "synapse/register",
        "app_name": "test_app",
        "unique_id": "test_unique_id",
        "data": {"title": "Test App"}
    }

    await handle_synapse_register(hass, connection, msg)

    connection.send_result.assert_called_once_with(1, {"success": True, "registered": True})
```

### 4.2 Integration Tests
```python
# tests/test_websocket_integration.py
async def test_websocket_connection_lifecycle(hass, websocket_client):
    """Test full WebSocket connection lifecycle."""
    # Test connection
    await websocket_client.connect()

    # Test registration
    response = await websocket_client.send_json({
        "id": 1,
        "type": "synapse/register",
        "app_name": "test_app",
        "unique_id": "test_unique_id",
        "data": {"title": "Test App"}
    })

    assert response["success"] is True
```

## 📚 Migration Strategy

### Step 1: Implement WebSocket API (Week 1)
- Create `websocket.py` with command handlers
- Register WebSocket commands in `__init__.py`
- Add basic authentication

### Step 2: Update Bridge (Week 2)
- Modify bridge to use WebSocket instead of event bus
- Add connection tracking
- Remove event bus listeners

### Step 3: Update Node.js Client (Week 3)
- Create new WebSocket client class
- Update existing apps to use new client
- Test bidirectional communication

### Step 4: Remove Event Bus (Week 4)
- Remove all event bus usage
- Clean up unused code
- Final testing and validation

## 🎯 Success Criteria

- ✅ WebSocket API handles all current event bus functionality
- ✅ Bidirectional communication works properly
- ✅ Authentication is implemented
- ✅ Error handling is robust
- ✅ Performance is improved
- ✅ No event bus usage remains

## 📝 Notes

- This is the most critical change for core acceptance
- WebSocket API is the standard pattern for external communication
- Provides better security and performance
- Enables proper bidirectional communication
- Follows Home Assistant's established patterns
