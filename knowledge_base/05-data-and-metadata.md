# Data and metadata

This chapter documents file structure and field meanings in the supplied acquisition code. It describes the schema and provenance needed to understand future datasets; it includes no individual test measurements, comparisons, or camera-development conclusions. All example folder names below are placeholders.

## Storage hierarchy

Long-test outputs are written under `LOCAL_DATA_ROOT`. Temporary image files are first written under `REMOTE_DATA_ROOT` on the camera, then copied to the acquisition host. The supplied local configuration selects `/home/henrik/Documents/FreezerTest_Results`; camera-side base configuration selects `/root/scripts/data`. These paths describe the copied acquisition profile, not the documentation folder on this computer. [Sources: local root](reference/local_config_snapshot.txt#L5), [remote root](../Config/system_config.py#L116), [sweep paths](../Scripts/run_single_sweep_remote.py#L214).

```text
<LOCAL_DATA_ROOT>/
├── STOP_REPEAT                         optional operator-created sequence-stop file
└── <camera_id>_repeat_001_<YYYYMMDD_HHMMSS>/
    ├── test_metadata.json
    ├── test_summary.json
    ├── test_log.jsonl
    ├── temperature_log.jsonl
    ├── STOP                            optional operator-created test-stop file
    └── sweep_0001_<YYYYMMDD_HHMMSS>/
        ├── sweep_summary.json
        ├── <YYYYMMDD_HHMMSS>_filter_1.png
        ├── <YYYYMMDD_HHMMSS>_filter_1.json
        ├── <YYYYMMDD_HHMMSS>_filter_2.png
        ├── <YYYYMMDD_HHMMSS>_filter_2.json
        ├── <YYYYMMDD_HHMMSS>_filter_3.png
        ├── <YYYYMMDD_HHMMSS>_filter_3.json
        ├── <YYYYMMDD_HHMMSS>_filter_4.png
        └── <YYYYMMDD_HHMMSS>_filter_4.json
```

For a single configured repeat, the long-test root omits `_repeat_001`: `<camera_id>_<timestamp>`. The standalone sweep command instead creates `manual_test_<timestamp>`. Camera IDs are sanitized to letters, digits, underscore, period, and hyphen; unsupported runs of characters become underscores. [Sources: camera-safe name](../Scripts/run_long_test.py#L62), [root naming](../Scripts/run_long_test.py#L429), [manual root](../Scripts/run_single_sweep_remote.py#L421).

JSON files contain one formatted JSON object. JSONL files contain one JSON object per line and may be read incrementally during a run. Expected files vary when filters are reconfigured; the current four-filter expectation follows sorted `FILTER_POSITIONS` keys rather than a separate hard-coded file list. [Sources: JSON/event writing](../Scripts/run_long_test.py#L104), [expected sweep files](../Scripts/run_single_sweep_remote.py#L179).

## Three levels of acquisition metadata

| Level | File | Primary use |
|---|---|---|
| Whole test/repeat | `test_metadata.json` | Camera/operator/context, repeat grouping, selected end/pre-cool configuration |
| Whole test/repeat | `test_summary.json` | Current/final state, sweep counts, event list, completion reason, recovery/cleanup records |
| Whole test/repeat | `test_log.jsonl` | Append-only sequence of pre-cool, sweep-attempt, stop, and end-condition events |
| Whole test/repeat | `temperature_log.jsonl` | External thermocouple records, output-state variables, and logger errors |
| One sweep | `sweep_summary.json` | Filter order/positions/exposures, trigger reason, timing, external-temperature snapshots and internal-temperature readings |
| One image | `<timestamp>_filter_<n>.json` | Capture device/format, requested/applied settings, image size and GStreamer command |
| One image | `<timestamp>_filter_<n>.png` | Monochrome captured image used by downstream analysis |

Sources: [test files](../Scripts/run_long_test.py#L451), [metadata object](../Scripts/run_long_test.py#L464), [test summary](../Scripts/run_long_test.py#L492), [sweep summary](../Scripts/run_single_sweep_remote.py#L224), [image metadata](../Camera_scripts/camera_control.py#L148).

## Test metadata fields

The initial `test_metadata.json` contains the following groups. It records selected settings, **not a complete snapshot of every effective configuration value**. [Source: object creation](../Scripts/run_long_test.py#L464).

| Fields | Meaning |
|---|---|
| `camera_id`, `operator`, `notes` | Explicit context from configuration; identity strings are not inferred from the captured image |
| `test_date`, `folder_created_at` | Date/time the repeat folder is created, before pre-cool; not measurement-start time |
| `test_duration_hours` | Configured time-mode duration, present even when temperature mode is selected |
| `test_end_mode`, `test_end_sensor`, `test_end_target_c`, `test_end_direction` | Chosen measurement termination rule |
| `test_end_safety_timeout_hours`, `test_end_required_consecutive_reads`, `test_end_final_sweep_enabled` | Temperature-mode deadline/confirmation/endpoint behavior |
| `repeat_index`, `repeat_count` | Position in configured repeat sequence and configured sequence length; a failed/stopped sequence may produce fewer folders |
| `repeat_group_id`, `repeat_group_start_date` | Link repeat folders to one sequence start |
| `precool_enabled`, `precool_sensor`, `precool_target_c` | Selected pre-cool configuration |
| `camera_keepalive_stream_enabled`, `camera_auto_recovery_enabled`, `camera_auto_recovery_max_per_test` | Selected runtime stream/recovery configuration |

The current runner derives `repeat_group_id` as `<safe_camera_id>_<YYYY-MM-DD>` from sequence start, then gives every repeat in that invocation the same ID. It is not guaranteed unique if two sequences for the same camera start on the same date. Older repair tools can produce different group formats, so do not infer precise grouping solely from a string pattern. [Sources: group ID](../Scripts/run_long_test.py#L69), [main sequence](../Scripts/run_long_test.py#L1025), [older repair format](../Scripts/repair_repeat_group_metadata.py#L137).

The owner uses the apparatus both for reproducibility across same-type camera units and for investigating design changes. Record a unique unit identity plus its tested revision/configuration, change under investigation, actual pre-cool threshold, verified wheel positions, and manual focus/setup state. Existing `camera_id` and `notes` can carry some of this context, but the runner does not create dedicated structured fields for every item. Do not treat the family name as a unique unit/revision ID or pool different revisions as an unchanged population. [Owner review R1](10-sources-and-maintenance.md#r1-owner-review-27-october-2026), [analysis comparisons](06-analysis-methodology.md#repeat-cycle-comparison).

Also record the **actual probe-placement map for each test**. The usual arrangement is shell probes 1–3, tray upper surface probe 4 and tray underside probe 5, but the owner can move probes between experiments. The numeric `probe_n` labels alone do not encode placement; the runner does not automatically store the map. Use the existing notes or an accompanying setup record. The PTFE/cage target, focus, halogen/reflector arrangement and camera/lamp-driven warming form part of that setup context. [Owner review R2](10-sources-and-maintenance.md#r2-owner-review-and-component-photos-29-october-2026).

## Test summary and event log

`test_summary.json` starts with status `initializing`, changes to `precooling` and `running`, then may finish as `completed`, `stopped_by_user`, or `aborted`. It stores `completed_sweeps` and `failed_sweeps`, initial storage information, configured limits, and an `events` array. Events are appended to both `test_log.jsonl` and the summary; the latter also gains `last_update` on each append. [Sources: initial summary](../Scripts/run_long_test.py#L492), [append mechanism](../Scripts/run_long_test.py#L109), [status transitions](../Scripts/run_long_test.py#L537), [termination](../Scripts/run_long_test.py#L945).

Additional fields appear as execution progresses:

- `precool_result`: assigned after completed or skipped pre-cool; successful pre-cool includes target/sensor/final temperature, duration, freezer on/off records, and last temperature record. A failed pre-cool appends a `precool_failed` event and raises before this field is assigned.
- `measurement_start_time`, `planned_end_time`, `planned_end_time_type`: measurement-phase timing, created after pre-cool, settle, camera boot, and optional stream startup.
- `end_time`, `completion_reason`: actual loop termination time/reason. `completed` can mean temperature target, time limit, temperature safety timeout, or maximum attempts; inspect the reason.
- `fatal_error`: text when the test aborts through an ordinary exception.
- `camera_keepalive_stream_events`, `camera_auto_recovery_count`, `camera_auto_recovery_events`: stream lifecycle and successful camera-recovery information recorded by the runner.
- `final_freezer_off_record`, `final_lamp_off_record`, `camera_power_off_record` or associated error fields: cleanup command outcomes/latest readbacks. They are not relay-contact feedback measurements.

Sources: [pre-cool results](../Scripts/run_long_test.py#L398), [pre-cool result assignment](../Scripts/run_long_test.py#L550), [measurement timing](../Scripts/run_long_test.py#L604), [completion/fatal errors](../Scripts/run_long_test.py#L932), [cleanup fields](../Scripts/run_long_test.py#L959).

An interrupted process can leave a nonterminal summary. In particular, Ctrl-C (`KeyboardInterrupt`) bypasses the `except Exception` status handler while still entering cleanup, so `status` can remain `precooling` or `running` without an `end_time`. Distinguish an incomplete record from a currently active process; compare the process state and logs rather than relying solely on that field. [Exception/cleanup handling](../Scripts/run_long_test.py#L945).

The JSONL event stream includes `event_type` for pre-cool, stop, and end-condition records. Sweep-attempt events instead include `sweep_index`, `trigger_reason`, `status`, and temperature/path/error fields; do not assume every log object has `event_type`. A sweep event is constructed as `started` but appended after the attempt, when it is usually `success` or `failed`. Its original `timestamp` is retained, so file append order/time and event timestamp have different meanings. [Sources: pre-cool event](../Scripts/run_long_test.py#L321), [sweep event construction](../Scripts/run_long_test.py#L806), [event append after attempt](../Scripts/run_long_test.py#L919).

## External temperature log schema

Normal `temperature_log.jsonl` records contain:

| Field | Type/meaning |
|---|---|
| `timestamp` | Host local ISO timestamp created before controller reads the enabled channels |
| `temperatures_c` | Object mapping enabled probe names to successfully returned temperatures in °C |
| `errors` | Object mapping probe names to individual MCC read error text |
| `lamp_state` | Controller's last commanded logical lamp state |
| `freezer_state` | Controller's last commanded logical freezer state |
| `camera_power_state` | Controller's last commanded camera state, possibly `null` before a command |
| `logger_timestamp` | Host local ISO timestamp added after `read_all()` returns |

Sources: [controller schema](../Control/temperature_control.py#L199), [logger record/write](../Control/temperature_logger.py#L79).

The supplied channel configuration enables K-type `probe_1` through `probe_5` (channels 0–4) and disables probes 6–8. A disabled probe is absent, not a zero-temperature measurement. An enabled probe whose read fails can be absent from `temperatures_c` and present in `errors`. The usual physical locations are now described in [the hardware map](02-hardware-and-connections.md#thermocouple-channels); sensor labels in a data file still require the actual run's placement record before that map is assumed. [Sources: channel configuration](../Config/temperature_config.py#L12), [per-channel read handling](../Control/temperature_control.py#L210).

If the whole logger iteration raises an exception, an error record has `logger_timestamp`, `logger_status="error"`, and `error`; it need not have normal temperatures or output-state keys. The logger continues attempting reads. The requested interval is 1 s, but sleep happens after reading/writing, so actual spacing includes operation time. The latest record supplied to sweep snapshots can also come from a relay wrapper's `read_all()` and may lack `logger_timestamp`. [Sources: logger loop](../Control/temperature_logger.py#L79), [relay wrappers](../Control/temperature_logger.py#L106).

Output states are software variables updated after output commands. They do not prove lamp light output, actual freezer compressor operation, physical contactor state, or camera boot completion. [Source: output methods](../Control/temperature_control.py#L108).

## Sweep summary schema

`sweep_summary.json` records:

| Fields | Meaning |
|---|---|
| `run_timestamp`, `sweep_name`, `sweep_index` | Host-generated name/time and numbered attempt; failed attempts can leave gaps among usable sweeps |
| `trigger_reason` | `time_interval`, `temperature_target_final`, or `temperature_safety_timeout_final` in the long runner; callers may supply another string |
| `camera_ip`, `remote_run_dir`, `local_run_dir` | Acquisition endpoint and original paths, which may become stale after data is moved |
| `status`, `error` | Capture/sweep-stage result; see transfer caveat below |
| `sweep_started_at`, `sweep_finished_at`, `sweep_duration_s` | Sweep-stage wall-clock endpoints and monotonic duration; transfer is timed separately |
| `transfer_started_at`, `transfer_finished_at`, `transfer_duration_s` | Added after successful copy, filename verification, and remote removal |
| `temperature_before_sweep`, `temperature_after_sweep` | Latest external logger/controller records around the sweep; the long runner fills the after-record after transfer |
| `homing`, `final_position` | Homing configuration/result and return-to-zero position when the successful path reaches those steps |
| `lamp` | Whether callbacks control it, warm-up duration, on/off flags |
| `filters` | Ordered list of successfully captured filters with position/exposure/path information |
| `camera_internal_temperature_readings` | Normally `before_capture` and `after_capture` read wrappers, including failure/disabled status if applicable |
| `camera_keepalive_stream_events` | Sweep-level stop/restart diagnostics |

Sources: [initial fields](../Scripts/run_single_sweep_remote.py#L224), [homing/lamp/filter fields](../Scripts/run_single_sweep_remote.py#L263), [timing and transfer fields](../Scripts/run_single_sweep_remote.py#L364), [after-sweep update](../Scripts/run_long_test.py#L835).

Each `filters` entry includes `filter_number`, `target_position`, `actual_position`, `exposure_time_absolute`, `remote_image_path`, and `remote_metadata_path`. The entry is appended only after that filter's remote capture call returns. Controller position is a motor-control coordinate, not an independently measured optical wavelength or alignment result. [Source: filter entry](../Scripts/run_single_sweep_remote.py#L314).

**Interpretation caveat:** the sweep-stage status becomes `success` before transfer. Copy, filename verification, or remote removal can later fail, while this summary remains successful and lacks transfer timing. Test-level event/counts may report failure in that case. Check both levels plus actual files. `verify_local_sweep()` establishes file existence only; it does not compare hashes, parse JSON, or decode PNGs. [Sources: transfer ordering](../Scripts/run_single_sweep_remote.py#L364), [filename check](../Scripts/run_single_sweep_remote.py#L179).

## Image format and sidecar schema

The supplied camera settings request 1296 × 1032, `GRAY8`, 24 frames/s, gain 0. The pipeline encodes a single camera buffer as PNG. The image is therefore a requested 8-bit grayscale acquisition product; do not describe it as a higher-bit-depth raw sensor dump. The hardware/driver's physical exposure units and radiometric response still need confirmation. [Sources: configuration](../Camera_scripts/camera_config.py#L2), [capture pipeline](../Camera_scripts/camera_control.py#L106).

Per-image JSON includes:

- Identity/storage: `timestamp`, `image_file`, `image_path`, `metadata_file`, `camera_device`.
- Requested image description: `width`, `height`, `pixel_format`, `image_encoding`, `actual_size_bytes`, `capture_status`.
- Requested controls: `requested_frame_rate`, `requested_exposure_time_absolute`, `requested_gain`.
- Readbacks as **strings**, retaining the `v4l2-ctl` output: `stream_parameters_before_capture`, `stream_parameters_after_capture`, `applied_exposure_before_capture`, `applied_exposure_after_capture`, `applied_gain_before_capture`, `applied_gain_after_capture`.
- Pipeline provenance: `gst_command` as argument list.
- Remote-entry additions: `capture_type="remote_trigger"`, `requested_exposure_from_cli`.

Sources: [sidecar object](../Camera_scripts/camera_control.py#L148), [remote-entry metadata](../Camera_scripts/capture_remote.py#L36).

The camera validates successful pipeline exit plus image existence/nonzero size before writing the sidecar. It does not decode the PNG to verify actual dimensions or image content. A failure after image creation can leave a PNG without its JSON sidecar. The image timestamp is recorded immediately before launching the capture pipeline; it is not a hardware exposure timestamp or an exact timestamp shared by every filter in a sweep. [Source: capture and metadata ordering](../Camera_scripts/camera_control.py#L126).

## Internal camera temperature schema

The sweep-level wrapper stores `label`, `host_timestamp`, `enabled`, and `status`, plus `stream_refresh_requested` when applicable. `status` may be `disabled`, `failed` with error text, or `success` with a `remote_payload`. Host wrapper success means the returned JSON was parsed, not that every internal sensor is valid. [Source: read wrapper](../Scripts/run_single_sweep_remote.py#L81).

`remote_payload` includes `timestamp`, `epoch`, `device`, `sensors`, and `errors`. Sources are the camera computer's `sensors -j` output and the V4L2 `sensor_temperature` control. lm-sensors entries contain chip/adapter/label/temperature and assigned friendly name. Names such as CPU, FPGA, or Sensor PCB are driver-based labels, not a verified wiring inventory. Preserve raw sensor keys to disambiguate them. [Sources: payload](../Camera_scripts/read_camera_temperatures.py#L335), [friendly mapping](../Camera_scripts/read_camera_temperatures.py#L20), [lm-sensors parsing](../Camera_scripts/read_camera_temperatures.py#L66).

The special `camera:sensor_temperature` entry contains `temp_c`, `name="Camera Sensor"`, `control_active`, and `stream_refresh` diagnostics. Code interprets its integer control as millidegrees, divides by 1000, and rounds to one decimal place. `control_active` reads the `temperature_control` control as a boolean when available. Exactly 20.0 °C adds `warning="exactly_20c_possible_default_or_stale_value"`; this is a possible-stale flag, not proof that every 20 °C observation is wrong. [Source: sensor conversion and warning](../Camera_scripts/read_camera_temperatures.py#L297).

These internal readings bracket a sweep and are not a continuous internal temperature log. External probe logging continues separately throughout pre-cool and measurement. Different sensor series should be aligned using their own timestamps and physical meaning rather than assuming identical sampling times.

## Timestamp conventions and alignment limits

| Timestamp/duration | Clock and meaning |
|---|---|
| Test/sweep folder timestamp | Acquisition-host `datetime.now()`, second precision, format `YYYYMMDD_HHMMSS` |
| Most host JSON timestamps | Acquisition-host local `datetime.now().isoformat(timespec="seconds")`; no explicit UTC offset |
| Image sidecar `timestamp` | Camera-computer local time immediately before GStreamer pipeline launch |
| Internal `host_timestamp` | Host time at the start of the internal-temperature wrapper |
| Internal payload `timestamp` / `epoch` | Camera computer's local ISO conversion / Unix seconds; recorded after its sensor collection |
| Durations such as `sweep_duration_s`, `transfer_duration_s`, pre-cool duration | Host `time.monotonic()` elapsed time, generally rounded to 0.001 s |
| Deadline scheduling | Host wall-clock datetimes, checked by the run loop |

Sources: [host helper](../Scripts/run_long_test.py#L59), [root names](../Scripts/run_long_test.py#L429), [sweep time/duration](../Scripts/run_single_sweep_remote.py#L214), [transfer time](../Scripts/run_single_sweep_remote.py#L390), [camera image time](../Camera_scripts/camera_control.py#L126), [internal timestamp](../Camera_scripts/read_camera_temperatures.py#L355).

No host/camera clock synchronization check or time-zone identifier is written by these acquisition functions. Clock agreement must be confirmed before assigning precise cross-device timing. Do not silently attach the documentation computer's time zone to historical acquisition timestamps. A sweep filename timestamp labels the start of the sweep; sequential filter images can be acquired later. `temperature_after_sweep` is filled after file transfer, while `sweep_finished_at` is set before transfer and before wheel shutdown completes. [Sources: acquisition ordering](../Scripts/run_single_sweep_remote.py#L376), [after-sweep snapshot](../Scripts/run_long_test.py#L835).

## Metadata repair and legacy folders

Two separate repair scripts exist; their grouping conventions differ:

| Script | Group convention and writes |
|---|---|
| `repair_repeat_group_metadata.py` | Infers groups by base name/timestamp/consecutive repeat index; uses `<base>_<anchor_YYYYMMDD_HHMMSS>` as group ID; writes repeat group/index/count/base into test metadata and summary |
| `repair_and_rename_repeat_folders.py` | Infers similar groups, reads camera ID from metadata/summary, uses `<camera_id>_<YYYY-MM-DD>`; updates metadata/summary and can rename root folders to camera-based names |

Sources: [older grouping](../Scripts/repair_repeat_group_metadata.py#L89), [older writes](../Scripts/repair_repeat_group_metadata.py#L137), [newer camera ID/grouping](../Scripts/repair_and_rename_repeat_folders.py#L108), [newer update and rename](../Scripts/repair_and_rename_repeat_folders.py#L164).

Both offer `--dry-run`. These reference commands inspect proposed changes and were not executed against result folders:

```bash
PYTHONPATH=. python3 Scripts/repair_repeat_group_metadata.py "/path/to/results/root" --dry-run
PYTHONPATH=. python3 Scripts/repair_and_rename_repeat_folders.py "/path/to/results/root" --dry-run --rename-folders
```

The scripts infer membership; they do not recover missing experimental intent. A missing repeat index can split a sequence. They identify folders by `test_summary.json` existence rather than enforcing completed status, and their JSON loader returns an empty object for unreadable/invalid JSON. Review proposals and retain originals before any applied repair. The rename helper checks target-name collisions, but is not a general metadata migration: it updates selected top-level fields, not every nested sweep/event/image path. It instructs users to rerun analysis afterward to refresh CSV paths. [Sources: folder detection/load](../Scripts/repair_and_rename_repeat_folders.py#L52), [index grouping](../Scripts/repair_and_rename_repeat_folders.py#L140), [selected writes](../Scripts/repair_and_rename_repeat_folders.py#L164), [collision checks](../Scripts/repair_and_rename_repeat_folders.py#L220), [rerun notice](../Scripts/repair_and_rename_repeat_folders.py#L269).

## Provenance gaps to resolve in the next version

The acquisition code does not automatically persist a Git commit, a complete merged configuration snapshot, a hardware serial-number inventory, per-run probe placement/calibration records, a schema version, clock synchronization status, environmental preparation details, or file checksums. The usual probe map and photographed component identities are available in this knowledge base, but are not automatically attached to each dataset. Per-filter requests, image readbacks, selected test settings, and events provide useful partial provenance. [Sources: test metadata fields](../Scripts/run_long_test.py#L464), [sweep fields](../Scripts/run_single_sweep_remote.py#L224), [image fields](../Camera_scripts/camera_control.py#L148).

For a reviewed operating procedure, see [Running the freezer test](04-running-the-test.md). Keep raw acquisition folders, later analysis products, and this general knowledge base distinguishable so a local AI can explain methods without treating individual results or stale profile values as universal facts.
