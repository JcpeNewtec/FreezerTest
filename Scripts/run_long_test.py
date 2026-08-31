#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import shutil
import time
from datetime import datetime, timedelta
from pathlib import Path
import re

from Scripts.run_single_sweep_remote import run_single_sweep
from Control.temperature_logger import TemperatureLogger
from Control.camera_keepalive_stream import CameraKeepaliveStream

from Config.system_config import (
    LOCAL_DATA_ROOT,
    TEST_NAME,
    TEST_DURATION_HOURS,
    SWEEP_INTERVAL_SECONDS,
    MAX_SWEEPS,
    RETRY_DELAY_SECONDS,
    MAX_CONSECUTIVE_FAILURES,
    MINIMUM_FREE_GB,
    FILTERWHEEL_HOME_ENABLED,
    LAMP_WARMUP_S,
    CAMERA_POWER_CONTROL_ENABLED,
    CAMERA_POWER_BOOT_WAIT_S,
    CAMERA_POWER_OFF_AT_TEST_END,
    CAMERA_KEEPALIVE_STREAM_ENABLED,
    CAMERA_ID,
    TEST_OPERATOR,
    TEST_NOTES,

    FREEZER_CONTROL_ENABLED,
    PRECOOL_BEFORE_TEST_ENABLED,
    PRECOOL_SENSOR_NAME,
    PRECOOL_TARGET_C,
    PRECOOL_TIMEOUT_HOURS,
    PRECOOL_POLL_INTERVAL_S,
    PRECOOL_SETTLE_AFTER_FREEZER_OFF_S,

    REPEAT_TEST_COUNT,
    REPEAT_DELAY_BETWEEN_TESTS_S,
    REPEAT_CONTINUE_AFTER_FAILURE,
    REPEAT_STOP_FILE_NAME,
)


def iso_now() -> str:
    return datetime.now().isoformat(timespec="seconds")

def safe_name(value: str) -> str:
    text = str(value).strip()
    text = re.sub(r"[^A-Za-z0-9_.-]+", "_", text)
    text = text.strip("_")
    return text or "unknown_camera"


def repeat_group_id_for_start(start_time: datetime) -> str:
    return f"{safe_name(CAMERA_ID)}_{start_time.date().isoformat()}"


def check_storage(path: Path, minimum_free_gb: float = MINIMUM_FREE_GB):
    path.mkdir(parents=True, exist_ok=True)

    usage = shutil.disk_usage(path)
    free_gb = usage.free / (1024 ** 3)

    if free_gb < minimum_free_gb:
        raise RuntimeError(
            f"Low disk space on {path}. Only {free_gb:.2f} GB free."
        )

    return {
        "total_bytes": usage.total,
        "used_bytes": usage.used,
        "free_bytes": usage.free,
        "free_gb": free_gb,
    }


def should_trigger_sweep_by_time(next_trigger_time: datetime) -> bool:
    return datetime.now() >= next_trigger_time


def stop_file_exists(test_root_dir: Path) -> bool:
    return (test_root_dir / "STOP").exists()


def repeat_stop_file_exists() -> bool:
    return (Path(LOCAL_DATA_ROOT) / REPEAT_STOP_FILE_NAME).exists()


def write_json(path: Path, data: dict):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def append_event(log_path: Path, test_summary: dict, event: dict, summary_path: Path):
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")

    test_summary["events"].append(event)
    test_summary["last_update"] = iso_now()
    write_json(summary_path, test_summary)


def get_temperature_from_record(record: dict | None, sensor_name: str):
    if not record:
        return None

    temperatures = record.get("temperatures_c") or {}

    if sensor_name not in temperatures:
        return None

    try:
        return float(temperatures[sensor_name])
    except (TypeError, ValueError):
        return None


def wait_for_first_temperature_record(
    temp_logger: TemperatureLogger,
    sensor_name: str,
    timeout_s: float = 60.0,
):
    start = time.monotonic()

    while time.monotonic() - start < timeout_s:
        record = temp_logger.get_latest_record()
        value = get_temperature_from_record(record, sensor_name)

        if value is not None:
            return record, value

        time.sleep(1.0)

    raise RuntimeError(
        f"No valid temperature value for {sensor_name} after {timeout_s:.0f} s."
    )


def precool_freezer(
    temp_logger: TemperatureLogger,
    test_root_dir: Path,
    log_path: Path,
    summary_path: Path,
    test_summary: dict,
):
    if not PRECOOL_BEFORE_TEST_ENABLED:
        event = {
            "timestamp": iso_now(),
            "event_type": "precool_skipped",
            "reason": "PRECOOL_BEFORE_TEST_ENABLED is False",
        }
        append_event(log_path, test_summary, event, summary_path)
        return event

    if not FREEZER_CONTROL_ENABLED:
        event = {
            "timestamp": iso_now(),
            "event_type": "precool_skipped",
            "reason": "FREEZER_CONTROL_ENABLED is False",
        }
        append_event(log_path, test_summary, event, summary_path)
        return event

    print(
        f"Pre-cooling freezer until {PRECOOL_SENSOR_NAME} <= "
        f"{PRECOOL_TARGET_C:.2f} C"
    )

    precool_start_monotonic = time.monotonic()
    precool_start_time = iso_now()
    timeout_s = float(PRECOOL_TIMEOUT_HOURS) * 3600.0

    start_event = {
        "timestamp": precool_start_time,
        "event_type": "precool_started",
        "sensor": PRECOOL_SENSOR_NAME,
        "target_c": PRECOOL_TARGET_C,
        "timeout_hours": PRECOOL_TIMEOUT_HOURS,
    }
    append_event(log_path, test_summary, start_event, summary_path)

    try:
        # Camera and lamp must be off while freezer is cooling.
        try:
            print("Ensuring lamp is OFF before pre-cool...")
            temp_logger.lamp_off()
        except Exception as e:
            print(f"Could not explicitly turn lamp OFF before pre-cool: {e}")

        if CAMERA_POWER_CONTROL_ENABLED:
            try:
                print("Ensuring camera power is OFF before pre-cool...")
                temp_logger.camera_power_off()
            except Exception as e:
                print(f"Could not explicitly turn camera OFF before pre-cool: {e}")

        print("Turning freezer ON...")
        freezer_on_record = temp_logger.freezer_on()

        last_print_time = 0.0
        last_record = None
        last_temp = None

        while True:
            if stop_file_exists(test_root_dir):
                raise RuntimeError("STOP file detected during pre-cool.")

            if repeat_stop_file_exists():
                raise RuntimeError(
                    f"{REPEAT_STOP_FILE_NAME} detected during pre-cool."
                )

            elapsed_s = time.monotonic() - precool_start_monotonic

            if elapsed_s > timeout_s:
                raise RuntimeError(
                    f"Pre-cool timeout after {elapsed_s / 3600.0:.2f} h. "
                    f"Last {PRECOOL_SENSOR_NAME} value: {last_temp}"
                )

            record = temp_logger.get_latest_record()
            value = get_temperature_from_record(record, PRECOOL_SENSOR_NAME)

            if value is not None:
                last_record = record
                last_temp = value

                if elapsed_s - last_print_time >= 30.0:
                    print(
                        f"Pre-cool: {PRECOOL_SENSOR_NAME} = "
                        f"{value:.2f} C, target = {PRECOOL_TARGET_C:.2f} C"
                    )
                    last_print_time = elapsed_s

                if value <= PRECOOL_TARGET_C:
                    break

            time.sleep(PRECOOL_POLL_INTERVAL_S)

        print("Pre-cool target reached. Turning freezer OFF...")
        freezer_off_record = temp_logger.freezer_off()

        if PRECOOL_SETTLE_AFTER_FREEZER_OFF_S > 0:
            print(
                f"Waiting {PRECOOL_SETTLE_AFTER_FREEZER_OFF_S} s "
                "after freezer OFF..."
            )
            time.sleep(PRECOOL_SETTLE_AFTER_FREEZER_OFF_S)

        result = {
            "timestamp": iso_now(),
            "event_type": "precool_completed",
            "sensor": PRECOOL_SENSOR_NAME,
            "target_c": PRECOOL_TARGET_C,
            "final_temperature_c": last_temp,
            "duration_s": round(time.monotonic() - precool_start_monotonic, 3),
            "freezer_on_record": freezer_on_record,
            "freezer_off_record": freezer_off_record,
            "last_temperature_record": last_record,
        }
        append_event(log_path, test_summary, result, summary_path)
        return result

    except Exception as e:
        print(f"Pre-cool failed: {e}")
        try:
            temp_logger.freezer_off()
        except Exception:
            pass

        event = {
            "timestamp": iso_now(),
            "event_type": "precool_failed",
            "error": str(e),
            "duration_s": round(time.monotonic() - precool_start_monotonic, 3),
        }
        append_event(log_path, test_summary, event, summary_path)
        raise


def create_test_folder(repeat_index: int, repeat_count: int) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    folder_prefix = safe_name(CAMERA_ID)

    if repeat_count > 1:
        folder_name = f"{folder_prefix}_repeat_{repeat_index:03d}_{timestamp}"
    else:
        folder_name = f"{folder_prefix}_{timestamp}"

    return Path(LOCAL_DATA_ROOT) / folder_name


def run_one_test(
    repeat_index: int,
    repeat_count: int,
    repeat_group_id: str,
) -> dict:
    
    folder_created_at = datetime.now()
    test_root_dir = create_test_folder(repeat_index, repeat_count)
    test_root_dir.mkdir(parents=True, exist_ok=True)

    stop_file_path = test_root_dir / "STOP"
    summary_path = test_root_dir / "test_summary.json"
    log_path = test_root_dir / "test_log.jsonl"
    temperature_log_path = test_root_dir / "temperature_log.jsonl"

    temp_logger = TemperatureLogger(
        log_path=temperature_log_path,
        interval_s=1.0,
    )
    camera_keepalive_stream = None

    storage_info = check_storage(test_root_dir)

    metadata_path = test_root_dir / "test_metadata.json"
    test_metadata = {
        "camera_id": CAMERA_ID,
        "test_date": folder_created_at.date().isoformat(),
        "folder_created_at": folder_created_at.isoformat(timespec="seconds"),
        "test_duration_hours": TEST_DURATION_HOURS,
        "operator": TEST_OPERATOR,
        "notes": TEST_NOTES,
        "repeat_index": repeat_index,
        "repeat_count": repeat_count,
        "repeat_group_id": repeat_group_id,
        "repeat_group_start_date": repeat_group_id.split("_")[-1],
        "precool_enabled": PRECOOL_BEFORE_TEST_ENABLED,
        "precool_sensor": PRECOOL_SENSOR_NAME,
        "precool_target_c": PRECOOL_TARGET_C,
        "camera_keepalive_stream_enabled": CAMERA_KEEPALIVE_STREAM_ENABLED,
    }
    write_json(metadata_path, test_metadata)

    test_summary = {
        "test_name": safe_name(CAMERA_ID),
        "test_root_dir": str(test_root_dir),
        "folder_created_at": folder_created_at.isoformat(timespec="seconds"),
        "test_duration_hours": TEST_DURATION_HOURS,
        "sweep_interval_seconds": SWEEP_INTERVAL_SECONDS,
        "max_sweeps": MAX_SWEEPS,
        "status": "initializing",
        "storage_at_start": storage_info,
        "completed_sweeps": 0,
        "failed_sweeps": 0,
        "events": [],
        "metadata_path": str(metadata_path),
        "repeat_index": repeat_index,
        "repeat_count": repeat_count,
        "repeat_group_id": repeat_group_id,
        "repeat_group_start_date": repeat_group_id.split("_")[-1],
        "precool_enabled": PRECOOL_BEFORE_TEST_ENABLED,
        "precool_sensor": PRECOOL_SENSOR_NAME,
        "precool_target_c": PRECOOL_TARGET_C,
        "camera_keepalive_stream_enabled": CAMERA_KEEPALIVE_STREAM_ENABLED,
        "camera_keepalive_stream_events": [],
    }
    write_json(summary_path, test_summary)

    print(f"\n=== Repeat {repeat_index}/{repeat_count} ===")
    print(f"Test root directory: {test_root_dir}")
    print(f"Temperature log: {temperature_log_path}")
    print(f"Create this file to stop this test after current cycle boundary: {stop_file_path}")
    print(
        f"Create this file to stop the repeat sequence: "
        f"{Path(LOCAL_DATA_ROOT) / REPEAT_STOP_FILE_NAME}"
    )

    try:
        print("Starting temperature logger...")
        temp_logger.start()

        wait_for_first_temperature_record(
            temp_logger=temp_logger,
            sensor_name=PRECOOL_SENSOR_NAME,
            timeout_s=60.0,
        )

        test_summary["status"] = "precooling"
        write_json(summary_path, test_summary)

        precool_result = precool_freezer(
            temp_logger=temp_logger,
            test_root_dir=test_root_dir,
            log_path=log_path,
            summary_path=summary_path,
            test_summary=test_summary,
        )
        test_summary["precool_result"] = precool_result

        if CAMERA_POWER_CONTROL_ENABLED:
            print("Turning camera power ON...")
            camera_power_on_record = temp_logger.camera_power_on()
            test_summary["camera_power_on_record"] = camera_power_on_record
            write_json(summary_path, test_summary)

            print(
                f"Waiting {CAMERA_POWER_BOOT_WAIT_S} s for camera "
                "boot/stabilization..."
            )
            time.sleep(CAMERA_POWER_BOOT_WAIT_S)

        if CAMERA_KEEPALIVE_STREAM_ENABLED:
            print("Starting camera keepalive stream for measurement phase...")
            camera_keepalive_stream = CameraKeepaliveStream()
            keepalive_start_event = camera_keepalive_stream.start(
                reason=f"repeat_{repeat_index:03d}_measurement_start"
            )
            test_summary["camera_keepalive_stream_events"].append(keepalive_start_event)
            write_json(summary_path, test_summary)

            if not keepalive_start_event.get("running", False):
                raise RuntimeError(
                    "Camera keepalive stream did not start. "
                    f"Event: {keepalive_start_event}"
                )

        measurement_start = datetime.now()
        test_end = measurement_start + timedelta(hours=TEST_DURATION_HOURS)

        test_summary["status"] = "running"
        test_summary["measurement_start_time"] = measurement_start.isoformat(
            timespec="seconds"
        )
        test_summary["planned_end_time"] = test_end.isoformat(timespec="seconds")
        write_json(summary_path, test_summary)

        print(f"Measurement start: {measurement_start}")
        print(f"Planned measurement end: {test_end}")
        print(f"Sweep interval: {SWEEP_INTERVAL_SECONDS} seconds")

        next_trigger_time = datetime.now()
        sweep_index = 1
        consecutive_failures = 0

        while datetime.now() < test_end and sweep_index <= MAX_SWEEPS:
            if stop_file_exists(test_root_dir):
                print("STOP file detected. Ending test after current cycle boundary.")

                stop_event = {
                    "timestamp": iso_now(),
                    "event_type": "stop_file_detected",
                    "stop_file_path": str(stop_file_path),
                    "status": "stopping",
                }
                append_event(log_path, test_summary, stop_event, summary_path)

                test_summary["status"] = "stopped_by_user"
                test_summary["end_time"] = iso_now()
                test_summary["stop_file_detected"] = True
                write_json(summary_path, test_summary)
                break

            if repeat_stop_file_exists():
                print(f"{REPEAT_STOP_FILE_NAME} detected. Ending repeat sequence.")

                stop_event = {
                    "timestamp": iso_now(),
                    "event_type": "repeat_stop_file_detected",
                    "stop_file_path": str(Path(LOCAL_DATA_ROOT) / REPEAT_STOP_FILE_NAME),
                    "status": "stopping",
                }
                append_event(log_path, test_summary, stop_event, summary_path)

                test_summary["status"] = "stopped_by_user"
                test_summary["end_time"] = iso_now()
                test_summary["repeat_stop_file_detected"] = True
                write_json(summary_path, test_summary)
                break

            if not should_trigger_sweep_by_time(next_trigger_time):
                time.sleep(1)
                continue

            latest_temp = temp_logger.get_latest_record()

            event = {
                "timestamp": iso_now(),
                "sweep_index": sweep_index,
                "trigger_reason": "time_interval",
                "status": "started",
                "latest_temperature_record": latest_temp,
            }

            try:
                print(f"\nStarting sweep {sweep_index}...")

                temperature_before_sweep = temp_logger.get_latest_record()

                local_run_dir = run_single_sweep(
                    test_root_dir=test_root_dir,
                    sweep_index=sweep_index,
                    trigger_reason="time_interval",
                    temperature_before_sweep=temperature_before_sweep,
                    temperature_after_sweep=None,
                    hall_reader=temp_logger.is_hall_active,
                    home_filterwheel=FILTERWHEEL_HOME_ENABLED,
                    lamp_on_callback=temp_logger.lamp_on,
                    lamp_off_callback=temp_logger.lamp_off,
                    lamp_warmup_s=LAMP_WARMUP_S,
                    camera_keepalive_stream=camera_keepalive_stream,
                )

                temperature_after_sweep = temp_logger.get_latest_record()

                sweep_summary_path = local_run_dir / "sweep_summary.json"

                with open(sweep_summary_path, "r", encoding="utf-8") as f:
                    sweep_summary = json.load(f)

                sweep_summary["temperature_after_sweep"] = temperature_after_sweep

                with open(sweep_summary_path, "w", encoding="utf-8") as f:
                    json.dump(sweep_summary, f, indent=4)

                event["temperature_before_sweep"] = temperature_before_sweep
                event["temperature_after_sweep"] = temperature_after_sweep
                event["status"] = "success"
                event["local_run_dir"] = str(local_run_dir)
                event["sweep_summary_path"] = str(sweep_summary_path)

                consecutive_failures = 0
                test_summary["completed_sweeps"] += 1

            except Exception as e:
                event["status"] = "failed"
                event["error"] = str(e)

                consecutive_failures += 1
                test_summary["failed_sweeps"] += 1

                print(f"Sweep {sweep_index} failed: {e}")

                if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                    raise RuntimeError(
                        f"Stopping test after {consecutive_failures} "
                        "consecutive failures."
                    )

                print(f"Waiting {RETRY_DELAY_SECONDS} seconds before continuing...")
                time.sleep(RETRY_DELAY_SECONDS)

            finally:
                append_event(log_path, test_summary, event, summary_path)

                sweep_index += 1
                next_trigger_time = datetime.now() + timedelta(
                    seconds=SWEEP_INTERVAL_SECONDS
                )

                check_storage(test_root_dir)

        if test_summary["status"] == "running":
            test_summary["status"] = "completed"
            test_summary["end_time"] = iso_now()

    except Exception as e:
        test_summary["status"] = "aborted"
        test_summary["end_time"] = iso_now()
        test_summary["fatal_error"] = str(e)
        print(f"Long test aborted: {e}")

        if not REPEAT_CONTINUE_AFTER_FAILURE:
            raise

    finally:
        if camera_keepalive_stream is not None:
            try:
                print("Stopping camera keepalive stream...")
                keepalive_stop_event = camera_keepalive_stream.stop(
                    reason=f"repeat_{repeat_index:03d}_test_end"
                )
                test_summary["camera_keepalive_stream_events"].append(keepalive_stop_event)
            except Exception as e:
                print(f"Failed to stop camera keepalive stream: {e}")
                test_summary["camera_keepalive_stream_stop_error"] = str(e)

        # Always remove cooling first.
        try:
            print("Ensuring freezer is OFF...")
            freezer_off_record = temp_logger.freezer_off()
            test_summary["final_freezer_off_record"] = freezer_off_record
        except Exception as e:
            print(f"Failed to turn freezer OFF: {e}")
            test_summary["final_freezer_off_error"] = str(e)

        try:
            print("Ensuring lamp is OFF...")
            lamp_off_record = temp_logger.lamp_off()
            test_summary["final_lamp_off_record"] = lamp_off_record
        except Exception as e:
            print(f"Failed to turn lamp OFF: {e}")
            test_summary["final_lamp_off_error"] = str(e)

        if CAMERA_POWER_CONTROL_ENABLED and CAMERA_POWER_OFF_AT_TEST_END:
            try:
                print("Turning camera power OFF...")
                camera_power_off_record = temp_logger.camera_power_off()
                test_summary["camera_power_off_record"] = camera_power_off_record
            except Exception as e:
                print(f"Failed to turn camera power OFF: {e}")
                test_summary["camera_power_off_error"] = str(e)

        print("Stopping temperature logger...")
        temp_logger.stop()

        write_json(summary_path, test_summary)
        print(f"Final summary written to: {summary_path}")

    return test_summary


def wait_between_repeats(seconds: float):
    if seconds <= 0:
        return

    print(f"Waiting {seconds} s before next repeat...")

    remaining = int(seconds)

    while remaining > 0:
        if repeat_stop_file_exists():
            print(f"{REPEAT_STOP_FILE_NAME} detected during repeat delay.")
            return

        step = min(60, remaining)
        time.sleep(step)
        remaining -= step
        print(f"Repeat delay: {remaining} s remaining")


def main():
    repeat_count = max(1, int(REPEAT_TEST_COUNT))
    sequence_start_time = datetime.now()
    repeat_group_id = repeat_group_id_for_start(sequence_start_time)
    print(f"Repeat group ID: {repeat_group_id}")

    print(f"Configured repeat count: {repeat_count}")

    for repeat_index in range(1, repeat_count + 1):
        if repeat_stop_file_exists():
            print(f"{REPEAT_STOP_FILE_NAME} exists. Not starting next repeat.")
            break

        try:
            run_one_test(
                repeat_index=repeat_index,
                repeat_count=repeat_count,
                repeat_group_id=repeat_group_id,
            )
        except Exception as e:
            print(f"Repeat {repeat_index} failed: {e}")

            if not REPEAT_CONTINUE_AFTER_FAILURE:
                print("Stopping repeat sequence because REPEAT_CONTINUE_AFTER_FAILURE is False.")
                break

        if repeat_index < repeat_count:
            wait_between_repeats(REPEAT_DELAY_BETWEEN_TESTS_S)

    print("Repeat sequence finished.")


if __name__ == "__main__":
    main()