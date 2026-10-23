# Software and configuration

Status: first version, based on static inspection of the supplied files on 23 October 2026. No hardware-control program was executed to build this documentation. Values below describe the copied source snapshot, not a guarantee of what is deployed on the test PC or camera.

The 33 shared Python/shell files in the supplied local copy were verified against public repository commit `df4ccebbbd0f41e32f5ae415e967728e5845d56b` dated 12 October 2026 and matched byte for byte. `Config/local_config.py` is an additional local file, so its effective settings must be retained when reproducing this copy's behavior. See [source provenance and maintenance](10-sources-and-maintenance.md) for verification details.

## Software layers

The host PC owns sequencing, MCC I/O, wheel movement, temperature logging, data transfer, and analysis. The camera computer owns the V4L2 video device, image-capture pipeline, and internal temperature queries. Camera-side Python modules are deployed separately; editing the local copy does not update the running camera. [Sweep orchestration](../Scripts/run_single_sweep_remote.py#L201), [camera deployment](../Scripts/deploy_camera_scripts.sh#L7).

| File or group | Responsibility |
|---|---|
| `Config/system_config.py` | Base host configuration: motion, DIO, network endpoints, control features, test timing, recovery and metadata; imports local overrides at the end. |
| `Config/local_config.py` | Site/run overrides currently supplied with this copy. It changes the actual test protocol substantially and defines the required local results path. |
| `Config/temperature_config.py` | MCC network endpoint and thermocouple channel definitions; imported directly by the temperature controller. |
| `Config/analysis_config.py` | Filter identities, nominal wavelengths/widths, image ROIs and analysis options; imported directly by analysis. |
| `Control/temperature_control.py` | MCC connection, thermocouple readings, Hall input, lamp/freezer/camera output switching. |
| `Control/temperature_logger.py` | Background nominal 1 s logging, latest-record access and forwarding control methods through one owned controller. |
| `Control/filterwheel_control.py` | Calls `ticcmd`, sets motion/current parameters, moves to positions, Hall homing and shutdown. |
| `Control/camera_keepalive_stream.py` | Starts, checks and stops a remote camera stream to `/dev/null`; captures process/event details. |
| `Scripts/run_long_test.py` | Repeated tests, pre-cool, camera power sequence, stop conditions, scheduled sweeps, storage checks, event/summary files and bounded camera recovery. |
| `Scripts/run_single_sweep_remote.py` | One wheel sweep, optional homing, illumination timing, internal camera readings, per-filter remote capture, transfer and local presence checks. |
| `Camera_scripts/camera_config.py` | Camera-side video format, resolution, frame rate, default exposure and gain. |
| `Camera_scripts/camera_control.py` | Applies V4L2 settings, runs a one-frame GStreamer PNG pipeline, checks file existence/size, and writes per-image metadata. |
| `Camera_scripts/capture_remote.py` | Camera-side entry point accepting output path and optional exposure-control value. |
| `Camera_scripts/read_camera_temperatures.py` | Camera-side JSON readout from `sensors -j` and V4L2, including temporary-stream refresh. |
| `Scripts/analyze_test_folder.py` | Single-test image metrics, temperature columns, CSVs, plots and profile diagnostics. |
| `Scripts/preview_analysis_rois.py` | Image/ROI previews used to review analysis regions. |
| `Scripts/analyze_repeat_tests.py` | Batch single-test analysis, cross-cycle diagnostics and repeatability summaries. |
| `Scripts/compare_tests_streamlit.py` | Interactive comparison application with metadata editing. |
| `Scripts/compare_tests_streamlit_updated.py` | A second comparison implementation with expanded test/repeat-group browsing. The authoritative entry point needs owner confirmation. |
| `Scripts/repair_repeat_group_metadata.py` and `Scripts/repair_and_rename_repeat_folders.py` | Historical metadata/folder repair tools. They modify stored records or names and are not required for a normal new acquisition. |

The analysis methods and data interpretation belong to the analysis chapter; this chapter records their software entry points and environment requirements.

## Configuration precedence

`Config/system_config.py` defines base values, then performs `from Config.local_config import *` inside an `ImportError` handler. Therefore the supplied local values win for consumers that import from `Config.system_config`. Editing a base value with an existing local override will not change the effective value. [Override mechanism](../Config/system_config.py#L169).

Important boundaries:

- `Config/temperature_config.py` and `Config/analysis_config.py` are separate configurations; the wildcard import does not replace the direct imports from those modules.
- The camera imports `camera_config.py` on the camera computer. Host overrides are not automatically shared with it. The host explicitly passes each filter's exposure value to the camera capture entry point.
- Many constants are imported by value when a program starts. Restart the appropriate process after changing configuration; do not expect live reload.
- `LOCAL_DATA_ROOT` is defined only in the supplied `local_config.py`, although acquisition/preflight import it from `system_config.py`. Removing the local file does not produce a complete working base-only configuration. Its current path refers to a different Linux user's home directory; choose a reviewed, writable results location on the intended host.

Sources: [temperature import](../Control/temperature_control.py#L23), [analysis import](../Scripts/analyze_test_folder.py#L13), [camera-side import](../Camera_scripts/capture_remote.py#L4), [explicit exposure transfer](../Scripts/run_single_sweep_remote.py#L319), [local results definition](reference/local_config_snapshot.txt#L5), [host imports](../Scripts/run_long_test.py#L15).

## Current effective acquisition settings

“Base” means the value before local overrides. “Effective” means the supplied local snapshot after override. These are configuration values and limits, not measured test results or accepted protocol specifications. [Base timing and pre-cool settings](../Config/system_config.py#L62), [base endpoint settings](../Config/system_config.py#L119), [local overrides](reference/local_config_snapshot.txt#L5).

| Setting | Base | Effective supplied configuration | Meaning |
|---|---|---|---|
| `PRECOOL_BEFORE_TEST_ENABLED` | `True` | `True` | Automated pre-cool before each test. |
| `PRECOOL_SENSOR_NAME` | `probe_2` | `probe_5` | Probe used for the cooling threshold. |
| `PRECOOL_TARGET_C` | -5 °C | 12 °C | Pre-cool completes when probe is at or below target. |
| `PRECOOL_TIMEOUT_HOURS` | 4 h | 7 h | Maximum pre-cool wait. |
| `PRECOOL_POLL_INTERVAL_S` | 5 s | 5 s | Threshold polling cadence. |
| `PRECOOL_SETTLE_AFTER_FREEZER_OFF_S` | 60 s | 60 s | Delay after switching freezer off. |
| `TEST_END_MODE` | `time` | `temperature` | Effective measurement phase uses a probe threshold. |
| `TEST_END_SENSOR_NAME` | `probe_2` | `probe_5` | Probe used for measurement endpoint. |
| `TEST_END_TARGET_C` | 40 °C | 40 °C | Measurement threshold. |
| `TEST_END_DIRECTION` | `above` | `above` | Endpoint requires temperature at or above threshold. |
| `TEST_END_REQUIRED_CONSECUTIVE_READS` | 3 | 3 | Several new logger records must satisfy endpoint. |
| `TEST_END_SAFETY_TIMEOUT_HOURS` | 14 h | 14 h | Temperature-mode deadline checked between operations; blocking work and the endpoint sweep can extend wall-clock duration. |
| `TEST_END_FINAL_SWEEP_ENABLED` | `True` | `True` | Immediate final sweep when endpoint/timeout occurs between scheduled sweeps. |
| `TEST_DURATION_HOURS` | 1 h | 12 h | Duration setting for time mode; not the effective temperature-mode endpoint. |
| `SWEEP_INTERVAL_SECONDS` | 180 s | 120 s | Wait scheduled after each attempt; capture/transfer time adds to start-to-start spacing. |
| `MAX_SWEEPS` | 25 | 500 | Cap on numbered attempts including failures; can terminate before temperature endpoint. |
| `REPEAT_TEST_COUNT` | 1 | 8 | Number requested in the repeat sequence. |
| `REPEAT_DELAY_BETWEEN_TESTS_S` | 0 s | 60 s | Delay between completed tests. |
| `REPEAT_CONTINUE_AFTER_FAILURE` | `False` | `False` | A failed test normally ends the repeat sequence. |
| `REPEAT_STOP_FILE_NAME` | `STOP_REPEAT` | `STOP_REPEAT` | Stop-sequence marker in the local results root. |
| `CAMERA_KEEPALIVE_STREAM_ENABLED` | `False` | `True` | Keep video pipeline active between image sweeps. |

The present effective protocol is therefore cooling to a `probe_5` threshold, switching the freezer off, then capturing repeatedly while warming toward a `probe_5` endpoint. That is a configured protocol for this snapshot, not evidence of a universal “freezer test” temperature range.

### Configured warm start is not implemented

`local_config.py` defines `PRECOOL_CAMERA_WARM_START_ENABLED=True`, a `probe_5` sensor and a 15 °C threshold, with comments about powering the camera on before it gets too cold. None of those three constants is referenced outside that file in the supplied source. The current long-test runner instead switches camera power off during pre-cool, switches freezer off at the pre-cool target, waits the settle period, and then switches camera power on for the 45 s boot wait. Do not describe a 15 °C warm start as operational in this version. [Unused local settings](reference/local_config_snapshot.txt#L18), [implemented pre-cool](../Scripts/run_long_test.py#L330), [implemented power-on](../Scripts/run_long_test.py#L559).

### Other control, recovery and timing settings

| Setting group | Current value or behavior | Source |
|---|---|---|
| Camera power control | Enabled; active-high DIO bit 2; 45 s boot wait; end-of-test off flag enabled. | [System settings](../Config/system_config.py#L34) |
| Freezer control | Enabled; active-high DIO bit 3. Duplicate base declarations have the same values. | [System settings](../Config/system_config.py#L51) |
| Lamp capture delay | 2 s after lamp-on; lamp then remains on for the sweep's image loop. | [Setting](../Config/system_config.py#L159), [sequence](../Scripts/run_single_sweep_remote.py#L299) |
| Acquisition retry | 30 s retry delay; maximum consecutive failures 3. | [Settings](../Config/system_config.py#L142) |
| Storage threshold | 5 GiB (`1024**3` bytes per unit) free-space threshold on the local output filesystem. | [Setting](../Config/system_config.py#L146), [check](../Scripts/run_long_test.py#L73) |
| Automatic camera recovery | Enabled; up to 3 per test; camera off wait 15 s, then boot wait and keepalive restoration. Triggered by recognized capture-error strings. | [Settings](../Config/system_config.py#L41), [implementation](../Scripts/run_long_test.py#L185) |
| Manual freezer diagnostic | Configured on-time 600 s and final off wait 600 s. | [Settings](../Config/system_config.py#L76), [diagnostic](../Scripts/test_freezer_relay.py#L51) |

The 600 s minimum-off constant is used by the manual freezer diagnostic's final wait; it is not a general interlock inside `freezer_on()` and is not imported by the long-test runner. The diagnostic initially waits only 2 s between commanding off and then on. Its name/comment does not establish protection against a compressor that was switched off immediately before the diagnostic. Review the actual freezer requirements and sequencing before interpreting this setting as enforced protection. [Diagnostic initial sequence](../Scripts/test_freezer_relay.py#L80), [low-level freezer output](../Control/temperature_control.py#L116), [runner imports](../Scripts/run_long_test.py#L15).

## Camera capture configuration and behavior

| Camera-side setting | Supplied value |
|---|---|
| Video device | `/dev/video4` |
| Frame size | 1296 × 1032 pixels |
| Pixel format | `GRAY8` |
| Frame rate | 24 frames/s requested |
| Gain | 0 requested |
| Default exposure control | `exposure_time_absolute=20000` |
| Image staging root | `/root/scripts/data` |
| Configured log root | `/root/scripts/logs`; the capture controller shown here does not itself use `LOG_ROOT` |

Source: [camera configuration](../Camera_scripts/camera_config.py#L2).

The host normally overrides exposure per filter: 3000, 15000, 8000 and 15000 for filters 1–4 respectively. A missing mapping uses host `DEFAULT_EXPOSURE_TIME_ABSOLUTE=20000`. The optional CLI argument to `capture_remote.py` takes precedence over the camera-side default. These numbers are driver-control values; unit/range confirmation remains open. [Exposure settings](../Config/system_config.py#L148), [CLI override](../Camera_scripts/capture_remote.py#L16).

Before each frame, the camera program applies requested frame rate, exposure and gain through `v4l2-ctl`, waits 0.1 s, and queries settings. It then runs `gst-launch-1.0 -e` with `v4l2src num-buffers=1`, raw `GRAY8` caps, `pngenc`, and `filesink`. The output is one PNG from an 8-bit grayscale input pipeline, plus a JSON sidecar. This does not establish the sensor's native bit depth or record higher-bit raw samples. [Settings](../Camera_scripts/camera_control.py#L80), [pipeline](../Camera_scripts/camera_control.py#L106).

The sidecar records requested and before/after applied exposure/gain, stream parameters, image dimensions and encoding, capture status, file size, timestamp and the pipeline command. Success requires a nonempty image file. It does not include an image-content/saturation/alignment acceptance check at capture time. The timestamp is recorded before launching the pipeline, not a hardware exposure timestamp. [Capture verification and metadata](../Camera_scripts/camera_control.py#L126).

## Streaming and internal-temperature configuration

The current local settings enable a long `v4l2-ctl --stream-mmap` stream on `/dev/video4`, with `100000000` requested frames, 2 s startup wait, frames discarded to `/dev/null`, PID file `/tmp/freezertest_keepalive_stream.pid`, and log file `/tmp/freezertest_keepalive_stream.log`. It is finite by frame count, despite being called continuous/keepalive. The code tests process existence for status, not actual frame progress or sensor freshness. [Settings](../Config/system_config.py#L99), [local enablement](reference/local_config_snapshot.txt#L36), [status](../Control/camera_keepalive_stream.py#L91), [launch](../Control/camera_keepalive_stream.py#L126).

Normal capture shares the same video node, so the sweep reads internal temperatures while the keepalive is active, stops it, waits 2 s for buffers/device release, captures all filters, then restarts it and reads temperatures again. The sweep avoids starting a second refresh stream if a keepalive object was supplied. [Sweep sequence](../Scripts/run_single_sweep_remote.py#L282).

Keepalive startup can terminate stale matching `v4l2-ctl` streams to `/dev/null`, including streams whose PID file was lost. This is useful cleanup but matters if someone is using another such diagnostic stream on the camera. Stop first requests termination and waits about 3 s, then force-kills if necessary. [Stale cleanup](../Control/camera_keepalive_stream.py#L134), [stop](../Control/camera_keepalive_stream.py#L184).

For reads without keepalive, the temporary sensor-refresh stream requests 300 frames and waits 1 s before reading `sensor_temperature` while the stream remains running. Internal temperature collection is enabled but non-fatal: the sweep retains failure/error details and continues capture. A successful remote JSON read can still contain sensor-specific errors, so inspect `remote_payload.errors` and per-sensor warnings rather than relying on outer `status=success`. [Refresh configuration](../Config/system_config.py#L88), [temporary stream](../Camera_scripts/read_camera_temperatures.py#L152), [host wrapper](../Scripts/run_single_sweep_remote.py#L81), [combined payload](../Camera_scripts/read_camera_temperatures.py#L335).

## Dependencies and environment

No requirements manifest, lockfile, or packaged environment was present among the supplied files. The following dependencies are established by imports and external commands; versions and complete installation procedure remain to be recorded from the working test systems.

| Environment | Dependencies used by the supplied source | Notes |
|---|---|---|
| Host acquisition | Python 3.10+ syntax, `uldaq`, MCC runtime/driver capable of the configured network device, `ticcmd`, OpenSSH `ssh` and `scp` | `str \| None` type hints require Python 3.10 or later in files without postponed annotation evaluation. The correct MCC runtime and permissions depend on the actual installed unit/system. |
| Host preflight | Above, plus `ping`; writable output storage | Includes device connection and output-state changes; not purely passive. |
| Camera computer | Python 3.10+ syntax, `v4l2-ctl`, `gst-launch-1.0`, V4L2 device/driver, GStreamer elements `v4l2src`, raw-video caps, `pngenc`, `filesink` | Camera scripts use standard-library Python modules; actual capture depends on external binaries/plugins. |
| Camera internal readings | `sensors` with JSON output, `v4l2-ctl` | Missing optional hardware-monitor readings are returned as errors. |
| Host offline analysis | NumPy, pandas, Matplotlib, Pillow; SciPy for Gaussian fitting | SciPy import failure is caught, but enabled Gaussian fit metrics cannot then be treated as available. |
| Interactive comparison | Streamlit, pandas, Plotly | Two application files exist; confirm which one is maintained. |

Sources: [DAQ imports](../Control/temperature_control.py#L12), [Tic call](../Control/filterwheel_control.py#L42), [SSH](../Scripts/run_single_sweep_remote.py#L51), [capture pipeline](../Camera_scripts/camera_control.py#L114), [hardware-monitor command](../Camera_scripts/read_camera_temperatures.py#L99), [analysis imports and SciPy fallback](../Scripts/analyze_test_folder.py#L4), [dashboard imports](../Scripts/compare_tests_streamlit_updated.py#L31).

Run host commands from the repository root with the project available on the Python import path, as shown by the diagnostic scripts' examples: `PYTHONPATH=. python3 Scripts/<entry_point>.py`. Camera-side files are colocated and import their sibling modules directly. Do not use hardware-control scripts as an automated test suite simply because their names begin with `test_`.

## Deployment and diagnostics

`Scripts/deploy_camera_scripts.sh` copies four camera-side files using SCP and then creates data/log directories over SSH. Its camera endpoint/account are hard-coded inside the shell script rather than read from `Config/system_config.py`; changing the Python endpoint does not update this deployment destination. It copies into `/root/scripts/` **before** creating subdirectories, so `/root/scripts/` must already exist for a first deployment. It does not install dependencies or compare deployed checksums. [Deployment script](../Scripts/deploy_camera_scripts.sh#L4).

| Program | Intended use | Material actions and limitations |
|---|---|---|
| `preflight_check.py` | Connectivity, SSH, camera script/data presence, Tic availability/status, output storage, MCC temperature/Hall read | Creates/deletes a storage test file; MCC connect/disconnect changes outputs and can turn camera off. `--test-camera-capture` creates/deletes a remote capture; `--test-lamp` toggles lamp. It is not suitable to run alongside an active test. |
| `read_temp_loop.py` | Print/log thermocouple readings nominally every second | Uses full `TemperatureController`; connect/disconnect output side effects apply. Writes `temperature_log.jsonl` in working directory. |
| `test_hall_sensor.py` | Watch raw Hall state while manually moving wheel | Standalone hard-coded MCC endpoint, AUXPORT0 bit 1; does not consume the shared host/channel configuration. Runs at top level when executed/imported. |
| `calibrate_filterwheel.py` | Manual wheel alignment and saved position map | Moves/energizes motor and optionally controls lamp/camera; JSON is not auto-applied to running configuration. |
| `test_homing_repeatability.py` | Three home cycles with +250 position offset between cycles | Produces diagnostic JSON and temperature log; controller positions are not a calibrated optical repeatability measurement. |
| `test_filterwheel_idle_current.py` | Move each configured filter, wait 10 s for manual idle-current/heating check | Does not perform Hall homing itself; current state/position reference must be understood before motion. |
| `test_freezer_relay.py` | Exercise freezer contactor | Switches real freezer and waits; CLI can override waits. Does not enforce a global minimum-off interlock. |
| `test_camera_internal_temperatures.py` | One remote camera-temperature JSON read | Can create a temporary video stream; not just a file read. |
| `test_capture_with_keepalive_stream.py` | Diagnostic experiment capturing while streaming | Deliberately probes the concurrent-access case that the production sequence normally avoids. |
| `test_keepalive_pause_capture.py` | Exercise pause/capture/restart sequence | Changes streaming state and captures an image; production-like control diagnostic. |

Sources: [preflight main](../Scripts/preflight_check.py#L275), [MCC preflight cleanup](../Scripts/preflight_check.py#L185), [temperature loop](../Scripts/read_temp_loop.py#L19), [standalone Hall watcher](../Scripts/test_hall_sensor.py#L16), [homing diagnostic](../Scripts/test_homing_repeatability.py#L33), [idle-current diagnostic](../Scripts/test_filterwheel_idle_current.py#L38), [freezer diagnostic](../Scripts/test_freezer_relay.py#L51), [internal reading diagnostic](../Scripts/test_camera_internal_temperatures.py#L17), [concurrent-stream experiment](../Scripts/test_capture_with_keepalive_stream.py#L4), [pause/capture diagnostic](../Scripts/test_keepalive_pause_capture.py#L4).

## Configuration review checklist for the next revision

1. Confirm which copied source version matches the running host and deployed camera; record commit/checksums and environment versions.
2. Select the intended local results path and confirm it is writable on the host actually running tests.
3. Confirm current camera identity/operator/notes rather than carrying them into every future run unchanged. Their supplied values describe one configured run context.
4. Resolve the unused warm-start settings before relying on camera initialization during cooling.
5. Confirm shared-supply sequencing, actual compressor limits and whether protections should be enforced centrally.
6. Record exposure-control units/range, controller motion units and required current against the actual hardware.
7. Choose the maintained Streamlit entry point; preserve historical repair tools as explicitly manual utilities.
8. Record the approved physical probe map, then keep probe names and end-condition settings aligned with it.
