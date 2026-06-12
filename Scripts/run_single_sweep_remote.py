import json
import subprocess
import time
from datetime import datetime
from pathlib import Path

from Control.filterwheel_control import FilterwheelController
from Config.system_config import (
    TIC_SERIAL,
    FILTER_POSITIONS,
    FILTERWHEEL_STEP_MODE,
    FILTERWHEEL_CURRENT_LIMIT_MA,
    FILTERWHEEL_MAX_SPEED,
    FILTERWHEEL_STARTING_SPEED,
    FILTERWHEEL_MAX_ACCEL,
    FILTERWHEEL_MAX_DECEL,
    FILTERWHEEL_POSITION_TOLERANCE,
    FILTERWHEEL_SETTLE_TIME_S,
    FILTERWHEEL_MOVE_TIMEOUT_S,
    CAMERA_IP,
    CAMERA_USER,
    REMOTE_CAPTURE_SCRIPT,
    REMOTE_DATA_ROOT,
    LOCAL_DATA_ROOT,
    FILTERWHEEL_HOME_ENABLED,
    FILTERWHEEL_HOME_SEARCH_DIRECTION,
    FILTERWHEEL_HOME_FAST_STEP,
    FILTERWHEEL_HOME_SLOW_STEP,
    FILTERWHEEL_HOME_MAX_STEPS,
    DEFAULT_EXPOSURE_TIME_ABSOLUTE,
    FILTER_EXPOSURE_TIME_ABSOLUTE,
)


def iso_now():
    return datetime.now().isoformat(timespec="seconds")


def run_ssh(command: list[str], timeout: int = 30) -> subprocess.CompletedProcess:
    ssh_cmd = [
        "ssh",
        "-o", "BatchMode=yes",
        "-o", "ConnectTimeout=5",
        "-o", "ServerAliveInterval=5",
        "-o", "ServerAliveCountMax=2",
        f"{CAMERA_USER}@{CAMERA_IP}",
    ] + command
    result = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError(
            f"SSH command failed.\n"
            f"Command: {' '.join(ssh_cmd)}\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )
    return result


def remote_capture(remote_output_path: str, exposure_time_absolute: int | None = None):
    command = ["python3", REMOTE_CAPTURE_SCRIPT, remote_output_path]

    if exposure_time_absolute is not None:
        command.append(str(exposure_time_absolute))

    result = run_ssh(command, timeout=60)
    return result.stdout.strip()


def remote_make_dir(remote_dir: str):
    run_ssh(["mkdir", "-p", remote_dir])


def remote_remove_dir(remote_dir: str):
    run_ssh(["rm", "-rf", remote_dir])


def copy_remote_dir_to_local(remote_dir: str, local_dir: Path):
    local_dir.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "scp",
        "-o", "BatchMode=yes",
        "-o", "ConnectTimeout=5",
        "-r",
        f"{CAMERA_USER}@{CAMERA_IP}:{remote_dir}",
        str(local_dir.parent),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"SCP failed.\n"
            f"Command: {' '.join(cmd)}\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )


def expected_sweep_files(run_timestamp: str) -> list[str]:
    files = []
    for filter_number in sorted(FILTER_POSITIONS.keys()):
        files.append(f"{run_timestamp}_filter_{filter_number}.png")
        files.append(f"{run_timestamp}_filter_{filter_number}.json")
    files.append("sweep_summary.json")
    return files


def verify_local_sweep(local_run_dir: Path, run_timestamp: str):
    missing = []
    for filename in expected_sweep_files(run_timestamp):
        if not (local_run_dir / filename).exists():
            missing.append(filename)

    if missing:
        raise RuntimeError(
            "Batch transfer completed but some files are missing locally:\n"
            + "\n".join(missing)
        )


def run_single_sweep(
    test_root_dir: Path,
    sweep_index: int,
    trigger_reason: str = "time_interval",
    temperature_before_sweep: dict | None = None,
    temperature_after_sweep: dict | None = None,
    hall_reader=None,
    home_filterwheel: bool = False,
    lamp_on_callback=None,
    lamp_off_callback=None,
    lamp_warmup_s: float = 1,
):
    run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    sweep_name = f"sweep_{sweep_index:04d}_{run_timestamp}"

    remote_run_dir = f"{REMOTE_DATA_ROOT}/{sweep_name}"
    local_run_dir = test_root_dir / sweep_name
    local_run_dir.mkdir(parents=True, exist_ok=True)

    sweep_started_at = iso_now()
    sweep_start_monotonic = time.monotonic()

    sweep_summary = {
        "run_timestamp": run_timestamp,
        "sweep_name": sweep_name,
        "sweep_index": sweep_index,
        "trigger_reason": trigger_reason,
        "camera_ip": CAMERA_IP,
        "remote_run_dir": remote_run_dir,
        "local_run_dir": str(local_run_dir),
        "filters": [],
        "status": "started",
        "sweep_started_at": sweep_started_at,
        "temperature_before_sweep": temperature_before_sweep,
        "temperature_after_sweep": temperature_after_sweep,
    }

    filterwheel = FilterwheelController(
        tic_serial=TIC_SERIAL,
        filter_positions=FILTER_POSITIONS,
        step_mode=FILTERWHEEL_STEP_MODE,
        current_limit_ma=FILTERWHEEL_CURRENT_LIMIT_MA,
        max_speed=FILTERWHEEL_MAX_SPEED,
        starting_speed=FILTERWHEEL_STARTING_SPEED,
        max_accel=FILTERWHEEL_MAX_ACCEL,
        max_decel=FILTERWHEEL_MAX_DECEL,
        position_tolerance=FILTERWHEEL_POSITION_TOLERANCE,
        settle_time_s=FILTERWHEEL_SETTLE_TIME_S,
        move_timeout_s=FILTERWHEEL_MOVE_TIMEOUT_S,
    )

    try:
        print(f"Creating remote run folder: {remote_run_dir}")
        remote_make_dir(remote_run_dir)

        print("Initializing filterwheel...")
        filterwheel.initialize(set_zero_here=False)
        
        if home_filterwheel:
            if hall_reader is None:
                raise RuntimeError("home_filterwheel=True but no hall_reader was provided.")
        
            homing_result = filterwheel.home_with_hall(
                is_hall_active=hall_reader,
                search_direction=FILTERWHEEL_HOME_SEARCH_DIRECTION,
                fast_step=FILTERWHEEL_HOME_FAST_STEP,
                slow_step=FILTERWHEEL_HOME_SLOW_STEP,
                max_steps=FILTERWHEEL_HOME_MAX_STEPS,
            )
            
            sweep_summary["homing"] = {
                "enabled": True,
                **homing_result,
            }
        else:
            sweep_summary["homing"] = {"enabled": False}
            
        lamp_was_turned_on = False
        
        if lamp_on_callback is not None:
            print("Turning lamp ON for image capture...")
            lamp_on_callback()
            lamp_was_turned_on = True
            time.sleep(lamp_warmup_s)
        
        sweep_summary["lamp"] = {
            "controlled_by_sweep": lamp_on_callback is not None,
            "warmup_s": lamp_warmup_s,
            "on_before_first_capture": lamp_was_turned_on,
        }

        try:
            for filter_number in sorted(FILTER_POSITIONS.keys()):
                print(f"Moving to filter {filter_number}...")
                target_position = filterwheel.move_to_filter(filter_number)
                actual_position = filterwheel.get_current_position()
        
                exposure_time_absolute = FILTER_EXPOSURE_TIME_ABSOLUTE.get(
                    filter_number,
                    DEFAULT_EXPOSURE_TIME_ABSOLUTE,
                )
        
                remote_image_path = f"{remote_run_dir}/{run_timestamp}_filter_{filter_number}.png"
        
                print(
                    f"Capturing image for filter {filter_number} "
                    f"with exposure {exposure_time_absolute}..."
                )
                remote_capture(
                    remote_image_path,
                    exposure_time_absolute=exposure_time_absolute,
                )
        
                sweep_summary["filters"].append({
                    "filter_number": filter_number,
                    "target_position": target_position,
                    "actual_position": actual_position,
                    "exposure_time_absolute": exposure_time_absolute,
                    "remote_image_path": remote_image_path,
                    "remote_metadata_path": remote_image_path.replace(".png", ".json"),
                })
        
        finally:
            if lamp_was_turned_on and lamp_off_callback is not None:
                print("Turning lamp OFF after final capture...")
                lamp_off_callback()
                sweep_summary["lamp"]["off_after_capture"] = True

        print("Returning filterwheel to zero...")
        filterwheel.return_to_zero()
        final_position = filterwheel.get_current_position()

        sweep_summary["final_position"] = final_position
        sweep_summary["status"] = "success"

    except Exception as e:
        sweep_summary["status"] = "failed"
        sweep_summary["error"] = str(e)
        raise

    finally:
        sweep_finished_at = iso_now()
        sweep_duration_s = time.monotonic() - sweep_start_monotonic

        sweep_summary["sweep_finished_at"] = sweep_finished_at
        sweep_summary["sweep_duration_s"] = round(sweep_duration_s, 3)

        print("Shutting down filterwheel...")
        filterwheel.shutdown()

        local_summary_path = local_run_dir / "sweep_summary.json"
        with open(local_summary_path, "w", encoding="utf-8") as f:
            json.dump(sweep_summary, f, indent=4)

    transfer_started_at = iso_now()
    transfer_start_monotonic = time.monotonic()

    print("Copying remote sweep folder to local disk...")
    copy_remote_dir_to_local(remote_run_dir, local_run_dir)

    print("Verifying local files...")
    verify_local_sweep(local_run_dir, run_timestamp)

    print("Removing remote sweep folder...")
    remote_remove_dir(remote_run_dir)

    transfer_finished_at = iso_now()
    transfer_duration_s = time.monotonic() - transfer_start_monotonic

    local_summary_path = local_run_dir / "sweep_summary.json"
    with open(local_summary_path, "r", encoding="utf-8") as f:
        sweep_summary = json.load(f)

    sweep_summary["transfer_started_at"] = transfer_started_at
    sweep_summary["transfer_finished_at"] = transfer_finished_at
    sweep_summary["transfer_duration_s"] = round(transfer_duration_s, 3)

    with open(local_summary_path, "w", encoding="utf-8") as f:
        json.dump(sweep_summary, f, indent=4)

    print(f"Sweep saved locally in: {local_run_dir}")

    return local_run_dir


def main():
    test_root_dir = Path(LOCAL_DATA_ROOT) / f"manual_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    test_root_dir.mkdir(parents=True, exist_ok=True)
    run_single_sweep(test_root_dir=test_root_dir, sweep_index=1)


if __name__ == "__main__":
    main()