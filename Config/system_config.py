TIC_SERIAL = None

FILTER_POSITIONS = {
    1: -57,
    2: -257,
    3: -457,
    4: -657,
}

FILTERWHEEL_STEP_MODE = 8
FILTERWHEEL_CURRENT_LIMIT_MA = 1500
FILTERWHEEL_MAX_SPEED = 4000000
FILTERWHEEL_STARTING_SPEED = 0
FILTERWHEEL_MAX_ACCEL = 40000
FILTERWHEEL_MAX_DECEL = 40000
FILTERWHEEL_POSITION_TOLERANCE = 5
FILTERWHEEL_SETTLE_TIME_S = 0.2
FILTERWHEEL_MOVE_TIMEOUT_S = 10.0

# Reduce long-run stepper heating.
# True means the Tic is energized only while actively moving/homing,
# then de-energized while the wheel is idle or images are captured.
FILTERWHEEL_DEENERGIZE_AFTER_MOVE = True

HALL_DIO_BIT = 1
HALL_ACTIVE_STATE = 0

FILTERWHEEL_HOME_ENABLED = True
FILTERWHEEL_HOME_SEARCH_DIRECTION = -1
FILTERWHEEL_HOME_FAST_STEP = 50
FILTERWHEEL_HOME_SLOW_STEP = 1
FILTERWHEEL_HOME_MAX_STEPS = 3000

# Camera power relay control through MCC DIO
CAMERA_POWER_CONTROL_ENABLED = True
CAMERA_POWER_DIO_BIT = 2
CAMERA_POWER_ACTIVE_STATE = 1
CAMERA_POWER_BOOT_WAIT_S = 45.0
CAMERA_POWER_OFF_AT_TEST_END = True

# Freezer contactor control through MCC DIO
FREEZER_CONTROL_ENABLED = True
FREEZER_DIO_BIT = 3
FREEZER_ACTIVE_STATE = 1


# Freezer contactor control through MCC DIO
FREEZER_CONTROL_ENABLED = True
FREEZER_DIO_BIT = 3
FREEZER_ACTIVE_STATE = 1

# Automatic pre-cool before each test
PRECOOL_BEFORE_TEST_ENABLED = True
PRECOOL_SENSOR_NAME = "probe_2"
PRECOOL_TARGET_C = -5.0
PRECOOL_TIMEOUT_HOURS = 4.0
PRECOOL_POLL_INTERVAL_S = 5.0
PRECOOL_SETTLE_AFTER_FREEZER_OFF_S = 60.0

# Repeated unattended tests
REPEAT_TEST_COUNT = 1
REPEAT_DELAY_BETWEEN_TESTS_S = 0
REPEAT_CONTINUE_AFTER_FAILURE = False
REPEAT_STOP_FILE_NAME = "STOP_REPEAT"

# Compressor protection for manual/test scripts
FREEZER_MIN_OFF_TIME_S = 10 * 60
FREEZER_TEST_ON_TIME_S = 10 * 60



CAMERA_IP = "10.100.10.100"
CAMERA_USER = "root"
REMOTE_CAPTURE_SCRIPT = "/root/scripts/capture_remote.py"
REMOTE_CAMERA_TEMPERATURE_SCRIPT = "/root/scripts/read_camera_temperatures.py"
REMOTE_CAMERA_TEMPERATURE_DEVICE = "/dev/video4"

# Some Qtec camera firmware/driver versions only update the V4L2
# sensor_temperature control while the camera is actively streaming.
# The camera-side temperature script therefore starts a temporary stream,
# keeps that stream active while sensor_temperature is read, then stops it.
REMOTE_CAMERA_TEMPERATURE_STREAM_REFRESH_ENABLED = True
REMOTE_CAMERA_TEMPERATURE_STREAM_DEVICE = REMOTE_CAMERA_TEMPERATURE_DEVICE
REMOTE_CAMERA_TEMPERATURE_STREAM_COUNT = 300
REMOTE_CAMERA_TEMPERATURE_STREAM_STARTUP_WAIT_S = 1.0

CAMERA_INTERNAL_TEMPERATURE_ENABLED = True
REMOTE_DATA_ROOT = "/root/scripts/data"


TEST_NAME = "freezer_test"
TEST_DURATION_HOURS = 1.0
SWEEP_INTERVAL_SECONDS = 180
MAX_SWEEPS = 25
RETRY_DELAY_SECONDS = 30
MAX_CONSECUTIVE_FAILURES = 3
MINIMUM_FREE_GB = 5.0

# Default exposure if a filter has no specific value
DEFAULT_EXPOSURE_TIME_ABSOLUTE = 20000

# Per-filter exposure settings.
FILTER_EXPOSURE_TIME_ABSOLUTE = {
    1: 3000,
    2: 15000,
    3: 8000,
    4: 15000,
}

LAMP_WARMUP_S = 2.0

# Test metadata
CAMERA_ID = "unknown_camera"
TEST_OPERATOR = "JCPE"
TEST_NOTES = ""




try:
    from Config.local_config import *
except ImportError:
    pass
