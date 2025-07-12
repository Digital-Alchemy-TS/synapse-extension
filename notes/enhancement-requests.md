# Enhancement Requests

## Overview
This document captures enhancement requests from users and community feedback for the Synapse integration.

## 🔧 Requested Features

### 1. Multiple Connections with Priority System

**Request**: Allow 2+ connections using the same `unique_id` with a `priority` number. Only traffic to/from the highest priority should be considered.

**Use Case**: Dev/prod setups where dev is higher priority for quick testing.

**Technical Considerations**:
- Need to track multiple WebSocket connections per `unique_id`
- Priority system (higher number = higher priority)
- Automatic failover when higher priority connection comes online
- Graceful handling when lower priority connections disconnect
- Conflict resolution for entity updates from multiple sources
- Heartbeat management across multiple connections

**Implementation Notes**:
- Bridge registry needs to support multiple connections per app
- Entity updates should only come from highest priority connection
- Discovery should show all connected instances with their priorities
- Config flow should allow selecting which instance to configure

### 2. Dynamic Service Creation

**Request**: Allow apps to create custom services by sending a schema. Calling the service sends payload over WebSocket to trigger TypeScript code.

**Use Case**: Apps want to expose custom functionality as Home Assistant services.

**Technical Considerations**:
- Service schema validation and registration
- Dynamic service discovery and registration
- WebSocket message routing for service calls
- Service parameter validation
- Response handling from TypeScript side
- Service cleanup when app disconnects

**Implementation Notes**:
- Need to register services with Home Assistant's service registry
- Service calls need to be routed to correct app via WebSocket
- Schema should support standard Home Assistant service parameter types
- Services should be namespaced (e.g., `synapse.my_app.custom_service`)
- Need to handle service call timeouts and errors

### 3. External Device Attachment

**Request**: Allow entities to be attached to other integration's devices instead of only synapse devices.

**Use Case**: Apps want to add sensors/switches to existing devices from other integrations.

**Technical Considerations**:
- Device registry lookup and validation
- Permission/security considerations
- Entity-device association validation
- Cleanup when external device is removed
- Conflict resolution with device owner

**Implementation Notes**:
- Need to validate that target device exists and is accessible
- Consider security implications of attaching to other integrations' devices
- May need device owner permission system
- Should support both synapse devices and external devices
- Entity creation should validate device compatibility

### 4. WebSocket-Based Discovery

**Request**: Implement discovery mechanism that works with 100% WebSocket-based communications.

**Use Case**: Automatic discovery of synapse apps without manual configuration.

**Technical Considerations**:
- No traditional discovery protocols (SSDP, mDNS, etc.)
- WebSocket-based app advertisement
- Discovery timing and coordination
- Handling multiple Home Assistant instances
- Discovery security and validation

**Implementation Notes**:
- Apps could broadcast their presence via WebSocket
- Discovery could use existing WebSocket connection
- Need to handle discovery across multiple HA instances
- May need discovery service registration
- Consider using WebSocket sub-protocols for discovery

## 📋 Implementation Priority

### High Priority
1. **Multiple Connections with Priority** - Solves real-world dev/prod workflow issues
2. **Dynamic Service Creation** - Significantly expands integration capabilities

### Medium Priority
3. **External Device Attachment** - Useful for complex setups but has security considerations

### Low Priority
4. **WebSocket-Based Discovery** - Nice to have but not critical for core functionality

## 🎯 Success Criteria

### Multiple Connections
- ✅ Multiple apps can connect with same `unique_id`
- ✅ Priority system works correctly
- ✅ Automatic failover to highest priority
- ✅ No conflicts between multiple connections

### Dynamic Services
- ✅ Apps can register custom services
- ✅ Service calls reach TypeScript code
- ✅ Proper schema validation
- ✅ Services are cleaned up on disconnect

### External Devices
- ✅ Entities can attach to external devices
- ✅ Proper validation and security
- ✅ Clean integration with existing devices

### WebSocket Discovery
- ✅ Automatic app discovery via WebSocket
- ✅ Works across multiple HA instances
- ✅ Secure and reliable

## 📝 Notes

- These enhancements would significantly expand the integration's capabilities
- Priority system is most requested and solves real workflow issues
- Service creation opens up many new use cases
- External device attachment requires careful security consideration
- WebSocket discovery is innovative but may be complex to implement

## 🔗 Related Issues

- Multiple connection support would solve dev/prod workflow issues
- Service creation would enable more complex automation scenarios
- External device attachment would improve integration with existing setups
- Discovery would improve user experience for initial setup
