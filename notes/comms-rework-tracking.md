# Communication Rework - Working Document

## 🎯 Project Overview

**Goal**: Replace the current event bus abuse with proper WebSocket API communication between Home Assistant and external Synapse applications.

**Current Status**: Planning phase - analyzing existing code and TypeScript libraries for reference.

**Timeline**:
- Phase 1: Python rework (current)
- Phase 2: TypeScript library updates (future)

## 📋 Current State Analysis

### Python Side (Home Assistant Integration)
**Location**: `custom_components/synapse/`

#### Key Files:
- `__init__.py` - Main integration setup
- `synapse/bridge.py` - Core communication logic (13KB, 341 lines)
- `synapse/base_entity.py` - Base entity class (4.3KB, 133 lines)
- `synapse/const.py` - Constants and types (3.9KB, 169 lines)
- `synapse/helpers.py` - Utility functions (478B, 17 lines)
- Entity files: `sensor.py`, `switch.py`, `climate.py`, etc.

#### Current Communication Pattern:
- Uses Home Assistant event bus for external communication
- `hass.bus.async_fire()` to send events
- `hass.bus.async_listen()` to receive events
- **Problem**: Event bus is for internal HA communication, not external apps

### TypeScript Side (Reference Libraries)
**Location**: `src/`

#### Key Files:
- `synapse.module.mts` - Main module (4.7KB, 203 lines)
- `index.mts` - Entry point
- `dev-types.mts` - Type definitions
- `services/` - Service implementations
- `helpers/` - Utility functions
- `mock/` - Mock implementations for testing

#### Current Communication Pattern:
- Likely uses HTTP API or event bus communication
- Needs to be updated to use WebSocket API

## 🔄 Corrected Communication Workflow

### Connection & Registration Flow
1. **NodeJS App connects** to Home Assistant via WebSocket API
2. **App sends "hello world"** message with app metadata (see `src/services/discovery.service.mts`)
3. **Extension validates unique_id** against existing connections (error if already in use)
4. **Extension checks unique_id** against registered apps list
5. **If not registered**: Do not continue (see enhancement requests for future discovery plans)
6. **If registered**: Send acknowledgment with last known app hash
7. **TS side compares hashes** using `storage.hash()` function
8. **If hash mismatch**: Transmit full entity/device configuration
9. **Configuration becomes source of truth** for HA entity/device management
10. **App enters "runtime" mode**

### Runtime Operation
- **Heartbeat every 30 seconds** with current hash
- **Hash drift detection** triggers configuration resync request
- **Entity patches** for state changes, icons, enable/disable, related entities
- **No hash changes** for runtime patches

## 🔄 Planned Changes

### Phase 1: Python WebSocket Implementation

#### 1.1 Create WebSocket Command Handlers
**File**: `custom_components/synapse/websocket.py` (NEW)

**Commands to implement**:
- `synapse/register` - App registration with metadata
- `synapse/heartbeat` - Health monitoring with hash
- `synapse/update_entity` - Runtime entity patches
- `synapse/update_configuration` - Full config sync
- `synapse/request_configuration` - Request config from app

#### 1.2 Update Bridge Class
**File**: `custom_components/synapse/synapse/bridge.py`

**Changes needed**:
- Remove event bus usage
- Add WebSocket connection tracking
- Implement hash-based synchronization
- Add unique_id validation
- Improve error handling
- Support configuration resync requests

#### 1.3 Update Integration Setup
**File**: `custom_components/synapse/__init__.py`

**Changes needed**:
- Register WebSocket commands
- Update bridge initialization
- Remove event bus listeners

### Phase 2: TypeScript Library Updates

#### 2.1 WebSocket Client Implementation
**File**: `src/synapse.module.mts`

**Changes needed**:
- Replace HTTP/event bus with WebSocket
- Implement proper connection management
- Add hash comparison logic
- Update heartbeat mechanism
- Add configuration sync support

#### 2.2 Update Service Implementations
**Location**: `src/services/`

**Changes needed**:
- Update discovery service for WebSocket
- Update all services to use WebSocket
- Maintain backward compatibility during transition
- Update error handling

## 📊 Implementation Status

### Phase 1: Python Implementation

#### ✅ Completed
- [x] Analysis of current code structure
- [x] Documentation of current communication patterns
- [x] Detailed workflow documentation with Mermaid diagrams
- [x] Understanding of hash-based synchronization

#### 🔄 In Progress
- [ ] Create `websocket.py` file
- [ ] Implement command handlers
- [ ] Update bridge class

#### ⏳ Pending
- [ ] Update integration setup
- [ ] Test WebSocket communication
- [ ] Update entity files if needed
- [ ] Add proper error handling
- [ ] Add authentication/validation

### Phase 2: TypeScript Implementation

#### ✅ Completed
- [x] Reference libraries available in `src/`
- [x] Analysis of current TypeScript structure
- [x] Understanding of discovery service workflow

#### ⏳ Pending
- [ ] Wait for Python implementation completion
- [ ] Update WebSocket client
- [ ] Update service implementations
- [ ] Maintain backward compatibility
- [ ] Update documentation

## 🧪 Testing Strategy

### Python Testing
1. **Unit Tests**: Test individual WebSocket handlers
2. **Integration Tests**: Test bridge with WebSocket
3. **Manual Testing**: Test with real Home Assistant instance
4. **Hash Synchronization**: Test hash comparison and resync
5. **Connection Management**: Test unique_id validation

### TypeScript Testing
1. **Unit Tests**: Test WebSocket client methods
2. **Integration Tests**: Test with Python implementation
3. **Mock Testing**: Use existing mock implementations
4. **Hash Testing**: Test hash generation and comparison
5. **Real-world Testing**: Test with actual applications

## 📝 Technical Decisions

### WebSocket Command Structure
```json
{
  "id": 1,
  "type": "synapse/register",
  "unique_id": "unique_app_id",
  "app_metadata": {
    "app": "my_app",
    "title": "My App",
    "hash": "current_hash",
    "device": {...},
    "secondary_devices": [...],
    "hostname": "hostname",
    "username": "username"
  }
}
```

### Hash Synchronization
- **Hash Generation**: Based on complete app configuration
- **Hash Comparison**: Used to detect configuration changes
- **Resync Trigger**: When hash drift is detected
- **Runtime Patches**: Don't change hash, only for state/config updates

### Authentication Strategy
- **Option 1**: API keys in config
- **Option 2**: Long-lived access tokens
- **Option 3**: App-specific tokens
- **Decision**: TBD based on security requirements

### Error Handling
- Proper error codes and messages
- Retry logic for transient failures
- Graceful degradation
- Comprehensive logging

## 🚨 Known Issues

### Current Problems
1. **Event Bus Abuse**: Using internal HA event bus for external communication
2. **No Authentication**: No proper security for external connections
3. **Performance**: Event bus overhead for external communication
4. **Scalability**: Doesn't handle multiple connections well

### Potential Challenges
1. **Backward Compatibility**: Ensuring existing apps continue to work
2. **Connection Management**: Handling WebSocket connection lifecycle
3. **Hash Synchronization**: Proper hash generation and comparison
4. **Configuration Resync**: Handling full configuration updates
5. **Testing**: Comprehensive testing of new communication layer

## 📚 Reference Materials

### Home Assistant WebSocket API
- [WebSocket API Documentation](https://developers.home-assistant.io/docs/api/websocket)
- [WebSocket Command Examples](https://developers.home-assistant.io/docs/api/websocket#command-examples)

### Current Implementation
- `notes/websocket-api.md` - Detailed WebSocket implementation plan
- `notes/code-quality.md` - Code quality improvements needed
- `notes/comms-workflow.md` - Complete workflow documentation with diagrams

### TypeScript Libraries
- `src/synapse.module.mts` - Main module reference
- `src/services/discovery.service.mts` - Discovery service reference
- `src/services/` - Service implementations reference

### Enhancement Requests
- `notes/enhancement-requests.md` - Future plans for multiple connections, dynamic services

## 🎯 Next Steps

### Immediate (This Week)
1. [ ] Create `websocket.py` with basic command handlers
2. [ ] Update bridge class to use WebSocket
3. [ ] Implement hash synchronization logic
4. [ ] Test basic communication

### Short Term (Next Week)
1. [ ] Complete Python implementation
2. [ ] Add proper error handling
3. [ ] Add authentication
4. [ ] Comprehensive testing

### Medium Term (Following Weeks)
1. [ ] Update TypeScript libraries
2. [ ] Maintain backward compatibility
3. [ ] Update documentation
4. [ ] Release new versions

## 📞 Communication Notes

### Team Coordination
- **Python First**: Focus on Python implementation before TypeScript
- **Reference Libraries**: TypeScript libraries in `src/` are for reference only
- **Documentation**: Keep this document updated with progress
- **Testing**: Test thoroughly before moving to TypeScript

### Decision Points
- Authentication method selection
- Backward compatibility strategy
- Error handling approach
- Testing methodology
- Hash synchronization strategy

---

**Last Updated**: [Current Date]
**Status**: Planning Phase - Workflow Documented
**Next Review**: After Python WebSocket implementation
