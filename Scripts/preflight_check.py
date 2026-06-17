#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jun 17 13:48:57 2026

@author: jcpe
"""

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import shutil
import subprocess
import sys
import time
from pathlib import Path

from Config.system_config import (
    CAMERA_IP,
    CAMERA_USER,
    REMOTE_CAPTURE_SCRIPT,
    REMOTE_DATA_ROOT,
    LOCAL_DATA_ROOT,
    MINIMUM_FREE_GB,
)

from Config.temperature_config import HOST as MCC_IP

from Control.temperature_control import TemperatureController


SSH_OPTIONS = [
    "-o", "BatchMode=yes",
    "-o", "ConnectTimeout=5",
    "-o", "ServerAliveInterval=5",
    "-o", "ServerAliveCountMax=2",
]


class CheckResult:
    def __init__(self, name: str, passed: bool, message: str = ""):
        self.name = name
        self.passed = passed
        self.message = message


def run_command(cmd: list[str], timeout: int = 10) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def check_ping(name: str, ip: str) -> CheckResult:
    try:
        result = run_command(["ping", "-c", "2", "-W", "2", ip], timeout=6)
        if result.returncode == 0:
            return CheckResult(name, True, f"{ip} reachable")
        return CheckResult(name, False, result.stderr.strip() or result.stdout.strip())
    except Exception as e:
        return CheckResult(name, False, str(e))


def check_ssh_camera() -> CheckResult:
    cmd = [
        "ssh",
        *SSH_OPTIONS,
        f"{CAMERA_USER}@{CAMERA_IP}",
        "echo camera_ok",
    ]

    try:
        result = run_command(cmd, timeout=10)
        if result.returncode == 0 and "camera_ok" in result.stdout:
            return CheckResult("Camera SSH", True, "SSH OK")
        return CheckResult("Camera SSH", False, result.stderr.strip() or result.stdout.strip())
    except Exception as e:
        return CheckResult("Camera SSH", False, str(e))


def check_camera_scripts() -> CheckResult:
    remote_cmd = (
        f"test -f {REMOTE_CAPTURE_SCRIPT} "
        f"&& test -d {REMOTE_DATA_ROOT} "
        f"&& echo camera_scripts_ok"
    )

    cmd = [
        "ssh",
        *SSH_OPTIONS,
        f"{CAMERA_USER}@{CAMERA_IP}",
        remote_cmd,
    ]

    try:
        result = run_command(cmd, timeout=10)
        if result.returncode == 0 and "camera_scripts_ok" in result.stdout:
            return CheckResult("Camera scripts", True, "capture script and data folder OK")
        return CheckResult("Camera scripts", False, result.stderr.strip() or result.stdout.strip())
    except Exception as e:
        return CheckResult("Camera scripts", False, str(e))


def check_optional_camera_capture() -> CheckResult:
    timestamp = int(time.time())
    remote_path = f"{REMOTE_DATA_ROOT}/preflight_capture_{timestamp}.png"

    remote_cmd = (
        f"python3 {REMOTE_CAPTURE_SCRIPT} {remote_path} "
        f"&& test -f {remote_path} "
        f"&& rm -f {remote_path} {remote_path.replace('.png', '.json')} "
        f"&& echo camera_capture_ok"
    )

    cmd = [
        "ssh",
        *SSH_OPTIONS,
        f"{CAMERA_USER}@{CAMERA_IP}",
        remote_cmd,
    ]

    try:
        result = run_command(cmd, timeout=30)
        if result.returncode == 0 and "camera_capture_ok" in result.stdout:
            return CheckResult("Camera capture", True, "test capture OK")
        return CheckResult("Camera capture", False, result.stderr.strip() or result.stdout.strip())
    except Exception as e:
        return CheckResult("Camera capture", False, str(e))


def check_ticcmd_available() -> CheckResult:
    tic_path = shutil.which("ticcmd")
    if tic_path is None:
        return CheckResult("ticcmd", False, "ticcmd not found in PATH")
    return CheckResult("ticcmd", True, tic_path)


def check_tic_connected() -> CheckResult:
    try:
        result = run_command(["ticcmd", "--list"], timeout=10)
        if result.returncode == 0 and result.stdout.strip():
            return CheckResult("Tic connected", True, result.stdout.strip())
        return CheckResult("Tic connected", False, "ticcmd --list returned no devices")
    except Exception as e:
        return CheckResult("Tic connected", False, str(e))


def check_tic_status() -> CheckResult:
    try:
        result = run_command(["ticcmd", "-s"], timeout=10)
        if result.returncode == 0:
            return CheckResult("Tic status", True, "status read OK")
        return CheckResult("Tic status", False, result.stderr.strip() or result.stdout.strip())
    except Exception as e:
        return CheckResult("Tic status", False, str(e))


def check_storage() -> CheckResult:
    try:
        path = Path(LOCAL_DATA_ROOT)
        path.mkdir(parents=True, exist_ok=True)

        test_file = path / "preflight_write_test.tmp"
        test_file.write_text("preflight", encoding="utf-8")
        test_file.unlink()

        usage = shutil.disk_usage(path)
        free_gb = usage.free / (1024 ** 3)

        if free_gb < MINIMUM_FREE_GB:
            return CheckResult(
                "Storage",
                False,
                f"Only {free_gb:.2f} GB free, minimum is {MINIMUM_FREE_GB:.2f} GB",
            )

        return CheckResult("Storage", True, f"{free_gb:.2f} GB free")
    except Exception as e:
        return CheckResult("Storage", False, str(e))


def check_temperature_and_hall() -> CheckResult:
    controller = TemperatureController()

    try:
        controller.connect()
        data = controller.read_all()

        hall_msg = ""
        if hasattr(controller, "is_hall_active"):
            hall_active = controller.is_hall_active()
            hall_msg = f", hall_active={hall_active}"

        errors = data.get("errors", {})
        temps = data.get("temperatures_c", {})

        if errors:
            return CheckResult(
                "MCC temperature/Hall",
                False,
                f"temps={temps}, errors={errors}{hall_msg}",
            )

        return CheckResult(
            "MCC temperature/Hall",
            True,
            f"temps={temps}{hall_msg}",
        )

    except Exception as e:
        return CheckResult("MCC temperature/Hall", False, str(e))

    finally:
        try:
            controller.disconnect()
        except Exception:
            pass


def check_optional_lamp() -> CheckResult:
    controller = TemperatureController()

    try:
        controller.connect()

        if not hasattr(controller, "lamp_on") or not hasattr(controller, "lamp_off"):
            return CheckResult("Lamp", False, "TemperatureController has no lamp_on/lamp_off")

        controller.lamp_on()
        time.sleep(0.2)
        controller.lamp_off()

        return CheckResult("Lamp", True, "lamp toggled briefly")

    except Exception as e:
        return CheckResult("Lamp", False, str(e))

    finally:
        try:
            controller.lamp_off()
        except Exception:
            pass

        try:
            controller.disconnect()
        except Exception:
            pass


def print_results(results: list[CheckResult]) -> bool:
    all_passed = True

    print("\n=== PREFLIGHT CHECK RESULTS ===\n")

    for result in results:
        status = "PASS" if result.passed else "FAIL"
        print(f"[{status}] {result.name}: {result.message}")

        if not result.passed:
            all_passed = False

    print()

    if all_passed:
        print("PRE-FLIGHT PASSED")
    else:
        print("PRE-FLIGHT FAILED")

    return all_passed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--test-camera-capture",
        action="store_true",
        help="Run one remote camera capture and delete it afterwards.",
    )
    parser.add_argument(
        "--test-lamp",
        action="store_true",
        help="Briefly toggle the lamp. Do not use during an active run.",
    )

    args = parser.parse_args()

    results = [
        check_ping("Camera ping", CAMERA_IP),
        check_ping("MCC ping", MCC_IP),
        check_ssh_camera(),
        check_camera_scripts(),
        check_ticcmd_available(),
        check_tic_connected(),
        check_tic_status(),
        check_storage(),
        check_temperature_and_hall(),
    ]

    if args.test_camera_capture:
        results.append(check_optional_camera_capture())

    if args.test_lamp:
        results.append(check_optional_lamp())

    passed = print_results(results)

    if not passed:
        sys.exit(1)


if __name__ == "__main__":
    main()