# Communication Rework - Working Document

## 🎯 Project Overview

**Goal**: Replace the current event bus abuse with proper WebSocket API communication between Home Assistant and external Synapse applications.

**Current Status**: Heartbeat implementation complete - hash drift detection and configuration resync logic implemented.

**Timeline**:
- Phase 1: Python rework (current)
- Phase 2: TypeScript library updates (future)

## 📋 Current State Analysis

### Python Side (Home Assistant Integration)
**Location**: `custom_components/synapse/`

#### Key Files:
- `__init__.py` - Main integration setup ✅ Updated
- `synapse/bridge.py` - Core communication logic ✅ Gutted & refactored
- `synapse/base_entity.py` - Base entity class (4.3KB, 133 lines)
- `synapse/const.py` - Constants and types ✅ Updated with error codes
- `synapse/helpers.py` - Utility functions (478B, 17 lines)
- `websocket.py` - WebSocket handlers ✅ Updated with error codes
- Entity files: `sensor.py`, `switch.py`, `climate.py`, etc.

#### Current Communication Pattern:
- ✅ **REMOVED**: Event bus communication (`hass.bus.async_fire()`, `hass.bus.async_listen()`)
- ✅ **ADDED**: WebSocket API handlers for all commands
- ✅ **ADDED**: Bridge methods for handling WebSocket communication
- ✅ **ADDED**: Connection tracking and management
- ✅ **ADDED**: Validation logic with error codes
- ✅ **ADDED**: Heartbeat monitoring with hash drift detection

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
3. **Extension validates unique_id** against existing connections (error if already in use) ✅ IMPLEMENTED
4. **Extension checks unique_id** against registered apps list ✅ IMPLEMENTED
5. **If not registered**: Do not continue (see enhancement requests for future discovery plans) ✅ IMPLEMENTED
6. **If registered**: Send acknowledgment with last known app hash ✅ IMPLEMENTED
7. **TS side compares hashes** using `storage.hash()` function
8. **If hash mismatch**: Transmit full entity/device configuration
9. **Configuration becomes source of truth** for HA entity/device management
10. **App enters "runtime" mode**

### Runtime Operation
- **Heartbeat every 30 seconds** with current hash ✅ IMPLEMENTED
- **Hash drift detection** triggers configuration resync request ✅ IMPLEMENTED
- **Entity patches** for state changes, icons, enable/disable, related entities
- **No hash changes** for runtime patches

## 🔄 Planned Changes

### Phase 1: Python WebSocket Implementation

#### 1.1 Create WebSocket Command Handlers ✅ COMPLETE
**File**: `custom_components/synapse/websocket.py` ✅ CREATED

**Commands implemented**:
- ✅ `synapse/register` - App registration with metadata
- ✅ `synapse/heartbeat` - Health monitoring with hash
- ✅ `synapse/update_entity` - Runtime entity patches
- ✅ `synapse/update_configuration` - Full config sync

#### 1.2 Update Bridge Class ✅ COMPLETE
**File**: `custom_components/synapse/synapse/bridge.py` ✅ REFACTORED

**Changes completed**:
- ✅ Removed event bus usage
- ✅ Added WebSocket connection tracking
- ✅ Implemented basic handler methods
- ✅ Added connection management methods
- ✅ Gutted old communication code
- ✅ **ADDED**: Validation logic with error codes
- ✅ **ADDED**: Registration validation methods
- ✅ **ADDED**: Heartbeat monitoring with timeout handling
- ✅ **ADDED**: Hash drift detection and configuration resync logic

#### 1.3 Update Integration Setup ✅ COMPLETE
**File**: `custom_components/synapse/__init__.py` ✅ UPDATED

**Changes completed**:
- ✅ Register WebSocket commands
- ✅ Added `async_setup()` function
- ✅ WebSocket handlers registered on integration load

#### 1.4 Error Codes & Validation ✅ COMPLETE
**File**: `custom_components/synapse/synapse/const.py` ✅ UPDATED

**Changes completed**:
- ✅ Added `SynapseErrorCodes` enum
- ✅ Defined all error codes for WebSocket communication
- ✅ Comprehensive error code documentation

#### 1.5 Heartbeat System ✅ COMPLETE
**File**: `custom_components/synapse/synapse/bridge.py` ✅ UPDATED

**Changes completed**:
- ✅ Heartbeat timer management (30-second timeout)
- ✅ Hash drift detection logic
- ✅ Configuration resync requests
- ✅ Connection health monitoring
- ✅ Online/offline state tracking

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
- [x] **WebSocket handlers created** (`websocket.py`)
- [x] **Bridge class gutted and refactored** (`bridge.py`)
- [x] **Integration setup updated** (`__init__.py`)
- [x] **Basic "hello world" reception implemented**
- [x] **Validation logic implemented** with error codes
- [x] **Error code system created** (`SynapseErrorCodes`)
- [x] **Registration validation complete** (unique_id checks, app registration checks)
- [x] **Heartbeat system implemented** (30-second monitoring, hash drift detection)
- [x] **Configuration resync logic** (hash drift triggers config update requests)

#### 🔄 In Progress
- [ ] Implement hash storage and comparison logic
- [ ] Implement configuration sync logic

#### ⏳ Pending
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
6. **Error Handling**: Test all error codes and validation scenarios
7. **Heartbeat Testing**: Test heartbeat timing and hash drift detection

### TypeScript Testing
1. **Unit Tests**: Test WebSocket client methods
2. **Integration Tests**: Test with Python implementation
3. **Mock Testing**: Use existing mock implementations
4. **Hash Testing**: Test hash generation and comparison
5. **Real-world Testing**: Test with actual applications

## 📝 Technical Decisions

### WebSocket Command Structure ✅ IMPLEMENTED
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

### Error Code System ✅ IMPLEMENTED
```python
class SynapseErrorCodes:
    ALREADY_CONNECTED = "already_connected"
    NOT_REGISTERED = "not_registered"
    BRIDGE_NOT_FOUND = "bridge_not_found"
    # ... additional error codes
```

### Heartbeat System ✅ IMPLEMENTED
```python
# Heartbeat response with hash drift detection
{
  "success": True,
  "heartbeat_received": True,
  "hash_drift_detected": True,
  "request_configuration": True,
  "message": "Hash drift detected - configuration update requested",
  "last_known_hash": "abc123...",
  "current_hash": "def456..."
}
```

### Hash Synchronization
- **Hash Generation**: Based on complete app configuration
- **Hash Comparison**: Used to detect configuration changes ✅ IMPLEMENTED
- **Resync Trigger**: When hash drift is detected ✅ IMPLEMENTED
- **Runtime Patches**: Don't change hash, only for state/config updates

### Authentication Strategy
- **Option 1**: API keys in config
- **Option 2**: Long-lived access tokens
- **Option 3**: App-specific tokens
- **Decision**: TBD based on security requirements

### Error Handling ✅ IMPLEMENTED
- ✅ Proper error codes and messages
- ✅ Consistent error response format
- ✅ Comprehensive error documentation
- ✅ Validation logic with clear error states

## 🚨 Known Issues

### Current Problems
1. **Event Bus Abuse**: ✅ REMOVED - No longer using event bus for external communication
2. **No Authentication**: No proper security for external connections
3. **Performance**: ✅ IMPROVED - Direct WebSocket communication
4. **Scalability**: ✅ IMPROVED - Better connection management

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
- `notes/websocket-error-codes.md` - Error codes and validation documentation ✅ NEW

### TypeScript Libraries
- `src/synapse.module.mts` - Main module reference
- `src/services/discovery.service.mts` - Discovery service reference
- `src/services/` - Service implementations reference

### Enhancement Requests
- `notes/enhancement-requests.md` - Future plans for multiple connections, dynamic services

## 🎯 Next Steps

### Immediate (This Week)
1. [x] Create `websocket.py` with basic command handlers ✅
2. [x] Update bridge class to use WebSocket ✅
3. [x] Implement basic "hello world" reception ✅
4. [x] Implement validation logic with error codes ✅
5. [x] Implement heartbeat system with hash drift detection ✅
6. [ ] Test basic communication

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
- Error handling approach ✅ DECIDED
- Testing methodology
- Hash synchronization strategy ✅ IMPLEMENTED

---

**Last Updated**: [Current Date]
**Status**: Heartbeat System Complete - Hash Drift Detection Implemented
**Next Review**: After configuration sync implementation
