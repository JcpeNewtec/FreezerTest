import json
import shutil
import time
from datetime import datetime, timedelta
from pathlib import Path

from Scripts.run_single_sweep_remote import run_single_sweep
from Control.temperature_logger import TemperatureLogger
from Config.system_config import (
    LOCAL_DATA_ROOT,
    TEST_NAME,
    TEST_DURATION_HOURS,
    SWEEP_INTERVAL_SECONDS,
    MAX_SWEEPS,
    RETRY_DELAY_SECONDS,
    MAX_CONSECUTIVE_FAILURES,
    MINIMUM_FREE_GB,
)

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

def main():
    test_start = datetime.now()
    test_end = test_start + timedelta(hours=TEST_DURATION_HOURS)

    test_root_dir = Path(LOCAL_DATA_ROOT) / f"{TEST_NAME}_{test_start.strftime('%Y%m%d_%H%M%S')}"
    test_root_dir.mkdir(parents=True, exist_ok=True)
    stop_file_path = test_root_dir / "STOP"

    summary_path = test_root_dir / "test_summary.json"
    log_path = test_root_dir / "test_log.jsonl"
    temperature_log_path = test_root_dir / "temperature_log.jsonl"
    temp_logger = TemperatureLogger(log_path=temperature_log_path, interval_s=1.0)

    storage_info = check_storage(test_root_dir)

    test_summary = {
        "test_name": TEST_NAME,
        "test_root_dir": str(test_root_dir),
        "start_time": test_start.isoformat(timespec="seconds"),
        "planned_end_time": test_end.isoformat(timespec="seconds"),
        "test_duration_hours": TEST_DURATION_HOURS,
        "sweep_interval_seconds": SWEEP_INTERVAL_SECONDS,
        "max_sweeps": MAX_SWEEPS,
        "status": "running",
        "storage_at_start": storage_info,
        "completed_sweeps": 0,
        "failed_sweeps": 0,
        "events": [],
    }

    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(test_summary, f, indent=4)

    next_trigger_time = datetime.now()
    sweep_index = 1
    consecutive_failures = 0

    print(f"Test root directory: {test_root_dir}")
    print(f"Test start: {test_start}")
    print(f"Planned end: {test_end}")
    print(f"Sweep interval: {SWEEP_INTERVAL_SECONDS} seconds")
    print(f"Temperature log: {temperature_log_path}")
    print(f"Create this file to stop after the current sweep: {stop_file_path}")
    print("Starting temperature logger...")
    temp_logger.start()

    try:
        while datetime.now() < test_end and sweep_index <= MAX_SWEEPS:
            if stop_file_exists(test_root_dir):
                print("STOP file detected. Ending test after current cycle boundary.")
                stop_event = {
                    "timestamp": datetime.now().isoformat(timespec="seconds"),
                    "event_type": "stop_file_detected",
                    "stop_file_path": str(stop_file_path),
                    "status": "stopping",
                }

                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(stop_event) + "\n")

                test_summary["events"].append(stop_event)
                test_summary["status"] = "stopped_by_user"
                test_summary["end_time"] = datetime.now().isoformat(timespec="seconds")
                test_summary["stop_file_detected"] = True
                break

            if not should_trigger_sweep_by_time(next_trigger_time):
                time.sleep(1)
                continue

            latest_temp = temp_logger.get_latest_record()

            event = {
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "sweep_index": sweep_index,
                "trigger_reason": "time_interval",
                "status": "started",
                "latest_temperature_record": latest_temp,
            }

            try:
                print(f"\nStarting sweep {sweep_index}...")
                temperature_before_sweep = temp_logger.get_latest_record()
                
                print("Turning lamp ON...")
                lamp_on_record = temp_logger.lamp_on()
                time.sleep(1.0)
                
                try:
                    local_run_dir = run_single_sweep(
                        test_root_dir=test_root_dir,
                        sweep_index=sweep_index,
                        trigger_reason="time_interval",
                        temperature_before_sweep=temperature_before_sweep,
                        temperature_after_sweep=None,
                    )
                finally:
                    print("Turning lamp OFF...")
                    lamp_off_record = temp_logger.lamp_off()

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
                event["lamp_on_record"] = lamp_on_record
                event["lamp_off_record"] = lamp_off_record
                
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
                        f"Stopping test after {consecutive_failures} consecutive failures."
                    )

                print(f"Waiting {RETRY_DELAY_SECONDS} seconds before continuing...")
                time.sleep(RETRY_DELAY_SECONDS)

            finally:
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(event) + "\n")

                test_summary["events"].append(event)
                test_summary["last_update"] = datetime.now().isoformat(timespec="seconds")

                with open(summary_path, "w", encoding="utf-8") as f:
                    json.dump(test_summary, f, indent=4)

            sweep_index += 1
            next_trigger_time = datetime.now() + timedelta(seconds=SWEEP_INTERVAL_SECONDS)

            check_storage(test_root_dir)

        if test_summary["status"] == "running":
            test_summary["status"] = "completed"
            test_summary["end_time"] = datetime.now().isoformat(timespec="seconds")

    except Exception as e:
        test_summary["status"] = "aborted"
        test_summary["end_time"] = datetime.now().isoformat(timespec="seconds")
        test_summary["fatal_error"] = str(e)
        print(f"Long test aborted: {e}")

    finally:
        print("Stopping temperature logger...")
        temp_logger.stop()

        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(test_summary, f, indent=4)

        print(f"Final summary written to: {summary_path}")


if __name__ == "__main__":
    main()