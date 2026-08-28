#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test whether normal image capture works while a continuous camera stream is running.

Run from repo root:

    PYTHONPATH=. python3 Scripts/test_capture_with_keepalive_stream.py

This script:
    - starts a long v4l2-ctl stream on the camera to /dev/null
    - tries one normal capture through /root/scripts/capture_remote.py
    - copies the result back to the host
    - stops the keepalive stream

Interpretation:
    If capture succeeds:
        We can probably keep the camera streaming during the full long test.

    If capture fails with device busy:
        We should implement pause-stream / capture / restart-stream during each sweep.
"""

import argparse
import subprocess
import time
from datetime import datetime
from pathlib import Path

from Config.system_config import (
    CAMERA_IP,
    CAMERA_USER,
    REMOTE_CAPTURE_SCRIPT,
    REMOTE_DATA_ROOT,
    LOCAL_DATA_ROOT,
    DEFAULT_EXPOSURE_TIME_ABSOLUTE,
    REMOTE_CAMERA_TEMPERATURE_STREAM_DEVICE,
)


REMOTE_PID_FILE = "/tmp/freezertest_keepalive_stream.pid"
REMOTE_LOG_FILE = "/tmp/freezertest_keepalive_stream.log"


def run_ssh(command: list[str], timeout: int = 30, check: bool = True):
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
            f"SSH command failed.\n"
            f"Command: {' '.join(ssh_cmd)}\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )

    return result


def start_keepalive_stream(stream_device: str, stream_count: int):
    print(f"Starting keepalive stream on {stream_device}...")

    remote_cmd = f"""
set -e
rm -f {REMOTE_PID_FILE}
rm -f {REMOTE_LOG_FILE}

nohup v4l2-ctl -d {stream_device} \\
    --stream-mmap \\
    --stream-to=/dev/null \\
    --stream-count={stream_count} \\
    > {REMOTE_LOG_FILE} 2>&1 &

echo $! > {REMOTE_PID_FILE}
cat {REMOTE_PID_FILE}
"""

    result = run_ssh(["bash", "-lc", remote_cmd], timeout=10)
    pid = result.stdout.strip().splitlines()[-1]
    print(f"Remote stream PID: {pid}")

    return pid


def stop_keepalive_stream():
    print("Stopping keepalive stream...")

    remote_cmd = f"""
if [ -f {REMOTE_PID_FILE} ]; then
    PID=$(cat {REMOTE_PID_FILE})
    kill "$PID" 2>/dev/null || true
    sleep 0.5
    kill -9 "$PID" 2>/dev/null || true
    rm -f {REMOTE_PID_FILE}
fi
"""

    run_ssh(["bash", "-lc", remote_cmd], timeout=10, check=False)


def check_keepalive_stream():
    remote_cmd = f"""
if [ ! -f {REMOTE_PID_FILE} ]; then
    echo "PID_FILE_MISSING"
    exit 1
fi

PID=$(cat {REMOTE_PID_FILE})

if kill -0 "$PID" 2>/dev/null; then
    echo "RUNNING pid=$PID"
    exit 0
else
    echo "NOT_RUNNING pid=$PID"
    echo "--- stream log tail ---"
    tail -n 30 {REMOTE_LOG_FILE} 2>/dev/null || true
    exit 1
fi
"""

    result = run_ssh(["bash", "-lc", remote_cmd], timeout=10, check=False)

    print(result.stdout.strip())

    if result.returncode != 0:
        raise RuntimeError(
            "Keepalive stream is not running.\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )


def remote_capture(remote_output_path: str, exposure_time_absolute: int):
    print("Trying normal capture while keepalive stream is running...")

    command = [
        "python3",
        REMOTE_CAPTURE_SCRIPT,
        remote_output_path,
        str(exposure_time_absolute),
    ]

    result = run_ssh(command, timeout=90, check=False)

    if result.returncode != 0:
        raise RuntimeError(
            "Capture failed while keepalive stream was running.\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )

    print("Capture stdout:")
    print(result.stdout.strip())

    return result


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
            f"SCP failed.\n"
            f"Command: {' '.join(cmd)}\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )


def print_stream_log_tail():
    print("\nRemote keepalive stream log tail:")
    result = run_ssh(
        ["bash", "-lc", f"tail -n 40 {REMOTE_LOG_FILE} 2>/dev/null || true"],
        timeout=10,
        check=False,
    )
    print(result.stdout.strip())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--stream-device",
        default=REMOTE_CAMERA_TEMPERATURE_STREAM_DEVICE,
        help="Camera device to stream from.",
    )
    parser.add_argument(
        "--stream-count",
        type=int,
        default=100000000,
        help="Large frame count so the stream stays active during capture.",
    )
    parser.add_argument(
        "--startup-wait-s",
        type=float,
        default=2.0,
        help="Wait after starting stream before trying capture.",
    )
    parser.add_argument(
        "--exposure",
        type=int,
        default=DEFAULT_EXPOSURE_TIME_ABSOLUTE,
        help="Exposure_time_absolute for the test capture.",
    )
    args = parser.parse_args()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    remote_run_dir = f"{REMOTE_DATA_ROOT}/keepalive_capture_test_{timestamp}"
    remote_image_path = f"{remote_run_dir}/capture_with_keepalive_{timestamp}.png"
    local_parent = Path(LOCAL_DATA_ROOT) / "keepalive_capture_tests"

    print(f"Remote run dir: {remote_run_dir}")
    print(f"Local output parent: {local_parent}")

    try:
        run_ssh(["mkdir", "-p", remote_run_dir], timeout=10)

        start_keepalive_stream(
            stream_device=args.stream_device,
            stream_count=args.stream_count,
        )

        print(f"Waiting {args.startup_wait_s} s for stream startup...")
        time.sleep(args.startup_wait_s)

        check_keepalive_stream()

        remote_capture(
            remote_output_path=remote_image_path,
            exposure_time_absolute=args.exposure,
        )

        print("Copying remote test folder back to host...")
        copy_remote_dir_to_local(remote_run_dir, local_parent)

        print("\nRESULT: SUCCESS")
        print("Normal capture worked while the keepalive stream was running.")
        print(f"Local files should be under: {local_parent}")

    except Exception as e:
        print("\nRESULT: FAILED")
        print(str(e))
        print("\nThis likely means the capture device cannot be used by two streaming processes at once.")
        print("If the error mentions busy/resource unavailable, we should implement pause-stream / capture / restart-stream.")

    finally:
        print_stream_log_tail()
        stop_keepalive_stream()


if __name__ == "__main__":
    main()
