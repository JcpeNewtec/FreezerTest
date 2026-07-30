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


def read_camera_sensor_temperature(device: str) -> tuple[dict, list[str]]:
    errors = []

    ok, output_or_error = _query_v4l2_ctrl(device, "sensor_temperature")
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

    return {
        "camera:sensor_temperature": {
            "chip": "camera",
            "adapter": device,
            "label": "sensor_temperature",
            "temp_c": temp_c,
            "name": "Camera Sensor",
            "control_active": control_active,
        }
    }, errors


def read_all_temperatures(device: str) -> dict:
    sensors, sensor_errors = read_lm_sensors()
    camera_sensor, camera_errors = read_camera_sensor_temperature(device)

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
    args = parser.parse_args()

    print(json.dumps(read_all_temperatures(args.device)))


if __name__ == "__main__":
    main()
