#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test the production-like keepalive-stream workflow used by the long test.

This is the sequence we need because normal PNG capture cannot use /dev/video4
while the keepalive stream is active:

    start keepalive stream
    read sensor temperature while keepalive is active, without starting another stream
    stop keepalive stream
    capture one normal PNG frame
    restart keepalive stream
    read sensor temperature again, without starting another stream
    stop keepalive stream

Run from repo root:

    PYTHONPATH=. python3 Scripts/test_keepalive_pause_capture.py
"""

import argparse
import json
import subprocess
from datetime import datetime
from pathlib import Path

from Control.camera_keepalive_stream import CameraKeepaliveStream
from Scripts.run_single_sweep_remote import remote_read_camera_temperatures
from Config.system_config import (
    CAMERA_IP,
    CAMERA_USER,
    REMOTE_CAPTURE_SCRIPT,
    REMOTE_DATA_ROOT,
    LOCAL_DATA_ROOT,
    DEFAULT_EXPOSURE_TIME_ABSOLUTE,
)


def run_ssh(command: list[str], timeout: int = 90, check: bool = True):
    ssh_cmd = [
        "ssh",
        "-o", "BatchMode=yes",
        "-o", "ConnectTimeout=5",
        "-o", "ServerAliveInterval=5",
        "-o", "ServerAliveCountMax=2",
        f"{CAMERA_USER}@{CAMERA_IP}",
    ] + command

    result = subprocess.run(
        ssh_cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )

    if check and result.returncode != 0:
        raise RuntimeError(
            "SSH command failed.\n"
            f"Command: {' '.join(ssh_cmd)}\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )

    return result


def remote_capture(remote_output_path: str, exposure_time_absolute: int):
    result = run_ssh(
        [
            "python3",
            REMOTE_CAPTURE_SCRIPT,
            remote_output_path,
            str(exposure_time_absolute),
        ],
        timeout=90,
        check=False,
    )

    if result.returncode != 0:
        raise RuntimeError(
            "Capture failed after stopping keepalive stream.\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )

    return result.stdout.strip()


def copy_remote_dir_to_local(remote_dir: str, local_parent: Path):
    local_parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "scp",
        "-o", "BatchMode=yes",
        "-o", "ConnectTimeout=5",
        "-r",
        f"{CAMERA_USER}@{CAMERA_IP}:{remote_dir}",
        str(local_parent),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            "SCP failed.\n"
            f"Command: {' '.join(cmd)}\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )


def summarize_temperature(record: dict):
    print(json.dumps(record, indent=2))

    payload = record.get("remote_payload") or {}
    sensors = payload.get("sensors") or {}
    camera_sensor = sensors.get("camera:sensor_temperature")
    if camera_sensor:
        print(f"Camera Sensor: {camera_sensor.get('temp_c')} C")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--exposure", type=int, default=DEFAULT_EXPOSURE_TIME_ABSOLUTE)
    args = parser.parse_args()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    remote_run_dir = f"{REMOTE_DATA_ROOT}/keepalive_pause_capture_test_{timestamp}"
    remote_image_path = f"{remote_run_dir}/capture_after_keepalive_stop_{timestamp}.png"
    local_parent = Path(LOCAL_DATA_ROOT) / "keepalive_pause_capture_tests"

    keepalive = CameraKeepaliveStream()
    events = []

    print(f"Remote run dir: {remote_run_dir}")
    print(f"Local output parent: {local_parent}")

    try:
        run_ssh(["mkdir", "-p", remote_run_dir], timeout=10)

        print("Starting keepalive stream...")
        event = keepalive.start(reason="test_start")
        events.append(event)
        print(json.dumps(event, indent=2))
        if not event.get("running", False):
            raise RuntimeError("Keepalive stream did not start.")

        print("Reading camera temperatures while keepalive stream is active...")
        temp_before = remote_read_camera_temperatures(
            "keepalive_active_before_capture",
            stream_refresh=False,
        )
        summarize_temperature(temp_before)

        print("Stopping keepalive stream before capture...")
        event = keepalive.stop(reason="before_capture")
        events.append(event)
        print(json.dumps(event, indent=2))

        print("Capturing one normal image...")
        capture_stdout = remote_capture(remote_image_path, args.exposure)
        print(capture_stdout)

        print("Restarting keepalive stream after capture...")
        event = keepalive.start(reason="after_capture")
        events.append(event)
        print(json.dumps(event, indent=2))
        if not event.get("running", False):
            raise RuntimeError("Keepalive stream did not restart after capture.")

        print("Reading camera temperatures after keepalive restart...")
        temp_after = remote_read_camera_temperatures(
            "keepalive_active_after_capture",
            stream_refresh=False,
        )
        summarize_temperature(temp_after)

        print("Copying remote test folder back to host...")
        copy_remote_dir_to_local(remote_run_dir, local_parent)

        print("\nRESULT: SUCCESS")
        print("Pause/restart keepalive workflow works.")
        print(f"Local files should be under: {local_parent}")

    except Exception as exc:
        print("\nRESULT: FAILED")
        print(str(exc))

    finally:
        print("Stopping keepalive stream for cleanup...")
        try:
            event = keepalive.stop(reason="test_cleanup")
            events.append(event)
            print(json.dumps(event, indent=2))
        except Exception as exc:
            print(f"Cleanup stop failed: {exc}")


if __name__ == "__main__":
    main()
