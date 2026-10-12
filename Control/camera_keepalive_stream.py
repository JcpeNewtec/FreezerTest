#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Host-side control for a continuous camera keepalive stream.

The stream runs on the camera computer and writes frames to /dev/null. It is
used during long freezer tests to keep the camera video pipeline active between
normal image captures. Normal PNG capture uses the same V4L2 device, so the
keepalive stream must be stopped before each capture and restarted afterward.
"""

from __future__ import annotations

import shlex
import subprocess
import time
from datetime import datetime

from Config.system_config import (
    CAMERA_IP,
    CAMERA_USER,
    CAMERA_KEEPALIVE_STREAM_DEVICE,
    CAMERA_KEEPALIVE_STREAM_COUNT,
    CAMERA_KEEPALIVE_STREAM_STARTUP_WAIT_S,
    CAMERA_KEEPALIVE_STREAM_PID_FILE,
    CAMERA_KEEPALIVE_STREAM_LOG_FILE,
    CAMERA_KEEPALIVE_KILL_STALE_ON_START,
)


def iso_now() -> str:
    return datetime.now().isoformat(timespec="seconds")


class CameraKeepaliveStream:
    """Manage a remote v4l2-ctl stream process on the camera computer."""

    def __init__(
        self,
        device: str = CAMERA_KEEPALIVE_STREAM_DEVICE,
        stream_count: int = CAMERA_KEEPALIVE_STREAM_COUNT,
        startup_wait_s: float = CAMERA_KEEPALIVE_STREAM_STARTUP_WAIT_S,
        pid_file: str = CAMERA_KEEPALIVE_STREAM_PID_FILE,
        log_file: str = CAMERA_KEEPALIVE_STREAM_LOG_FILE,
        kill_stale_on_start: bool = CAMERA_KEEPALIVE_KILL_STALE_ON_START,
    ):
        self.device = device
        self.stream_count = int(stream_count)
        self.startup_wait_s = float(startup_wait_s)
        self.pid_file = pid_file
        self.log_file = log_file
        self.kill_stale_on_start = bool(kill_stale_on_start)
        self.last_pid = None

    def _run_ssh(
        self,
        remote_shell_command: str,
        timeout: int = 30,
        check: bool = False,
    ) -> subprocess.CompletedProcess:
        ssh_cmd = [
            "ssh",
            "-o", "BatchMode=yes",
            "-o", "ConnectTimeout=5",
            "-o", "ServerAliveInterval=5",
            "-o", "ServerAliveCountMax=2",
            f"{CAMERA_USER}@{CAMERA_IP}",
            "bash",
            "-lc",
            remote_shell_command,
        ]

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

    def status(self) -> dict:
        """Return whether the remote keepalive process appears to be running."""
        pid_file_q = shlex.quote(self.pid_file)

        command = f"""
if [ ! -f {pid_file_q} ]; then
    echo 'STATUS missing_pid_file'
    exit 0
fi
PID=$(cat {pid_file_q} 2>/dev/null || true)
if [ -z "$PID" ]; then
    echo 'STATUS empty_pid_file'
    exit 0
fi
if kill -0 "$PID" 2>/dev/null; then
    echo "STATUS running $PID"
else
    echo "STATUS not_running $PID"
fi
"""
        result = self._run_ssh(command, timeout=10, check=False)
        stdout = result.stdout.strip()
        parts = stdout.split()
        running = len(parts) >= 2 and parts[1] == "running"
        pid = parts[2] if running and len(parts) >= 3 else None

        return {
            "timestamp": iso_now(),
            "running": running,
            "pid": pid,
            "stdout": stdout,
            "stderr": result.stderr.strip(),
            "returncode": result.returncode,
        }

    def start(self, reason: str = "manual") -> dict:
        """Start the remote keepalive stream and wait briefly for it to run."""
        device_q = shlex.quote(self.device)
        pid_file_q = shlex.quote(self.pid_file)
        log_file_q = shlex.quote(self.log_file)
        stream_count = int(self.stream_count)
        kill_stale = "1" if self.kill_stale_on_start else "0"

        command = f"""
set +e
if [ "{kill_stale}" = "1" ]; then
    if [ -f {pid_file_q} ]; then
        OLD_PID=$(cat {pid_file_q} 2>/dev/null || true)
        if [ -n "$OLD_PID" ]; then
            kill "$OLD_PID" 2>/dev/null || true
            sleep 0.5
            kill -9 "$OLD_PID" 2>/dev/null || true
        fi
        rm -f {pid_file_q}
    fi
    # Clear old FreezerTest/v4l2-ctl keepalive streams that may have lost
    # their PID file. This deliberately matches only v4l2-ctl streams to
    # /dev/null, not the camera UI service.
    pkill -f 'v4l2-ctl.*--stream-to=/dev/null' 2>/dev/null || true
fi
rm -f {log_file_q}
nohup v4l2-ctl -d {device_q} \
    --stream-mmap \
    --stream-to=/dev/null \
    --stream-count={stream_count} \
    > {log_file_q} 2>&1 &
PID=$!
echo "$PID" > {pid_file_q}
echo "$PID"
"""

        result = self._run_ssh(command, timeout=15, check=False)
        pid = result.stdout.strip().splitlines()[-1] if result.stdout.strip() else None
        self.last_pid = pid

        time.sleep(max(0.0, self.startup_wait_s))
        status = self.status()

        return {
            "timestamp": iso_now(),
            "event_type": "camera_keepalive_start",
            "reason": reason,
            "device": self.device,
            "stream_count": self.stream_count,
            "startup_wait_s": self.startup_wait_s,
            "pid": pid,
            "running": status.get("running", False),
            "status": status,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "returncode": result.returncode,
        }

    def stop(self, reason: str = "manual") -> dict:
        """Stop the remote keepalive stream if it is running."""
        pid_file_q = shlex.quote(self.pid_file)

        command = f"""
set +e
STOPPED=0
FORCED=0
PID=''
if [ -f {pid_file_q} ]; then
    PID=$(cat {pid_file_q} 2>/dev/null || true)
    if [ -n "$PID" ]; then
        kill "$PID" 2>/dev/null || true

        # Prefer a clean exit so the V4L2 driver can release mmap/DMA
        # buffers normally. Wait up to about 3 seconds before SIGKILL.
        i=0
        while kill -0 "$PID" 2>/dev/null && [ "$i" -lt 30 ]; do
            sleep 0.1
            i=$((i + 1))
        done

        if kill -0 "$PID" 2>/dev/null; then
            kill -9 "$PID" 2>/dev/null || true
            FORCED=1
            sleep 0.2
        fi
        STOPPED=1
    fi
    rm -f {pid_file_q}
fi
echo "PID=$PID STOPPED=$STOPPED FORCED=$FORCED"
"""

        result = self._run_ssh(command, timeout=10, check=False)
        status = self.status()

        return {
            "timestamp": iso_now(),
            "event_type": "camera_keepalive_stop",
            "reason": reason,
            "device": self.device,
            "running_after_stop": status.get("running", False),
            "status": status,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "returncode": result.returncode,
        }
