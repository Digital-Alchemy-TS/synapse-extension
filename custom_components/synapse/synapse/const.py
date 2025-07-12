APP_OFFLINE_DELAY=30
DOMAIN = "synapse"
EVENT_NAMESPACE = "digital_alchemy"
QUERY_TIMEOUT=0.1
RETRIES=3
RETRY_DELAY=5

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

    # Validation errors
    INVALID_UNIQUE_ID = "invalid_unique_id"
    INVALID_APP_METADATA = "invalid_app_metadata"
    INVALID_HASH = "invalid_hash"

    # System errors
    INTERNAL_ERROR = "internal_error"
    TIMEOUT_ERROR = "timeout_error"
    CONNECTION_ERROR = "connection_error"

    # Connection management errors
    CONNECTION_TIMEOUT = "connection_timeout"
    RECONNECTION_FAILED = "reconnection_failed"
    CONNECTION_LOST = "connection_lost"
    INVALID_MESSAGE_FORMAT = "invalid_message_format"
    MESSAGE_TOO_LARGE = "message_too_large"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"

    # Configuration errors
    CONFIGURATION_INVALID = "configuration_invalid"
    CONFIGURATION_TOO_LARGE = "configuration_too_large"
    ENTITY_VALIDATION_FAILED = "entity_validation_failed"
    DEVICE_VALIDATION_FAILED = "device_validation_failed"

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

# #MARK: Entities
PLATFORMS: list[str] = [
    # Working -
    #
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
    # High priority wishlist -
    #
    # "image",
    # "media_player",
    # "notify",
    # "remote",
    # "todo_list",
    # "update",
    #
    # Low priority wishlist -
    #
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

class SynapseBaseEntity:
    """Common properties to all synapse entities"""
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

class SynapseSensorDefinition(SynapseBaseEntity):
    capability_attributes: int
    last_reset: str
    native_unit_of_measurement: str
    options: list[str]
    state_class: str
    suggested_display_precision: int
    unit_of_measurement: str

class SynapseAlarmControlPanelDefinition(SynapseBaseEntity):
    changed_by: str
    code_arm_required: bool
    code_format: str

class SynapseNumberDefinition(SynapseBaseEntity):
    max_value: float
    min_value: float
    mode: str
    state: float
    step: float

class SynapseButtonDefinition(SynapseBaseEntity):
    pass
class SynapseBinarySensorDefinition(SynapseBaseEntity):
    pass
class SynapseClimateDefinition(SynapseBaseEntity):
    pass
class SynapseCoverDefinition(SynapseBaseEntity):
    pass
class SynapseDateDefinition(SynapseBaseEntity):
    pass
class SynapseDateTimeDefinition(SynapseBaseEntity):
    pass
class SynapseFanDefinition(SynapseBaseEntity):
    pass
class SynapseHumidifierDefinition(SynapseBaseEntity):
    pass
class SynapseImageDefinition(SynapseBaseEntity):
    pass
class SynapseLawnMowerDefinition(SynapseBaseEntity):
    pass
class SynapseLightDefinition(SynapseBaseEntity):
    pass
class SynapseLockDefinition(SynapseBaseEntity):
    pass
class SynapseMediaPlayerDefinition(SynapseBaseEntity):
    pass
class SynapseNotifyDefinition(SynapseBaseEntity):
    pass
class SynapseRemoteDefinition(SynapseBaseEntity):
    pass
class SynapseSceneDefinition(SynapseBaseEntity):
    pass
class SynapseSelectDefinition(SynapseBaseEntity):
    pass
class SynapseSirenDefinition(SynapseBaseEntity):
    pass
class SynapseSwitchDefinition(SynapseBaseEntity):
    pass
class SynapseTextDefinition(SynapseBaseEntity):
    pass
class SynapseTimeDefinition(SynapseBaseEntity):
    pass
class SynapseTodoListDefinition(SynapseBaseEntity):
    pass
class SynapseUpdateDefinition(SynapseBaseEntity):
    pass
class SynapseVacuumDefinition(SynapseBaseEntity):
    pass
class SynapseValveDefinition(SynapseBaseEntity):
    pass
class SynapseWaterHeaterDefinition(SynapseBaseEntity):
    pass
class SynapseCameraDefinition(SynapseBaseEntity):
    pass
