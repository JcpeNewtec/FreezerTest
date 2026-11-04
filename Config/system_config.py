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

# Automatic camera recovery for long unattended tests.
# Some V4L2/GStreamer failures (for example buffer-pool/CMA allocation
# failures) leave the camera capture path unusable until the camera is
# power-cycled. When one of those known errors is detected, the long-test
# runner can automatically reboot only the camera and continue.
CAMERA_AUTO_RECOVERY_ENABLED = True
CAMERA_AUTO_RECOVERY_MAX_PER_TEST = 3
CAMERA_AUTO_RECOVERY_POWER_OFF_WAIT_S = 15.0


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

# Continuous camera keepalive stream during long tests.
# This keeps the camera/TEC/video pipeline active between sweeps. Normal image
# capture uses the same V4L2 device, so the long-test logic stops this stream
# before each sweep capture and restarts it afterward.
CAMERA_KEEPALIVE_STREAM_ENABLED = False
CAMERA_KEEPALIVE_STREAM_DEVICE = REMOTE_CAMERA_TEMPERATURE_STREAM_DEVICE
CAMERA_KEEPALIVE_STREAM_COUNT = 100000000
CAMERA_KEEPALIVE_STREAM_STARTUP_WAIT_S = 2.0
CAMERA_KEEPALIVE_STREAM_PID_FILE = "/tmp/freezertest_keepalive_stream.pid"
CAMERA_KEEPALIVE_STREAM_LOG_FILE = "/tmp/freezertest_keepalive_stream.log"
CAMERA_KEEPALIVE_KILL_STALE_ON_START = True
CAMERA_KEEPALIVE_STOP_BEFORE_SWEEP = True
CAMERA_KEEPALIVE_RESTART_AFTER_SWEEP = True

# Keepalive start robustness after a cold camera boot. The fixed camera boot
# delay is followed by an actual V4L2 readiness check and several stream-start
# attempts. Failed events include the remote stream log and device diagnostics.
CAMERA_KEEPALIVE_DEVICE_READY_TIMEOUT_S = 180.0
CAMERA_KEEPALIVE_DEVICE_READY_POLL_S = 5.0
CAMERA_KEEPALIVE_START_MAX_ATTEMPTS = 6
CAMERA_KEEPALIVE_START_RETRY_DELAY_S = 10.0
CAMERA_KEEPALIVE_LOG_TAIL_LINES = 60
# Give the kernel/driver a little time to release V4L2 mmap/DMA buffers after
# the keepalive process stops before a still-capture pipeline is opened.
CAMERA_CAPTURE_DEVICE_RELEASE_WAIT_S = 2.0

REMOTE_DATA_ROOT = "/root/scripts/data"


TEST_NAME = "freezer_test"
TEST_DURATION_HOURS = 1.0

# Measurement end condition.
#
# "time": preserve the existing behavior and end after TEST_DURATION_HOURS.
# "temperature": end when TEST_END_SENSOR_NAME reaches TEST_END_TARGET_C.
#                TEST_END_SAFETY_TIMEOUT_HOURS remains a hard maximum runtime
#                so a missing/broken probe cannot leave a test running forever.
TEST_END_MODE = "time"
TEST_END_SENSOR_NAME = "probe_2"
TEST_END_TARGET_C = 40.0
# "above" means end when temperature >= target.
# "below" means end when temperature <= target.
TEST_END_DIRECTION = "above"
TEST_END_SAFETY_TIMEOUT_HOURS = 14.0
# Require several new logger records at/through the target before ending.
# This prevents one bad temperature sample from ending an unattended test.
TEST_END_REQUIRED_CONSECUTIVE_READS = 3
# When a temperature target or safety timeout is reached between normal sweeps,
# take one immediate final sweep so the analysis contains an endpoint image set.
TEST_END_FINAL_SWEEP_ENABLED = True

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




# MCC recovery limits (attempt counts, not elapsed-time guarantees).
MCC_AUTO_RECONNECT_ENABLED = True
MCC_RECONNECT_MAX_ATTEMPTS = 10
MCC_RECONNECT_DELAY_S = 2.0
MCC_COMMAND_RETRY_COUNT = 2
MCC_SAFE_SHUTDOWN_RECONNECT_ATTEMPTS = 30
MCC_SAFE_SHUTDOWN_RETRY_DELAY_S = 2.0

try:
    from Config.local_config import *
except ImportError:
    pass
