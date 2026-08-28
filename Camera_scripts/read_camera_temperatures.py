#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Read internal camera/system temperatures on the camera computer.

This script is intended to be run on the camera over SSH from the host PC.
It prints one JSON object to stdout and does not require any arguments.

Example on camera:
    python3 /root/scripts/read_camera_temperatures.py --device /dev/video4
"""

import argparse
import json
import re
import subprocess
import time
from datetime import datetime


DRIVER_FRIENDLY_NAMES = {
    "k10temp": "CPU",
    "coretemp": "CPU",
    "amdgpu": "GPU",
    "nouveau": "GPU",
    "nvidia": "GPU",
    "axi_hwmon": "FPGA",
    "lm73": "Sensor PCB",
    "jc42": "PCB",
}

_BUS_TYPES = ("isa", "pci", "i2c", "acpi", "spi")
_CHIP_DRIVER_RE = re.compile(r"^(.+?)-(?:" + "|".join(_BUS_TYPES) + r")-")


def _driver_name(chip: str) -> str:
    match = _CHIP_DRIVER_RE.match(chip)
    return match.group(1) if match else chip


def _friendly_for_driver(driver: str) -> str:
    if driver in DRIVER_FRIENDLY_NAMES:
        return DRIVER_FRIENDLY_NAMES[driver]
    stripped = re.sub(r"\d+$", "", driver)
    return DRIVER_FRIENDLY_NAMES.get(stripped, driver)


def _apply_friendly_names(result: dict) -> dict:
    groups = {}

    for sensor_key, info in result.items():
        friendly = _friendly_for_driver(_driver_name(info["chip"]))
        groups.setdefault(friendly, []).append(sensor_key)

    for friendly, keys in groups.items():
        multiple = len(keys) > 1
        for index, sensor_key in enumerate(sorted(keys), start=1):
            result[sensor_key]["name"] = (
                f"{friendly} {index}" if multiple else friendly
            )

    return result


def _parse_sensors_json(raw: str) -> dict:
    data = json.loads(raw)
    result = {}

    for chip, chip_data in data.items():
        if not isinstance(chip_data, dict):
            continue

        adapter = chip_data.get("Adapter", "")

        for label, subfeatures in chip_data.items():
            if label == "Adapter" or not isinstance(subfeatures, dict):
                continue

            temp = next(
                (value for key, value in subfeatures.items() if key.endswith("_input")),
                None,
            )

            if temp is None:
                continue

            sensor_key = f"{chip}:{label}"
            result[sensor_key] = {
                "chip": chip,
                "adapter": adapter,
                "label": label,
                "temp_c": round(float(temp), 1),
            }

    return _apply_friendly_names(result)


def read_lm_sensors() -> tuple[dict, list[str]]:
    errors = []

    try:
        proc = subprocess.run(
            ["sensors", "-j"],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (subprocess.SubprocessError, OSError) as exc:
        return {}, [f"Could not run sensors -j: {exc}"]

    if proc.returncode != 0:
        errors.append(proc.stderr.strip() or f"sensors exited with {proc.returncode}")
        return {}, errors

    if not proc.stdout.strip():
        return {}, ["sensors -j returned empty output"]

    try:
        return _parse_sensors_json(proc.stdout), errors
    except (json.JSONDecodeError, ValueError) as exc:
        return {}, [f"Could not parse sensors -j output: {exc}"]


def _ctrl_value_re(name: str):
    return re.compile(rf"{name}\b.*?\bvalue=(-?\d+)"), re.compile(
        rf"{name}:\s*(-?\d+)"
    )


_SENSOR_TEMP_VALUE_RE, _SENSOR_TEMP_PLAIN_RE = _ctrl_value_re("sensor_temperature")
_TEMP_CONTROL_VALUE_RE, _TEMP_CONTROL_PLAIN_RE = _ctrl_value_re("temperature_control")


def _query_v4l2_ctrl(device: str, ctrl_name: str) -> tuple[bool, str]:
    try:
        proc = subprocess.run(
            ["v4l2-ctl", "-d", device, f"--get-ctrl={ctrl_name}"],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (subprocess.SubprocessError, OSError) as exc:
        return False, str(exc)

    if proc.returncode != 0:
        return False, proc.stderr.strip() or f"exited with code {proc.returncode}"

    return True, proc.stdout


def start_camera_temperature_stream(
    stream_device: str,
    frame_count: int = 300,
    startup_wait_s: float = 1.0,
) -> tuple[subprocess.Popen | None, dict]:
    """Start a temporary stream and leave it running while temperature is read.

    On this camera, the V4L2 sensor_temperature control is updated only while
    the video pipeline is actively streaming. A short pre-read stream is not
    enough if it stops before the get-ctrl call. Therefore this function starts
    v4l2-ctl as a background process, waits briefly for streaming to begin, and
    the caller reads sensor_temperature while the process is still alive.
    """
    command = [
        "v4l2-ctl",
        "-d",
        stream_device,
        "--stream-mmap",
        f"--stream-count={int(frame_count)}",
        "--stream-to=/dev/null",
    ]

    metadata = {
        "enabled": True,
        "mode": "active_during_read",
        "stream_device": stream_device,
        "frame_count": int(frame_count),
        "startup_wait_s": float(startup_wait_s),
        "command": command,
    }

    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except (subprocess.SubprocessError, OSError) as exc:
        metadata.update({
            "ok": False,
            "error": str(exc),
        })
        return None, metadata

    time.sleep(max(0.0, float(startup_wait_s)))

    returncode = process.poll()
    if returncode is not None:
        stdout, stderr = process.communicate(timeout=1)
        metadata.update({
            "ok": False,
            "returncode": returncode,
            "stdout": stdout.strip(),
            "stderr": stderr.strip(),
            "error": "stream process ended before sensor_temperature read",
        })
        return None, metadata

    metadata.update({
        "ok": True,
        "running_during_read": True,
    })
    return process, metadata


def stop_camera_temperature_stream(
    process: subprocess.Popen | None,
    metadata: dict,
    stop_timeout_s: float = 3.0,
) -> dict:
    """Stop the temporary stream and append shutdown details to metadata."""
    if process is None:
        metadata.setdefault("stopped", False)
        return metadata

    if process.poll() is None:
        process.terminate()
        try:
            stdout, stderr = process.communicate(timeout=float(stop_timeout_s))
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate(timeout=1)
            metadata["forced_kill"] = True
    else:
        stdout, stderr = process.communicate(timeout=1)

    metadata.update({
        "stopped": True,
        "returncode_after_stop": process.returncode,
        "stdout": (stdout or "").strip(),
        "stderr": (stderr or "").strip(),
    })
    return metadata


def read_camera_sensor_temperature(
    device: str,
    stream_refresh: bool = True,
    stream_device: str | None = None,
    stream_count: int = 300,
    stream_startup_wait_s: float = 1.0,
) -> tuple[dict, list[str]]:
    errors = []
    stream_device = stream_device or device
    stream_process = None

    if stream_refresh:
        stream_process, refresh_result = start_camera_temperature_stream(
            stream_device=stream_device,
            frame_count=stream_count,
            startup_wait_s=stream_startup_wait_s,
        )
        if not refresh_result.get("ok", False):
            errors.append(
                "camera stream was not active before sensor_temperature read: "
                + (refresh_result.get("error") or refresh_result.get("stderr") or "unknown error")
            )
    else:
        refresh_result = {
            "enabled": False,
            "ok": None,
            "stream_device": stream_device,
        }

    try:
        ok, output_or_error = _query_v4l2_ctrl(device, "sensor_temperature")
    finally:
        if stream_refresh:
            refresh_result = stop_camera_temperature_stream(
                stream_process,
                refresh_result,
            )

    if not ok:
        return {}, [f"sensor_temperature query failed on {device}: {output_or_error}"]

    match = (
        _SENSOR_TEMP_VALUE_RE.search(output_or_error)
        or _SENSOR_TEMP_PLAIN_RE.search(output_or_error)
    )

    if not match:
        return {}, [f"Could not parse sensor_temperature output: {output_or_error.strip()}"]

    try:
        temp_c = round(int(match.group(1)) / 1000.0, 1)
    except ValueError as exc:
        return {}, [f"Could not convert sensor_temperature to int: {exc}"]

    control_active = None
    ctrl_ok, ctrl_output = _query_v4l2_ctrl(device, "temperature_control")

    if ctrl_ok:
        ctrl_match = (
            _TEMP_CONTROL_VALUE_RE.search(ctrl_output)
            or _TEMP_CONTROL_PLAIN_RE.search(ctrl_output)
        )

        if ctrl_match:
            try:
                control_active = bool(int(ctrl_match.group(1)))
            except ValueError:
                control_active = None

    sensor_info = {
        "chip": "camera",
        "adapter": device,
        "label": "sensor_temperature",
        "temp_c": temp_c,
        "name": "Camera Sensor",
        "control_active": control_active,
        "stream_refresh": refresh_result,
    }

    if temp_c == 20.0:
        sensor_info["warning"] = "exactly_20c_possible_default_or_stale_value"

    return {
        "camera:sensor_temperature": sensor_info
    }, errors


def read_all_temperatures(
    device: str,
    stream_refresh: bool = True,
    stream_device: str | None = None,
    stream_count: int = 5,
    stream_startup_wait_s: float = 1.0,
) -> dict:
    sensors, sensor_errors = read_lm_sensors()
    camera_sensor, camera_errors = read_camera_sensor_temperature(
        device=device,
        stream_refresh=stream_refresh,
        stream_device=stream_device,
        stream_count=stream_count,
        stream_startup_wait_s=stream_startup_wait_s,
    )

    readings = {}
    readings.update(sensors)
    readings.update(camera_sensor)

    timestamp_epoch = time.time()

    return {
        "timestamp": datetime.fromtimestamp(timestamp_epoch).isoformat(timespec="seconds"),
        "epoch": timestamp_epoch,
        "device": device,
        "sensors": readings,
        "errors": sensor_errors + camera_errors,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--device", default="/dev/video4")
    parser.add_argument(
        "--stream-device",
        default=None,
        help="Device node to briefly stream before reading sensor_temperature. "
             "Defaults to --device.",
    )
    parser.add_argument(
        "--stream-count",
        type=int,
        default=300,
        help="Number of frames to stream to /dev/null while reading sensor_temperature.",
    )
    parser.add_argument(
        "--stream-startup-wait-s",
        type=float,
        default=1.0,
        help="Seconds to wait after starting the temporary stream before reading sensor_temperature.",
    )
    parser.add_argument(
        "--no-stream-refresh",
        action="store_true",
        help="Disable the pre-read stream refresh.",
    )
    args = parser.parse_args()

    print(json.dumps(
        read_all_temperatures(
            device=args.device,
            stream_refresh=not args.no_stream_refresh,
            stream_device=args.stream_device,
            stream_count=args.stream_count,
            stream_startup_wait_s=args.stream_startup_wait_s,
        )
    ))


if __name__ == "__main__":
    main()
