# WebSocket API Reference

## Overview

The Synapse Extension uses Home Assistant's WebSocket API for secure, bidirectional communication between NodeJS applications and Home Assistant.

## Why WebSocket API?

- **Bidirectional Communication**: Apps can send commands AND receive responses
- **Better Performance**: Direct communication without event bus overhead
- **Standard Pattern**: Uses Home Assistant's standard WebSocket API
- **Scalable**: Handles multiple connections efficiently
- **Security**: Rate limiting, validation, and connection management

## Supported Commands

### App → Home Assistant

| Command | Purpose | Rate Limit | Size Limit |
|---------|---------|------------|------------|
| `synapse/register` | App registration | 10/min | 50KB |
| `synapse/heartbeat` | Health monitoring | 120/min | 1KB |
| `synapse/update_entity` | Entity updates | 300/min | 10KB |
| `synapse/update_configuration` | Full config sync | 5/min | 1MB |
| `synapse/going_offline` | Graceful shutdown | 10/min | 1KB |
| `synapse/get_health` | Health check | 120/min | 1KB |

### Home Assistant → App

| Event Type | Purpose | Trigger |
|------------|---------|---------|
| `synapse/request_configuration` | Request config sync | Hash drift detected |
| `synapse/connection_lost` | Connection lost | Timeout or failure |
| `synapse/reconnection_failed` | Reconnection failed | Max attempts reached |

## Security Features

### Rate Limiting
- **Per-command limits**: Different limits for different command types
- **Sliding window**: 60-second window for rate limit tracking
- **Automatic cleanup**: Old tracking entries are automatically removed
- **Configurable limits**: Easy to adjust limits based on requirements

### Message Validation
- **Size limits**: Prevents DoS attacks through oversized messages
- **Schema validation**: Ensures message format compliance
- **Type validation**: Validates field types and values
- **Domain-specific validation**: Entity-specific validation rules

### Connection Management
- **Timeout handling**: Automatic cleanup of stale connections
- **Reconnection logic**: Exponential backoff for failed connections
- **Health monitoring**: Real-time connection health tracking
- **Graceful shutdown**: Proper cleanup on app shutdown

## Error Handling

### Error Response Format
All error responses include:
- `error_code`: Machine-readable error identifier
- `message`: Human-readable error description
- `unique_id`: App identifier for correlation

### Common Error Codes
- `rate_limit_exceeded`: Too many requests
- `message_too_large`: Message exceeds size limit
- `invalid_message_format`: Invalid message structure
- `bridge_not_found`: No bridge found (usually temporary)
- `entity_validation_failed`: Entity data validation failed

## Connection Lifecycle

1. **Initial Connection**: App connects to WebSocket API
2. **Registration**: App sends registration with metadata
3. **Validation**: System validates app registration and connection
4. **Hash Sync**: Compare configuration hashes and sync if needed
5. **Runtime**: App sends heartbeats and entity updates
6. **Shutdown**: App sends going offline message or timeout occurs

## Health Monitoring

Use the `synapse/get_health` command to monitor connection health. Response includes:
- Connection status and uptime
- Reconnection attempt count
- Online status and last heartbeat time

## Best Practices

### For App Developers
1. Handle all error codes with appropriate recovery strategies
2. Respect rate limits and implement backoff
3. Validate data before sending
4. Use health checks to monitor connection status
5. Always send going offline message before disconnecting
6. Implement exponential backoff for transient errors

### For Integration Developers
1. Use predefined error codes from `SynapseErrorCodes`
2. Log validation failures with context
3. Handle unexpected errors gracefully
4. Monitor connection health and implement recovery
5. Don't expose sensitive information in error messages

## Performance Considerations

### Connection Management
- **Connection pooling**: Efficient handling of multiple connections
- **Timeout optimization**: Appropriate timeout values for different scenarios
- **Resource cleanup**: Proper cleanup of timers and connections
- **Memory management**: Efficient tracking of connection state

### Message Processing
- **Size validation**: Early size validation to prevent processing large messages
- **Schema validation**: Fast schema validation using voluptuous
- **Rate limiting**: Efficient rate limit tracking with automatic cleanup
- **Error handling**: Fast error response without unnecessary processing

## Migration from Event Bus

### Benefits
1. **Better performance**: Direct WebSocket communication without event bus overhead
2. **Improved reliability**: Proper error handling and recovery mechanisms
3. **Enhanced security**: Rate limiting, validation, and connection management
4. **Standard compliance**: Uses Home Assistant's standard WebSocket API
5. **Better debugging**: Comprehensive error codes and health monitoring

### Migration Steps
1. Update app code to use WebSocket commands
2. Implement proper error handling for all error codes
3. Add health monitoring and checks
4. Test all scenarios including error conditions
5. Monitor performance improvements

---

**Status**: Implementation Complete with Enhanced Security & Error Handling
