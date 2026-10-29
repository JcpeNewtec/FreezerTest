# Running the freezer test

This chapter combines the reviewed source behavior with the owner's operating clarifications of 27 and 29 October 2026. Normal pre-cool uses **`probe_5` at 5 °C**. The freezer cools with the camera off; afterward the freezer is off while camera heat and intermittent lamp operation warm the chamber during measurement. Filter positions are verified/calibrated before each run, and focus is adjusted manually to the target plane when the camera changes. Individual test results are outside this knowledge base. [Owner review R1](10-sources-and-maintenance.md#r1-owner-review-27-october-2026), [owner review R2](10-sources-and-maintenance.md#r2-owner-review-and-component-photos-29-october-2026).

## What a run does

The main entry point is `Scripts/run_long_test.py`. For each configured repeat it creates a separate test folder, starts continuous MCC temperature logging, pre-cools with the camera off, turns the freezer off, starts the camera and optional continuous stream, collects periodic filter sweeps, and shuts down the controlled outputs. The next repeat starts a fresh pre-cool cycle. **The camera and freezer are never on together in normal operation.** During measurement the freezer stays off; heat from the camera and lamp warms the chamber toward the end-temperature condition. The runner commands no separate heater or closed-loop temperature ramp. [Owner review R2](10-sources-and-maintenance.md#r2-owner-review-and-component-photos-29-october-2026), [run setup](../Scripts/run_long_test.py#L441), [pre-cool](../Scripts/run_long_test.py#L287), [measurement startup](../Scripts/run_long_test.py#L537), [repeat loop](../Scripts/run_long_test.py#L1025).

```text
Initialize folder and logger
  → Wait for a valid pre-cool probe reading
  → Camera/lamp off; freezer on
  → Pre-cool threshold reached; freezer off; timed settle
  → Camera on; boot wait; keepalive stream if enabled
  → Measurement clock starts
  → Camera heat + sweep-switched lamp warm the chamber
  → Sweep → wait interval → sweep … until end condition/stop/failure
  → Stop stream; freezer off; lamp off; camera off; stop logger
  → Inter-repeat delay → next repeat
```

The diagram represents the normal path when the relevant control features are enabled. Normal pre-cool ends when `probe_5` reaches **5 °C or below**. The lamp is on for each sweep's 2 s warm-up and image loop, then off between sweeps; it is not continuously on during the thermal warm-up phase. **Lamp and freezer are never enabled together in normal operation**, as the owner also confirms in the supply-map follow-up. Pre-cooling can be skipped by configuration, sweeps can fail, and stop requests or timeouts can interrupt the path. [Owner review R1](10-sources-and-maintenance.md#r1-owner-review-27-october-2026), [owner follow-up R2](10-sources-and-maintenance.md#r2-owner-review-and-component-photos-29-october-2026), [lamp control](../Scripts/run_single_sweep_remote.py#L299).

## Configuration to review before starting

`Config/system_config.py` imports `Config.local_config` at the end using a wildcard import. Matching names in `local_config.py` therefore override the base settings. Before a normal run, confirm `PRECOOL_SENSOR_NAME="probe_5"` and `PRECOOL_TARGET_C=5.0`. [Source: override import](../Config/system_config.py#L169), [owner review R1](10-sources-and-maintenance.md#r1-owner-review-27-october-2026).

The table below preserves the **historical copied profile** for traceability. Its **12 °C pre-cool threshold was a deliberate shorter recent trial**. It is not the normal 5 °C procedure, and the original snapshot is retained as evidence rather than silently rewritten. Review all run-specific settings before acquisition. [Historical snapshot](reference/local_config_snapshot.txt), [owner review R1](10-sources-and-maintenance.md#r1-owner-review-27-october-2026).

| Setting | Original base setting | Historical copied local setting | Meaning |
|---|---|---|---|
| `LOCAL_DATA_ROOT` | Required from local configuration | `/home/henrik/Documents/FreezerTest_Results` | Result folder on the acquisition host; verify that it exists/is writable on the actual host |
| `PRECOOL_BEFORE_TEST_ENABLED` | `True` | `True` | Run pre-cool before each repeat |
| `PRECOOL_SENSOR_NAME` | `probe_2` | `probe_5` | Probe used to decide pre-cool completion |
| `PRECOOL_TARGET_C` | −5 °C | 12 °C | Shorter trial value; normal pre-cool is `probe_5` ≤5 °C |
| `PRECOOL_TIMEOUT_HOURS` | 4 h | 7 h | Maximum pre-cool polling duration, checked at loop boundaries |
| `PRECOOL_POLL_INTERVAL_S` | 5 s | 5 s | Pre-cool decision polling interval |
| `PRECOOL_SETTLE_AFTER_FREEZER_OFF_S` | 60 s | 60 s | Fixed wait after switching freezer off |
| `TEST_END_MODE` | `time` | `temperature` | Selects measurement end logic |
| `TEST_DURATION_HOURS` | 1 h | 12 h | Measurement duration in time mode; not the selected end criterion in copied temperature mode |
| `TEST_END_SENSOR_NAME` | `probe_2` | `probe_5` | End-condition probe |
| `TEST_END_TARGET_C` / direction | 40 °C / `above` | 40 °C / `above` | End condition is selected reading ≥40 °C |
| `TEST_END_REQUIRED_CONSECUTIVE_READS` | 3 | 3 | New observed records satisfying end threshold |
| `TEST_END_SAFETY_TIMEOUT_HOURS` | 14 h | 14 h | Measurement deadline in temperature mode |
| `TEST_END_FINAL_SWEEP_ENABLED` | `True` | `True` | Request endpoint sweep for temperature target or temperature-mode timeout |
| `SWEEP_INTERVAL_SECONDS` | 180 s | 120 s | Wait scheduled **after** a sweep attempt finishes |
| `MAX_SWEEPS` | 25 | 500 | Maximum numbered sweep attempts, including failures |
| `CAMERA_KEEPALIVE_STREAM_ENABLED` | `False` | `True` | Keep camera video stream active between image sweeps |
| `REPEAT_TEST_COUNT` | 1 | 8 | Maximum repeats for one invocation |
| `REPEAT_DELAY_BETWEEN_TESTS_S` | 0 s | 60 s | Delay after a repeat before the next one |
| `REPEAT_CONTINUE_AFTER_FAILURE` | `False` | `False` | Stop sequence after a fatal test failure |

Sources: [base pre-cool/repeats](../Config/system_config.py#L62), [base end/cadence](../Config/system_config.py#L119), [local overrides](reference/local_config_snapshot.txt#L5), [local pre-cool/stream](reference/local_config_snapshot.txt#L27), [local repeats](reference/local_config_snapshot.txt#L46).

Also check camera identity, operator, notes, filter positions, and exposures. The copied profile's filter positions are −51, −251, −451, and −651 controller position units, with requested exposure controls 3000, 15000, 8000, and 15000 respectively. Positions must be verified/calibrated for each run; these numbers are not permanent alignment references. The code passes exposure values to `exposure_time_absolute`; the physical unit must be confirmed from the camera/driver documentation. [Sources: historical filter and exposure settings](reference/local_config_snapshot.txt#L52), [capture control](../Camera_scripts/camera_control.py#L50), [owner review R1](10-sources-and-maintenance.md#r1-owner-review-27-october-2026).

## Operator preparation

1. Identify the camera under test, including its family variant and individual unit. The setup supports Qtec Hypervision variants rather than one fixed reference camera. Keep the same-type unit comparison and evaluation of a camera change identifiable in the run context.
2. **Whenever the camera is changed, manually focus it on the target plane.** Focus is an operator adjustment; the acquisition code does not perform autofocus.
3. **Before every run, verify/calibrate the filter positions.** The owner reports that the motor's internal reference may drift. Hall homing supplies a home reference during managed sweeps, but does not replace this per-run optical-position verification.
4. Use the calibration interface as needed, then ensure the reviewed positions are in the effective `FILTER_POSITIONS` configuration. `calibrated_filter_positions.json` is not loaded automatically by the test runner.
5. Record the actual probe positions for this run, including any changes from the usual map below. Confirm which physical measurement is selected for pre-cool and measurement end.
6. Check the intended pre-cool threshold, camera identity/operator/notes, capture settings, storage path, and stop-file state before the preflight/acquisition sequence.

The manual focus and per-run calibration requirements are owner-confirmed. Their detailed acceptance criteria and adjustment method still need to be recorded. [Owner review R1](10-sources-and-maintenance.md#r1-owner-review-27-october-2026), [calibration workflow](02-hardware-and-connections.md#calibration-workflow-supported-by-the-code), [calibration save](../Scripts/calibrate_filterwheel.py#L207), [runtime position use](../Scripts/run_single_sweep_remote.py#L314).

### Usual probe positions

| Probe | Usual owner-reported placement |
|---|---|
| `probe_1` | Camera case on the side without the computer |
| `probe_2` | Camera case on the computer side, at the hotter area |
| `probe_3` | Side of the camera case midway between the non-computer and computer sides |
| `probe_4` | Camera-facing top surface of an aluminium tray in the upper freezer, away from the camera and lamp |
| `probe_5` | Underside of the same tray, away from heat sources |

This is the usual arrangement, not a permanent assignment for every experiment. `probe_5` normally measures the tray underside, **not free air or camera core temperature**. A 5 °C threshold at that probe does not establish uniform camera or chamber temperature. Keep the actual run map with the test context so temperature-associated results remain interpretable. [Owner review R2](10-sources-and-maintenance.md#r2-owner-review-and-component-photos-29-october-2026).

## Starting a run

These commands are verified from the source entry points; they were **not executed against hardware** while preparing this knowledge base. Run them from the repository root in the configured acquisition environment.

```bash
PYTHONPATH=. python3 Scripts/preflight_check.py
PYTHONPATH=. python3 Scripts/run_long_test.py
```

Preflight is a separate command. The long-test runner does not automatically run it. Its default checks are camera and MCC ping, camera SSH, remote capture-script/data-folder presence, `ticcmd` availability/device/status, local storage write/free space, and an MCC temperature/Hall read. It exits with status 1 if any check fails. [Source: preflight main](../Scripts/preflight_check.py#L275).

**Preflight operates real outputs.** Its MCC check connects a `TemperatureController`; connection switches the lamp and enabled freezer output off, and disconnection attempts lamp/freezer/camera power off. Consequently, even default preflight must not be treated as a passive diagnostic to run during acquisition. Optional flags add a real capture, deleted afterward, or a brief lamp toggle. [Sources: MCC check](../Scripts/preflight_check.py#L185), [connect](../Control/temperature_control.py#L69), [disconnect](../Control/temperature_control.py#L168), [optional checks](../Scripts/preflight_check.py#L107), [optional lamp](../Scripts/preflight_check.py#L223).

```bash
PYTHONPATH=. python3 Scripts/preflight_check.py --test-camera-capture --test-lamp
```

The camera deployment helper is `bash Scripts/deploy_camera_scripts.sh`. It copies `capture_remote.py`, `camera_control.py`, `camera_config.py`, and `read_camera_temperatures.py` to `/root/scripts/`, then creates the remote `data` and `logs` subfolders. It has its own hard-coded camera address/user and assumes `/root/scripts/` already exists for the copy step. Check those before using it; editing host configuration alone does not update the helper. [Source: deployment script](../Scripts/deploy_camera_scripts.sh#L4).

### What preflight does not establish

Successful preflight does not verify optical alignment, correct filter identity, probe placement/calibration, compressor protection, environmental equilibrium, or image-analysis quality. The default preflight does not capture an image or perform filter-wheel homing. It checks that the capture script exists, rather than comparing all deployed camera files with the local versions. The configured camera must already be reachable for its SSH checks. [Source: implemented checks](../Scripts/preflight_check.py#L275).

## Pre-cooling and the start of measurement

1. Start the MCC logger with a requested 1 s interval, before pre-cool and before measurement timing begins.
2. Wait up to 60 s for a value from `PRECOOL_SENSOR_NAME`. This wait occurs even if pre-cooling will subsequently be skipped.
3. When pre-cooling and freezer control are enabled, attempt lamp off and camera off, then freezer on. Errors while forcing lamp/camera off are printed and do not themselves stop pre-cooling.
4. Poll the latest logger record until selected temperature ≤ target; normal settings are **`probe_5` ≤5 °C**. This is one threshold crossing, **not a temperature stability window or soak hold**. If the probe is already at/below target, pre-cool may finish almost immediately after freezer-on.
5. Switch freezer off and wait the fixed settle duration.
6. Power camera on when enabled, wait 45 s by default, then start keepalive if enabled. Failure to establish keepalive at measurement startup aborts the test.
7. Only now set `measurement_start_time`, calculate the end deadline, and allow the first sweep immediately.

Sources: [first record](../Scripts/run_long_test.py#L266), [pre-cool sequence](../Scripts/run_long_test.py#L287), [measurement startup](../Scripts/run_long_test.py#L537), [boot wait](../Config/system_config.py#L34), [measurement clock](../Scripts/run_long_test.py#L586).

The owner confirms that the operating camera and lamp provide the heat for the measurement warm-up with freezer power off. In the supplied code the camera remains powered during this phase, while the lamp is switched only for sweep capture. No lamp duty-cycle change or extra heater is implied by the thermal description. [Owner review R2](10-sources-and-maintenance.md#r2-owner-review-and-component-photos-29-october-2026), [sweep lamp sequence](../Scripts/run_single_sweep_remote.py#L299).

There is no explicit probe-freshness limit, stability slope check, or finite-number validation in the threshold helper: it converts the selected value with `float()`. Pre-cool polls the latest available record rather than requiring a new record on each poll. Confirm that logged readings are advancing when interpreting a run. [Sources: conversion helper](../Scripts/run_long_test.py#L118), [pre-cool loop](../Scripts/run_long_test.py#L352).

## What happens during one sweep

Each long-test sweep receives the logger's latest external-temperature record, Hall reader, lamp callbacks, and optional keepalive object. Its normal sequence is:

1. Create a local sweep folder and matching temporary camera-side folder.
2. Initialize filter-wheel controller. If enabled, home using the Hall input and the configured search parameters.
3. Read internal camera temperatures with label `before_capture`.
4. Stop keepalive before capture, if configured, and wait the default 2 s for video-device buffers to release.
5. Switch lamp on and wait the default 2 s warm-up.
6. Visit filters in ascending numerical order. For each: move to configured target, read actual controller position, select per-filter exposure or default exposure, and invoke the remote PNG capture.
7. In the capture cleanup block, switch lamp off, restart keepalive if configured, and read internal camera temperatures with label `after_capture`.
8. Return wheel to zero and read its final position on successful capture path. Shutdown of the wheel controller is attempted in the outer `finally` block, including on failure.
9. Write local `sweep_summary.json`, copy the remote folder to local disk, check for all expected filenames, and only then remove the remote folder.
10. Write transfer timing. The long-test runner then adds its latest `temperature_after_sweep` record to the summary.

Sources: [sweep arguments and folder creation](../Scripts/run_single_sweep_remote.py#L201), [initialization and capture](../Scripts/run_single_sweep_remote.py#L256), [capture cleanup](../Scripts/run_single_sweep_remote.py#L344), [return/shutdown/transfer](../Scripts/run_single_sweep_remote.py#L364), [long-run after-sweep record](../Scripts/run_long_test.py#L819).

One image per filter is captured by a GStreamer pipeline using `v4l2src` with `num-buffers=1` and `pngenc`. Camera settings are applied before capture, and requested/applied settings are recorded in an image sidecar. The copied camera configuration requests 1296 × 1032 pixels, `GRAY8`, 24 frames/s, and gain 0. There is no image averaging or multi-frame selection in this capture function. [Sources: camera configuration](../Camera_scripts/camera_config.py#L2), [settings and pipeline](../Camera_scripts/camera_control.py#L80).

### Standalone single-sweep entry point

```bash
PYTHONPATH=. python3 Scripts/run_single_sweep_remote.py
```

This creates a `manual_test_<timestamp>` folder and calls `run_single_sweep()` with its defaults. It **does not** create an MCC logger, power-cycle the camera, pre-cool, home via Hall, control the lamp, or pass a keepalive object. The operator must arrange appropriate illumination, camera availability, wheel reference, and video-device availability. Its behavior is not equivalent to one fully managed long-test repeat. [Sources: standalone main](../Scripts/run_single_sweep_remote.py#L421), [function defaults](../Scripts/run_single_sweep_remote.py#L201).

## Timing and end conditions

| Mechanism | Implemented meaning |
|---|---|
| Sweep interval | After every attempt, the runner schedules the next normal sweep for current time + interval. Capture, homing, internal-temperature reads, transfer, and cleanup add to start-to-start spacing. This is not a fixed 120 s sampling grid. |
| Time mode | Ends when elapsed measurement time reaches `TEST_DURATION_HOURS`, checked between sweep attempts/waits. No extra endpoint sweep is requested in this branch. |
| Temperature mode | Ends when selected probe meets inclusive `above` (≥ target) or `below` (≤ target) condition for the required count of new records observed by the runner. A nonmeeting or missing-value record resets the count. |
| Record uniqueness | Uses the temperature record's `timestamp` to avoid repeatedly counting one record; falls back to object identity when timestamp is missing. |
| Temperature safety timeout | Uses `TEST_END_SAFETY_TIMEOUT_HOURS` from measurement start. Does not include pre-cool, settle, or camera boot time. |
| Endpoint images | When enabled in temperature mode, threshold or timeout forces an immediate final sweep regardless of next normal trigger. Completion follows a successful final sweep. Failures can cause further attempts, until another stopping condition intervenes. |
| Maximum sweeps | Caps numbered attempts. Failed sweeps increment the index too. Reaching the cap can complete a test before the temperature target. |

Sources: [end-mode helpers](../Scripts/run_long_test.py#L133), [record identity](../Scripts/run_long_test.py#L163), [deadlines](../Scripts/run_long_test.py#L590), [end logic](../Scripts/run_long_test.py#L681), [consecutive observations](../Scripts/run_long_test.py#L733), [rescheduling/max attempts](../Scripts/run_long_test.py#L919).

The runner does not examine the end-condition temperature during a blocking sweep or transfer. “Three consecutive reads” means consecutive **new records observed by this loop**, not necessarily every record written by the logger. The 14 h deadline is a logical measurement deadline, not a guaranteed wall-clock cutoff: a current operation, recovery, or requested endpoint sweep can extend it. For example, SSH capture has a 60 s host timeout, but `scp` is invoked without a subprocess timeout. [Sources: measurement loop](../Scripts/run_long_test.py#L646), [remote capture timeout](../Scripts/run_single_sweep_remote.py#L71), [copy implementation](../Scripts/run_single_sweep_remote.py#L157).

`completed` alone does not prove target temperature was reached. Inspect `completion_reason`: `time_limit`, `temperature_target`, `temperature_safety_timeout`, or `max_sweeps`. [Sources: time completion](../Scripts/run_long_test.py#L685), [temperature completion](../Scripts/run_long_test.py#L778), [post-sweep completion](../Scripts/run_long_test.py#L932).

## Keepalive and internal-temperature behavior

Keepalive runs a remote `v4l2-ctl` memory-mapped video stream to `/dev/null`, retaining no image file. Its purpose in the code is to keep the camera/TEC/video pipeline active between sweeps; it is not an independent implementation of temperature regulation. PID and log files live under `/tmp` by default. Starting it can terminate stale `v4l2-ctl` streams to `/dev/null` on that camera. [Sources: rationale](../Control/camera_keepalive_stream.py#L4), [start command](../Control/camera_keepalive_stream.py#L126), [configured files](../Config/system_config.py#L99).

Because keepalive and PNG capture use the same V4L2 device, keepalive normally stops before image capture and restarts afterward. Stop first sends a normal termination, waits about 3 s, and may force termination. The status check establishes that a PID is alive; it does not inspect frame content or prove streaming health. Startup at measurement begin and after camera recovery requires `running=True`; ordinary post-sweep restart events are saved but are not explicitly rejected by the sweep if `running=False`. [Sources: status](../Control/camera_keepalive_stream.py#L91), [stop](../Control/camera_keepalive_stream.py#L184), [sweep restart](../Scripts/run_single_sweep_remote.py#L350), [startup enforcement](../Scripts/run_long_test.py#L571).

Without a keepalive object, the camera-temperature script may briefly stream so `sensor_temperature` updates while it is read. With a keepalive object, sweeps request no temporary refresh to avoid a second stream on the same device. Internal-temperature reads are nonfatal: missing script, SSH trouble, or unavailable sensor records produce failure/error information in the sweep summary while image acquisition may continue. A wrapper status of `success` means JSON was received; inspect the payload's `errors` too. [Sources: wrapper](../Scripts/run_single_sweep_remote.py#L81), [refresh selection](../Scripts/run_single_sweep_remote.py#L282), [camera sensor reading](../Camera_scripts/read_camera_temperatures.py#L248).

## Stops, repeats, and cleanup

| Operator action | Scope and behavior |
|---|---|
| Create `STOP` inside the current test folder | Checked during pre-cool and at measurement loop boundaries. During measurement, marks `stopped_by_user`; it does not necessarily prevent the main repeat loop from starting the next repeat. During pre-cool it raises an error and records pre-cool failure. |
| Create `STOP_REPEAT` in `LOCAL_DATA_ROOT` (or configured stop filename) | Stops the active measurement at a loop boundary and prevents the next repeat. Also checked during pre-cool and between repeats. |
| Remove old stop files before a new intended sequence | Existing root-level repeat-stop file prevents any repeat from starting. The runner does not delete it automatically. |

Sources: [stop-file helpers](../Scripts/run_long_test.py#L96), [pre-cool checks](../Scripts/run_long_test.py#L352), [measurement checks](../Scripts/run_long_test.py#L646), [repeat-delay and main loop](../Scripts/run_long_test.py#L1006).

Stop files do not interrupt an image capture, transfer, recovery power-cycle, fixed settle, or boot wait in progress. Between repeats, the stop file is checked in chunks up to 60 s. [Sources: boot wait](../Scripts/run_long_test.py#L559), [recovery waits](../Scripts/run_long_test.py#L231), [repeat delay](../Scripts/run_long_test.py#L1006).

Normal and exception cleanup attempt, in order, keepalive stop, freezer off, lamp off, optional explicit camera off, then logger stop. Output-command failures are recorded or printed. These are attempts through software control, not physical feedback proving contacts opened. The logger's own stop/disconnect path also attempts camera power off, so setting `CAMERA_POWER_OFF_AT_TEST_END=False` does **not** reliably keep the camera on in the supplied implementation. Abrupt process termination, host power loss, or broken communication cannot be assumed to execute cleanup. [Sources: runner cleanup](../Scripts/run_long_test.py#L959), [logger stop](../Control/temperature_logger.py#L44), [controller disconnect](../Control/temperature_control.py#L168).

**Routine camera shutdown is by removing its power.** The owner confirms this as the accepted procedure for the rig, matching the relay-based shutdown in the runner. [Owner review R2](10-sources-and-maintenance.md#r2-owner-review-and-component-photos-29-october-2026), [camera power-off call](../Scripts/run_long_test.py#L988).

Ctrl-C raises `KeyboardInterrupt`, which bypasses the runner's `except Exception` status handlers. Its `finally` cleanup is still attempted, but a saved summary can remain `running` or `precooling` without a terminal status or `end_time`. Use the documented stop-file path for a normal recorded stop; the status left in a folder is not by itself proof that a process is still running. [Exception and cleanup path](../Scripts/run_long_test.py#L945).

## Failures and recovery

Storage is checked initially and after each attempted sweep against the default 5 GiB free threshold (calculated with 1024³ bytes). It is not a continuous disk monitor while a sweep is capturing/transferring. Low space raises an error. [Sources: storage check](../Scripts/run_long_test.py#L73), [post-attempt check](../Scripts/run_long_test.py#L919), [threshold](../Config/system_config.py#L142).

Ordinary sweep errors increment both failed-attempt count and consecutive failures. The default retry wait is 30 s; afterward the normal post-attempt sweep interval is also scheduled, so ordinary retry timing is longer than 30 s. Three consecutive ordinary failures abort by default. Successful capture resets the streak. [Sources: failure handling](../Scripts/run_long_test.py#L853), [rescheduling](../Scripts/run_long_test.py#L919), [defaults](../Config/system_config.py#L142).

Automatic camera recovery matches a small set of error strings: required-memory allocation, buffer-pool activation, `VIDIOC_REQBUFS`, and device/resource-busy errors. With recovery enabled, it stops keepalive, forces lamp off, powers **only the camera** off, waits 15 s by default, powers it on, waits 45 s, and restarts keepalive. The MCC logger and host process continue; freezer control is unchanged and the freezer is normally off during measurement. Up to three recoveries per test are configured by default; a successful recovery resets ordinary failure streak and schedules the next numbered sweep immediately. The failed attempt remains a failure; recovery does not recreate that same sweep index. [Sources: markers](../Scripts/run_long_test.py#L176), [recovery procedure](../Scripts/run_long_test.py#L191), [recovery decision](../Scripts/run_long_test.py#L864), [recovery defaults](../Config/system_config.py#L41).

Capture failure can leave images on the camera because transfer/removal happens only after the successful sweep block. Transfer verification checks expected filename existence, not checksums or PNG decodability. A transfer/removal failure can leave a local `sweep_summary.json` already marked `success` while the test-level event records that the attempt failed. Review both levels and file integrity before treating a partial sweep as usable. [Source: summary and transfer ordering](../Scripts/run_single_sweep_remote.py#L364).

## Physical procedure still to confirm

- Detailed installation checks for the enclosure, target, optics, filters, lamp, camera, thermocouples, and cabling, plus acceptance criteria for manual focus and per-run filter-position verification/calibration.
- Record any per-run departures from the usual probe map and the detailed attachment/contact method; the usual positions are now owner-confirmed above.
- Record ambient conditions and any additional thermal influences for each test; the owner-confirmed measurement heat sources are the camera and intermittent lamp operation with freezer power off.
- The required compressor minimum-off behavior. `FREEZER_MIN_OFF_TIME_S=600` is used by the dedicated relay test script; the long-run `freezer_on()` path does not enforce that delay. [Sources: manual protection setting](../Config/system_config.py#L76), [relay-test wait](../Scripts/test_freezer_relay.py#L87), [direct output control](../Control/temperature_control.py#L116).
- The required response to condensation, an out-of-range sensor, unavailable network, or a command that failed to switch an output. These procedures should come from the actual apparatus and operator experience.

For output files and interpretation of timestamps, see [Data and metadata](05-data-and-metadata.md).
