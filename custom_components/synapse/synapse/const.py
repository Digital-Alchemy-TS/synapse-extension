"""
Constants and type definitions for the Synapse integration.

This module contains all configuration constants, error codes, and type
definitions used throughout the Synapse custom component.
"""

# Application timeout settings
APP_OFFLINE_DELAY = 30  # seconds - delay before marking app as offline
DOMAIN = "synapse"  # Home Assistant domain name
EVENT_NAMESPACE = "digital_alchemy"  # Event bus namespace for app communication
QUERY_TIMEOUT = 0.1  # seconds - timeout for discovery queries
RETRIES = 3  # number of retry attempts for failed operations
RETRY_DELAY = 5  # seconds - base delay between retry attempts

# Connection timeout settings
CONNECTION_TIMEOUT = 60  # seconds - timeout for initial connection
HEARTBEAT_TIMEOUT = 30   # seconds - timeout for heartbeat (same as APP_OFFLINE_DELAY)
RECONNECT_DELAY = 5      # seconds - base delay for reconnection attempts
MAX_RECONNECT_ATTEMPTS = 10  # maximum number of reconnection attempts

# WebSocket Error Codes
class SynapseErrorCodes:
    """Error codes for Synapse WebSocket communication."""

    # Registration errors
    ALREADY_CONNECTED = "already_connected"
    NOT_REGISTERED = "not_registered"
    BRIDGE_NOT_FOUND = "bridge_not_found"

    # Communication errors
    REGISTRATION_FAILED = "registration_failed"
    HEARTBEAT_FAILED = "heartbeat_failed"
    UPDATE_FAILED = "update_failed"
    CONFIGURATION_UPDATE_FAILED = "configuration_update_failed"
    GOING_OFFLINE_FAILED = "going_offline_failed"

    # System errors
    INTERNAL_ERROR = "internal_error"

    # Connection management errors
    CONNECTION_TIMEOUT = "connection_timeout"
    INVALID_MESSAGE_FORMAT = "invalid_message_format"
    MESSAGE_TOO_LARGE = "message_too_large"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"

    # Configuration errors
    CONFIGURATION_TOO_LARGE = "configuration_too_large"
    ENTITY_VALIDATION_FAILED = "entity_validation_failed"

class SynapseMetadata:
    """Entity device information for device registry."""
    configuration_url: str | None
    default_manufacturer: str
    default_model: str
    default_name: str
    hw_version: str | None
    manufacturer: str | None
    model: str | None
    name: str | None
    serial_number: str | None
    suggested_area: str | None
    sw_version: str | None
    unique_id: str | None

class SynapseApplication:
    """Description of application state"""
    app: str
    boot: str
    device: SynapseMetadata
    hash: str
    hostname: str
    name: str
    secondary_devices: list[SynapseMetadata]
    sensor: list[object]
    title: str
    unique_id: str
    username: str
    version: str

# Supported entity platforms
PLATFORMS: list[str] = [
    # Currently implemented platforms
    "binary_sensor",
    "button",
    "date",
    "datetime",
    "lock",
    "number",
    "scene",
    "select",
    "sensor",
    "switch",
    "text",
    "time",
    #
    # High priority wishlist - planned for future implementation
    #
    # "image",
    # "media_player",
    # "notify",
    # "remote",
    # "todo_list",
    # "update",
    #
    # Low priority wishlist - potential future additions
    #
    # "alarm_control_panel",
    # "camera",
    # "climate",
    # "cover",
    # "fan",
    # "humidifier",
    # "lawn_mower",
    # "light",
    # "siren",
    # "vacuum",
    # "valve",
    # "water_heater",
]

# Entity domains that are currently supported and can be configured dynamically
# This includes all domains that can be sent in app metadata during registration
ENTITY_DOMAINS: list[str] = [
    "sensor",
    "switch",
    "binary_sensor",
    "button",
    "climate",
    "lock",
    "number",
    "select",
    "text",
    "date",
    "time",
    "datetime",
    "scene",
]

# Note: Generated entities are now tracked explicitly in the bridge class
# No patterns needed - entities are registered when created

class SynapseBaseEntityData:
    """Common properties shared by all Synapse entities.

    This base class defines the standard properties that all entity types
    inherit from, providing a consistent interface for entity configuration.
    """
    attributes: object
    device_class: str | None = None
    entity_category: str | None = None
    icon: str | None = None
    name: str
    state: str | int | None = None
    suggested_object_id: str
    supported_features: int
    translation_key: str | None = None
    unique_id: str

class SynapseSensorDefinition(SynapseBaseEntityData):
    """Type definition for sensor entities with sensor-specific properties."""
    capability_attributes: int
    last_reset: str
    native_unit_of_measurement: str
    options: list[str]
    state_class: str
    suggested_display_precision: int
    unit_of_measurement: str

class SynapseAlarmControlPanelDefinition(SynapseBaseEntityData):
    """Type definition for alarm control panel entities."""
    changed_by: str
    code_arm_required: bool
    code_format: str

class SynapseNumberDefinition(SynapseBaseEntityData):
    """Type definition for number entities with numeric input properties."""
    max_value: float
    min_value: float
    mode: str
    state: float
    step: float

class SynapseButtonDefinition(SynapseBaseEntityData):
    """Type definition for button entities."""
    pass

class SynapseBinarySensorDefinition(SynapseBaseEntityData):
    """Type definition for binary sensor entities."""
    pass

class SynapseClimateDefinition(SynapseBaseEntityData):
    """Type definition for climate entities."""
    pass

class SynapseCoverDefinition(SynapseBaseEntityData):
    """Type definition for cover entities."""
    pass

class SynapseDateDefinition(SynapseBaseEntityData):
    """Type definition for date entities."""
    pass

class SynapseDateTimeDefinition(SynapseBaseEntityData):
    """Type definition for datetime entities."""
    pass

class SynapseFanDefinition(SynapseBaseEntityData):
    """Type definition for fan entities."""
    pass

class SynapseHumidifierDefinition(SynapseBaseEntityData):
    """Type definition for humidifier entities."""
    pass

class SynapseImageDefinition(SynapseBaseEntityData):
    """Type definition for image entities."""
    pass

class SynapseLawnMowerDefinition(SynapseBaseEntityData):
    """Type definition for lawn mower entities."""
    pass

class SynapseLightDefinition(SynapseBaseEntityData):
    """Type definition for light entities."""
    pass

class SynapseLockDefinition(SynapseBaseEntityData):
    """Type definition for lock entities."""
    pass

class SynapseMediaPlayerDefinition(SynapseBaseEntityData):
    """Type definition for media player entities."""
    pass

class SynapseNotifyDefinition(SynapseBaseEntityData):
    """Type definition for notify entities."""
    pass

class SynapseRemoteDefinition(SynapseBaseEntityData):
    """Type definition for remote entities."""
    pass

class SynapseSceneDefinition(SynapseBaseEntityData):
    """Type definition for scene entities."""
    pass

class SynapseSelectDefinition(SynapseBaseEntityData):
    """Type definition for select entities."""
    pass

class SynapseSirenDefinition(SynapseBaseEntityData):
    """Type definition for siren entities."""
    pass

class SynapseSwitchDefinition(SynapseBaseEntityData):
    """Type definition for switch entities."""
    pass

class SynapseTextDefinition(SynapseBaseEntityData):
    """Type definition for text entities."""
    pass

class SynapseTimeDefinition(SynapseBaseEntityData):
    """Type definition for time entities."""
    pass

class SynapseTodoListDefinition(SynapseBaseEntityData):
    """Type definition for todo list entities."""
    pass

class SynapseUpdateDefinition(SynapseBaseEntityData):
    """Type definition for update entities."""
    pass

class SynapseVacuumDefinition(SynapseBaseEntityData):
    """Type definition for vacuum entities."""
    pass

class SynapseValveDefinition(SynapseBaseEntityData):
    """Type definition for valve entities."""
    pass

class SynapseWaterHeaterDefinition(SynapseBaseEntityData):
    """Type definition for water heater entities."""
    pass

class SynapseCameraDefinition(SynapseBaseEntityData):
    """Type definition for camera entities."""
    pass
