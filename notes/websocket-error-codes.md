# WebSocket Error Codes & Validation

## Overview

This document explains the error handling system for the Synapse WebSocket communication. The system provides specific error codes and automatic recovery mechanisms.

## Error Code Reference

### Registration Errors
- `already_connected` - Unique ID is already connected
- `not_registered` - App is not registered in config
- `bridge_not_found` - No bridge found for unique_id (usually temporary)

### Communication Errors
- `registration_failed` - Registration process failed
- `heartbeat_failed` - Heartbeat processing failed
- `update_failed` - Entity update failed
- `configuration_update_failed` - Configuration update failed
- `going_offline_failed` - Going offline process failed

### Connection Management Errors
- `connection_timeout` - Connection timeout (60s)
- `reconnection_failed` - Reconnection failed after max attempts
- `connection_lost` - WebSocket connection lost
- `invalid_message_format` - Invalid message format
- `message_too_large` - Message exceeds size limits
- `rate_limit_exceeded` - Rate limit exceeded

### Configuration Errors
- `configuration_invalid` - Invalid configuration data
- `configuration_too_large` - Configuration exceeds 1MB limit
- `entity_validation_failed` - Entity validation failed
- `device_validation_failed` - Device validation failed

## Error Recovery Strategies

### For App Developers

| Error Code | Recovery Strategy | Retry Logic |
|------------|-------------------|-------------|
| `bridge_not_found` | Wait and retry | Exponential backoff (2s, 4s, 8s...) |
| `rate_limit_exceeded` | Wait and retry | Exponential backoff (1s, 2s, 4s...) |
| `message_too_large` | Reduce message size | Immediate retry with smaller message |
| `entity_validation_failed` | Fix validation errors | Immediate retry after fixing errors |
| `not_registered` | Configure app | No retry - configuration error |
| `connection_timeout` | Reconnect | Exponential backoff |
| `reconnection_failed` | Manual intervention | No automatic retry |

### For End Users
- **No action required** - apps should handle most errors automatically
- **If persistent**: Check Home Assistant logs for detailed error information
- **If frequent**: Consider adjusting app configuration or timing
- **For rate limits**: Reduce request frequency or contact app developer

## Security & Rate Limiting

### Rate Limiting Configuration
- **Registration**: 10 requests per minute
- **Heartbeat**: 120 requests per minute (2 per second)
- **Entity Updates**: 300 requests per minute (5 per second)
- **Configuration Updates**: 5 requests per minute

### Message Size Limits
- **Registration**: 50KB
- **Entity Updates**: 10KB
- **Configuration Updates**: 1MB

### Connection Timeout Settings
- **Connection Timeout**: 60 seconds for initial registration
- **Heartbeat Timeout**: 30 seconds for heartbeat monitoring
- **Reconnect Delay**: 5 seconds base delay
- **Max Reconnect Attempts**: 10 attempts

## Health Monitoring

Use the `synapse/get_health` command to monitor connection health. Response includes:
- Connection status and uptime
- Reconnection attempt count
- Online status and last heartbeat time

## Best Practices

### For App Developers
1. Handle all error codes with appropriate recovery strategies
2. Implement exponential backoff for transient errors
3. Respect rate limits and implement backoff
4. Validate data before sending
5. Use health checks to monitor connection status
6. Always send going offline message before disconnecting

### For Integration Developers
1. Use predefined error codes from `SynapseErrorCodes`
2. Log validation failures with context
3. Handle unexpected errors gracefully
4. Don't expose sensitive information in error messages
5. Monitor connection health and implement recovery

---

**Status**: Implementation Complete with Enhanced Error Handling
