#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Host-side control for a continuous camera keepalive stream.

The stream runs on the camera computer and writes frames to /dev/null. It is
used during long freezer tests to keep the camera video pipeline active between
normal image captures. Normal PNG capture uses the same V4L2 device, so the
keepalive stream must be stopped before each capture and restarted afterward.

This implementation is deliberately defensive around camera boot/restart:
- stale FreezerTest streams are removed;
- the V4L2 device is polled until it is actually queryable;
- stream startup is retried several times;
- failed-start events include the remote v4l2-ctl log and device diagnostics.
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
    CAMERA_KEEPALIVE_DEVICE_READY_TIMEOUT_S,
    CAMERA_KEEPALIVE_DEVICE_READY_POLL_S,
    CAMERA_KEEPALIVE_START_MAX_ATTEMPTS,
    CAMERA_KEEPALIVE_START_RETRY_DELAY_S,
    CAMERA_KEEPALIVE_LOG_TAIL_LINES,
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
        device_ready_timeout_s: float = CAMERA_KEEPALIVE_DEVICE_READY_TIMEOUT_S,
        device_ready_poll_s: float = CAMERA_KEEPALIVE_DEVICE_READY_POLL_S,
        start_max_attempts: int = CAMERA_KEEPALIVE_START_MAX_ATTEMPTS,
        start_retry_delay_s: float = CAMERA_KEEPALIVE_START_RETRY_DELAY_S,
        log_tail_lines: int = CAMERA_KEEPALIVE_LOG_TAIL_LINES,
    ):
        self.device = device
        self.stream_count = int(stream_count)
        self.startup_wait_s = float(startup_wait_s)
        self.pid_file = pid_file
        self.log_file = log_file
        self.kill_stale_on_start = bool(kill_stale_on_start)
        self.device_ready_timeout_s = float(device_ready_timeout_s)
        self.device_ready_poll_s = float(device_ready_poll_s)
        self.start_max_attempts = max(1, int(start_max_attempts))
        self.start_retry_delay_s = float(start_retry_delay_s)
        self.log_tail_lines = max(1, int(log_tail_lines))
        self.last_pid = None

    def _run_ssh(
        self,
        remote_shell_command: str,
        timeout: int = 30,
        check: bool = False,
    ) -> subprocess.CompletedProcess:
        # Multiline remote scripts are sent through stdin. Passing them after
        # `bash -lc` caused intermittent "bash: -c: option requires an argument"
        # failures in earlier versions of this project.
        ssh_cmd = [
            "ssh",
            "-o", "BatchMode=yes",
            "-o", "ConnectTimeout=5",
            "-o", "ServerAliveInterval=5",
            "-o", "ServerAliveCountMax=2",
            f"{CAMERA_USER}@{CAMERA_IP}",
            "bash",
            "-s",
        ]

        try:
            result = subprocess.run(
                ssh_cmd, input=remote_shell_command, capture_output=True,
                text=True, timeout=timeout,
            )
        except subprocess.TimeoutExpired as exc:
            # A boot-time SSH timeout is a failed attempt, so readiness/start
            # retries and the long-test power-cycle recovery can still run.
            result = subprocess.CompletedProcess(ssh_cmd, 124, "", str(exc))

        if check and result.returncode != 0:
            raise RuntimeError(
                "SSH command failed.\n"
                f"Command: {' '.join(ssh_cmd)} < remote shell script\n"
                f"stdout:\n{result.stdout}\n"
                f"stderr:\n{result.stderr}"
            )

        return result

    def _cleanup_stale(self) -> dict:
        """Remove stale FreezerTest keepalive processes and PID state."""
        pid_file_q = shlex.quote(self.pid_file)

        command = f"""
set +e
OLD_PID=''
if [ -f {pid_file_q} ]; then
    OLD_PID=$(cat {pid_file_q} 2>/dev/null || true)
    if [ -n "$OLD_PID" ]; then
        kill "$OLD_PID" 2>/dev/null || true
        i=0
        while kill -0 "$OLD_PID" 2>/dev/null && [ "$i" -lt 20 ]; do
            sleep 0.1
            i=$((i + 1))
        done
        if kill -0 "$OLD_PID" 2>/dev/null; then
            kill -9 "$OLD_PID" 2>/dev/null || true
        fi
    fi
    rm -f {pid_file_q}
fi
pkill -f 'v4l2-ctl.*--stream-to=/dev/null' 2>/dev/null || true
sleep 0.5
echo "OLD_PID=$OLD_PID"
"""
        result = self._run_ssh(command, timeout=10, check=False)
        return {
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "returncode": result.returncode,
        }

    def log_tail(self, lines: int | None = None) -> str:
        """Read the tail of the remote keepalive log without blocking."""
        log_file_q = shlex.quote(self.log_file)
        line_count = max(1, int(lines or self.log_tail_lines))
        command = f"tail -n {line_count} {log_file_q} 2>/dev/null || true\n"
        result = self._run_ssh(command, timeout=10, check=False)
        text = result.stdout.strip()
        if result.stderr.strip():
            text = f"{text}\n[stderr]\n{result.stderr.strip()}".strip()
        return text

    def diagnostics(self) -> dict:
        """Collect compact remote diagnostics after a failed stream start."""
        device_q = shlex.quote(self.device)
        log_file_q = shlex.quote(self.log_file)
        line_count = self.log_tail_lines

        command = f"""
set +e
echo '--- device ---'
ls -l {device_q} 2>&1 || true
echo '--- format ---'
v4l2-ctl -d {device_q} --get-fmt-video 2>&1 || true
echo '--- device users ---'
fuser -v {device_q} 2>&1 || true
echo '--- camera processes ---'
ps -eo pid,stat,args | grep -E 'v4l2-ctl|gst-launch|capture_remote|read_camera_temperatures' | grep -v grep || true
echo '--- memory ---'
grep -E 'MemAvailable|CmaTotal|CmaFree' /proc/meminfo 2>/dev/null || true
echo '--- keepalive log ---'
tail -n {line_count} {log_file_q} 2>/dev/null || true
"""
        result = self._run_ssh(command, timeout=15, check=False)
        return {
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "returncode": result.returncode,
        }

    def wait_until_device_ready(self) -> dict:
        """Wait until the configured V4L2 node exists and can be queried."""
        device_q = shlex.quote(self.device)
        start_monotonic = time.monotonic()
        attempts = []

        while True:
            command = f"""
set +e
if [ ! -e {device_q} ]; then
    echo 'DEVICE_MISSING'
    exit 2
fi
OUTPUT=$(v4l2-ctl -d {device_q} --get-fmt-video 2>&1)
RC=$?
if [ "$RC" -eq 0 ]; then
    echo 'DEVICE_READY'
    echo "$OUTPUT"
    exit 0
fi
echo 'DEVICE_NOT_READY'
echo "$OUTPUT"
exit "$RC"
"""
            result = self._run_ssh(command, timeout=10, check=False)
            attempt = {
                "elapsed_s": round(time.monotonic() - start_monotonic, 3),
                "returncode": result.returncode,
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
            }
            attempts.append(attempt)

            if result.returncode == 0 and "DEVICE_READY" in result.stdout:
                return {
                    "ready": True,
                    "elapsed_s": attempt["elapsed_s"],
                    "attempts": attempts,
                }

            elapsed_s = time.monotonic() - start_monotonic
            if elapsed_s >= self.device_ready_timeout_s:
                return {
                    "ready": False,
                    "elapsed_s": round(elapsed_s, 3),
                    "attempts": attempts,
                    "diagnostics": self.diagnostics(),
                }

            time.sleep(max(0.1, self.device_ready_poll_s))

    def status(self) -> dict:
        """Return whether the expected remote keepalive process is running."""
        pid_file_q = shlex.quote(self.pid_file)
        device_q = shlex.quote(self.device)

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
if ! kill -0 "$PID" 2>/dev/null; then
    echo "STATUS not_running $PID"
    exit 0
fi
STATE=$(ps -p "$PID" -o stat= 2>/dev/null | awk '{{print $1}}')
ARGS=$(ps -p "$PID" -o args= 2>/dev/null)
case "$STATE" in
    Z*|*Z*)
        echo "STATUS zombie $PID $STATE"
        ;;
    *)
        if printf '%s' "$ARGS" | grep -Fq 'v4l2-ctl' && printf '%s' "$ARGS" | grep -Fq {device_q}; then
            echo "STATUS running $PID"
        else
            echo "STATUS unexpected_process $PID $STATE $ARGS"
        fi
        ;;
esac
"""
        result = self._run_ssh(command, timeout=10, check=False)
        stdout = result.stdout.strip()
        parts = stdout.split()
        running = result.returncode == 0 and len(parts) >= 2 and parts[1] == "running"
        pid = parts[2] if running and len(parts) >= 3 else None

        return {
            "timestamp": iso_now(),
            "running": running,
            "pid": pid,
            "stdout": stdout,
            "stderr": result.stderr.strip(),
            "returncode": result.returncode,
        }

    def _start_once(self) -> dict:
        device_q = shlex.quote(self.device)
        pid_file_q = shlex.quote(self.pid_file)
        log_file_q = shlex.quote(self.log_file)
        stream_count = int(self.stream_count)

        command = f"""
set +e
rm -f {log_file_q}
nohup v4l2-ctl -d {device_q} \\
    --stream-mmap \\
    --stream-to=/dev/null \\
    --stream-count={stream_count} \\
    </dev/null > {log_file_q} 2>&1 &
PID=$!
echo "$PID" > {pid_file_q}
echo "$PID"
"""
        result = self._run_ssh(command, timeout=15, check=False)
        pid = result.stdout.strip().splitlines()[-1] if result.stdout.strip() else None
        self.last_pid = pid
        return {
            "pid": pid,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "returncode": result.returncode,
        }

    def start(self, reason: str = "manual") -> dict:
        """Start the keepalive stream with device-readiness checks and retries."""
        start_time = iso_now()
        cleanup = None

        if self.kill_stale_on_start:
            cleanup = self._cleanup_stale()

        readiness = self.wait_until_device_ready()
        attempts = []

        if not readiness.get("ready", False):
            return {
                "timestamp": start_time,
                "event_type": "camera_keepalive_start",
                "reason": reason,
                "device": self.device,
                "stream_count": self.stream_count,
                "startup_wait_s": self.startup_wait_s,
                "running": False,
                "status": {"running": False, "stdout": "device_not_ready"},
                "cleanup": cleanup,
                "device_readiness": readiness,
                "attempts": attempts,
                "log_tail": self.log_tail(),
                "diagnostics": self.diagnostics(),
            }

        last_start_result = None
        last_status = None

        for attempt_number in range(1, self.start_max_attempts + 1):
            if attempt_number > 1:
                self._cleanup_stale()

            start_result = self._start_once()
            last_start_result = start_result

            time.sleep(max(0.0, self.startup_wait_s))
            status = self.status()
            last_status = status
            log_tail = self.log_tail()

            attempt_event = {
                "attempt": attempt_number,
                "pid": start_result.get("pid"),
                "start_stdout": start_result.get("stdout", ""),
                "start_stderr": start_result.get("stderr", ""),
                "start_returncode": start_result.get("returncode"),
                "status": status,
                "log_tail": log_tail,
            }
            attempts.append(attempt_event)

            if status.get("running", False):
                return {
                    "timestamp": iso_now(),
                    "event_type": "camera_keepalive_start",
                    "reason": reason,
                    "device": self.device,
                    "stream_count": self.stream_count,
                    "startup_wait_s": self.startup_wait_s,
                    "pid": status.get("pid") or start_result.get("pid"),
                    "running": True,
                    "status": status,
                    "cleanup": cleanup,
                    "device_readiness": readiness,
                    "attempt_count": attempt_number,
                    "attempts": attempts,
                    "stdout": start_result.get("stdout", ""),
                    "stderr": start_result.get("stderr", ""),
                    "returncode": start_result.get("returncode"),
                }

            self._cleanup_stale()

            if attempt_number < self.start_max_attempts:
                time.sleep(max(0.0, self.start_retry_delay_s))

        return {
            "timestamp": iso_now(),
            "event_type": "camera_keepalive_start",
            "reason": reason,
            "device": self.device,
            "stream_count": self.stream_count,
            "startup_wait_s": self.startup_wait_s,
            "pid": (last_start_result or {}).get("pid"),
            "running": False,
            "status": last_status or {"running": False},
            "cleanup": cleanup,
            "device_readiness": readiness,
            "attempt_count": len(attempts),
            "attempts": attempts,
            "stdout": (last_start_result or {}).get("stdout", ""),
            "stderr": (last_start_result or {}).get("stderr", ""),
            "returncode": (last_start_result or {}).get("returncode"),
            "log_tail": self.log_tail(),
            "diagnostics": self.diagnostics(),
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
