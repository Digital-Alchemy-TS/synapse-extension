# Communication Workflow Documentation

## 🎯 Overview

This document details the complete communication workflow between NodeJS Synapse applications and the Home Assistant Synapse extension. The workflow uses WebSocket API for bidirectional communication and implements a hash-based synchronization system.

## 🔄 Connection & Registration Flow

### Initial Connection Sequence

```mermaid
sequenceDiagram
    participant App as NodeJS App
    participant WS as WebSocket API
    participant Bridge as Synapse Bridge
    participant Registry as App Registry
    participant Storage as Hash Storage

    App->>WS: Connect to Home Assistant WebSocket API
    WS->>App: Connection established

    Note over App: App sends "hello world" message
    App->>WS: synapse/register {unique_id, app_metadata}
    WS->>Bridge: Forward registration request

    Note over Bridge: Check for existing connections
    Bridge->>Bridge: Validate unique_id not in use
    alt unique_id already connected
        Bridge->>WS: Error: unique_id already in use
        WS->>App: Registration failed
    else unique_id available
        Bridge->>Registry: Check if app is registered
        alt App not registered
            Bridge->>WS: Error: app not registered
            WS->>App: Registration failed
        else App registered
            Bridge->>Storage: Get last known hash for app
            Storage->>Bridge: Return stored hash
            Bridge->>WS: Registration success + last hash
            WS->>App: Registration acknowledged
        end
    end
```

### App Metadata Structure

The "hello world" message contains the following metadata:

```typescript
interface AppMetadata {
  app: string;                    // Application name
  device: DeviceInfo;             // Primary device information
  hash: string;                   // Current configuration hash
  hostname: string;               // Host machine name
  secondary_devices: Device[];    // Additional devices
  title: string;                  // Human-readable title
  unique_id: string;              // Unique identifier
  username: string;               // System username
  // ... additional storage dump data
}
```

## 🔄 Hash Synchronization Flow

### Configuration Synchronization

```mermaid
sequenceDiagram
    participant App as NodeJS App
    participant Storage as App Storage
    participant WS as WebSocket API
    participant Bridge as Synapse Bridge
    participant Entities as Entity Registry

    Note over App: App receives registration ack with last hash
    App->>Storage: Generate current hash
    Storage->>App: Return current hash

    App->>App: Compare hashes
    alt Hash mismatch
        Note over App: Configuration has changed
        App->>Storage: Get full configuration dump
        Storage->>App: Return entities + devices

        App->>WS: synapse/update_configuration
        WS->>Bridge: Forward configuration update
        Bridge->>Entities: Reconfigure all entities/devices
        Entities->>Bridge: Configuration applied

        Bridge->>WS: Configuration update success
        WS->>App: Configuration synchronized
    else Hash match
        Note over App: Configuration is current
        App->>App: Proceed to runtime mode
    end
```

### Runtime State Management

```mermaid
sequenceDiagram
    participant App as NodeJS App
    participant WS as WebSocket API
    participant Bridge as Synapse Bridge
    participant Entities as Entity Registry

    Note over App: App enters runtime mode

    loop Every 30 seconds
        App->>WS: synapse/heartbeat {hash}
        WS->>Bridge: Forward heartbeat
        Bridge->>Bridge: Check hash drift
        alt Hash changed
            Bridge->>WS: Request configuration update
            WS->>App: synapse/request_configuration
            App->>WS: synapse/update_configuration
            WS->>Bridge: Forward new configuration
            Bridge->>Entities: Update entities/devices
        else Hash unchanged
            Bridge->>WS: Heartbeat acknowledged
            WS->>App: Heartbeat success
        end
    end
```

## 🔄 App Disconnection Flow

### Graceful Shutdown (SIGINT Handling)

When an app receives a SIGINT signal (Ctrl+C, process termination), it should perform a graceful shutdown:

```mermaid
sequenceDiagram
    participant App as NodeJS App
    participant WS as WebSocket API
    participant Bridge as Synapse Bridge
    participant Entities as Entity Registry

    Note over App: App receives SIGINT signal
    App->>WS: synapse/going_offline {unique_id}
    WS->>Bridge: Forward going offline message
    Bridge->>Bridge: Immediately mark app as offline
    Bridge->>Bridge: Clean up WebSocket connection
    Bridge->>Entities: Update entity availability
    Bridge->>WS: Going offline acknowledged
    WS->>App: Acknowledgment received
    App->>WS: Close WebSocket connection
    App->>App: Terminate process
```

### Unexpected Disconnection (Timeout)

When an app suddenly stops (power loss, crash, network issues), the bridge detects this through heartbeat timeout:

```mermaid
sequenceDiagram
    participant App as NodeJS App
    participant WS as WebSocket API
    participant Bridge as Synapse Bridge
    participant Entities as Entity Registry

    Note over App: App suddenly stops (no SIGINT)
    Note over Bridge: No heartbeat received for 30 seconds
    Bridge->>Bridge: Heartbeat timeout detected
    Bridge->>Bridge: Mark app as offline
    Bridge->>Bridge: Clean up WebSocket connection
    Bridge->>Entities: Update entity availability
    Bridge->>Bridge: Fire health event
    Entities->>Entities: Update online/offline status
```

### Disconnection Handling Comparison

| Scenario | Signal | Bridge Response | Cleanup Actions |
|----------|--------|-----------------|-----------------|
| **Graceful Shutdown** | SIGINT | Immediate offline | Connection cleanup, entity availability update |
| **Unexpected Stop** | None (timeout) | 30-second delay | Connection cleanup, entity availability update |

### Implementation Notes

#### TypeScript Side (App)
```typescript
// Graceful shutdown handler
process.on('SIGINT', async () => {
  console.log('Received SIGINT, shutting down gracefully...');

  try {
    // Send going offline message
    await client.sendMessage('synapse/going_offline', {
      unique_id: appUniqueId
    });

    // Wait for acknowledgment
    await new Promise(resolve => setTimeout(resolve, 1000));

    // Close WebSocket connection
    client.disconnect();

    console.log('Graceful shutdown complete');
    process.exit(0);
  } catch (error) {
    console.error('Error during graceful shutdown:', error);
    process.exit(1);
  }
});
```

#### Python Side (Bridge)
```python
async def handle_going_offline(self, unique_id: str) -> Dict[str, Any]:
    """Handle graceful app shutdown."""
    self.logger.info(f"App {unique_id} going offline gracefully")

    # Immediately mark as offline
    self.online = False

    # Clean up WebSocket connection
    self.unregister_websocket_connection(unique_id)

    # Update entity availability
    self.hass.bus.async_fire(self.event_name("health"))

    return {
        "success": True,
        "offline": True,
        "message": "App marked as offline"
    }
```

## 🔄 Entity Update Flow

### Runtime Entity Patches

```mermaid
sequenceDiagram
    participant App as NodeJS App
    participant WS as WebSocket API
    participant Bridge as Synapse Bridge
    participant Entities as Entity Registry

    Note over App: Entity state/configuration changes

    App->>WS: synapse/update_entity {unique_id, changes}
    WS->>Bridge: Forward entity update
    Bridge->>Bridge: Validate entity exists
    alt Entity not found
        Bridge->>WS: Error: entity not found
        WS->>App: Update failed
    else Entity found
        Bridge->>Entities: Apply entity changes
        Entities->>Bridge: Changes applied

        Note over Bridge: No hash change for patches
        Bridge->>WS: Entity update success
        WS->>App: Update acknowledged
    end
```

### Supported Entity Patch Types

The following entity updates are supported during runtime (no hash change):

1. **State Changes**
   - Sensor values
   - Switch states
   - Climate settings
   - Any entity state updates

2. **Visual Changes**
   - Icon updates
   - Name changes
   - Attribute modifications

3. **Configuration Changes**
   - Enable/disable entities
   - Related entity associations
   - Custom attributes

4. **Device Changes**
   - Device information updates
   - Device availability status

## 🚨 Error Handling

### Connection Errors

```mermaid
flowchart TD
    A[Connection Attempt] --> B{Connection Success?}
    B -->|No| C[Log Error]
    C --> D[Retry with Backoff]
    D --> A

    B -->|Yes| E[Send Registration]
    E --> F{Registration Success?}
    F -->|No| G[Handle Registration Error]
    G --> H[Log Error Details]
    H --> I[Retry or Exit]

    F -->|Yes| J[Proceed to Runtime]
```

### Hash Drift Recovery

```mermaid
flowchart TD
    A[Heartbeat Sent] --> B{Hash Match?}
    B -->|Yes| C[Continue Normal Operation]
    B -->|No| D[Request Full Configuration]
    D --> E[Receive Configuration]
    E --> F[Apply Configuration]
    F --> G{Configuration Success?}
    G -->|Yes| H[Update Stored Hash]
    G -->|No| I[Log Configuration Error]
    I --> J[Retry Configuration]
    H --> C
```

## 🔧 Future Enhancements

### Multiple Connection Support (Planned)

```mermaid
sequenceDiagram
    participant App1 as Dev App
    participant App2 as Prod App
    participant WS as WebSocket API
    participant Bridge as Synapse Bridge

    Note over App1,App2: Both apps use same unique_id

    App1->>WS: Register with priority 2
    WS->>Bridge: Register high priority
    Bridge->>Bridge: Set as active connection

    App2->>WS: Register with priority 1
    WS->>Bridge: Register low priority
    Bridge->>Bridge: Keep as backup

    Note over Bridge: Only App1 receives updates
    Bridge->>WS: Send updates to App1 only

    Note over App1: Dev app disconnects
    App1->>WS: Disconnect
    Bridge->>Bridge: Failover to App2
    Bridge->>WS: Send updates to App2
```

### Dynamic Service Creation (Planned)

```mermaid
sequenceDiagram
    participant App as NodeJS App
    participant WS as WebSocket API
    participant Bridge as Synapse Bridge
    participant Services as Service Registry

    App->>WS: synapse/register_service {schema}
    WS->>Bridge: Forward service registration
    Bridge->>Services: Register dynamic service
    Services->>Bridge: Service registered

    Note over Services: User calls service
    Services->>Bridge: Service call received
    Bridge->>WS: Forward to app
    WS->>App: synapse/service_call {data}
    App->>WS: synapse/service_response {result}
    WS->>Bridge: Forward response
    Bridge->>Services: Return result to user
```

## 📋 Implementation Notes

### WebSocket Commands

| Command | Direction | Purpose | Payload |
|---------|-----------|---------|---------|
| `synapse/register` | App → HA | Initial registration | App metadata |
| `synapse/heartbeat` | App → HA | Health check | Current hash |
| `synapse/update_entity` | App → HA | Entity updates | Entity changes |
| `synapse/update_configuration` | App → HA | Full config sync | Complete config |
| `synapse/request_configuration` | HA → App | Request config | None |
| `synapse/going_offline` | App → HA | Graceful shutdown | Unique ID |
| `synapse/register_service` | App → HA | Service registration | Service schema |
| `synapse/service_call` | HA → App | Service invocation | Service data |
| `synapse/service_response` | App → HA | Service response | Service result |

### Hash Generation

The hash is generated from the complete application configuration:

```typescript
// Simplified hash generation
function generateHash(config: AppConfiguration): string {
  const normalized = normalizeConfiguration(config);
  return createHash('sha256')
    .update(JSON.stringify(normalized))
    .digest('hex');
}
```

### Connection Management

- **Unique ID Validation**: Prevents multiple active connections with same ID
- **Priority System**: Future enhancement for dev/prod workflows
- **Graceful Disconnect**: Clean up resources when apps disconnect
- **Reconnection**: Apps can reconnect and resume operation

### Error Recovery

- **Connection Loss**: Automatic reconnection with exponential backoff
- **Hash Drift**: Request full configuration resync
- **Invalid Data**: Log errors and continue operation
- **Service Failures**: Retry with appropriate error handling

## 🎯 Success Criteria

### Connection & Registration
- ✅ Apps can connect and register successfully
- ✅ Duplicate unique_id connections are rejected
- ✅ Unregistered apps are rejected
- ✅ Hash synchronization works correctly

### Runtime Operation
- ✅ Heartbeats maintain connection health
- ✅ Hash drift detection triggers resync
- ✅ Entity updates are applied correctly
- ✅ No hash changes for runtime patches

### Error Handling
- ✅ Connection failures are handled gracefully
- ✅ Invalid data doesn't crash the system
- ✅ Recovery mechanisms work correctly
- ✅ Comprehensive error logging

### Future Enhancements
- ✅ Multiple connection support (planned)
- ✅ Dynamic service creation (planned)
- ✅ External device attachment (planned)
- ✅ WebSocket-based discovery (planned)

---

**Last Updated**: [Current Date]
**Status**: Documentation Complete
**Next Review**: After WebSocket Implementation
