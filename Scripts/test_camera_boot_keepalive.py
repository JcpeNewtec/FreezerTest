#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Test the exact cold-boot keepalive sequence used by run_long_test.py.

This turns the freezer and lamp off, powers the camera off/on, waits the normal
boot delay, then starts the keepalive stream using the configured readiness and
retry logic. The camera is switched off again during cleanup.

Run from the repository root:

    PYTHONPATH=. python3 Scripts/test_camera_boot_keepalive.py
"""

import json
import time

from Config.system_config import (
    CAMERA_POWER_BOOT_WAIT_S,
    CAMERA_POWER_CONTROL_ENABLED,
)
from Control.camera_keepalive_stream import CameraKeepaliveStream
from Control.temperature_logger import TemperatureLogger


def main():
    logger = TemperatureLogger(
        log_path="camera_boot_keepalive_test.jsonl",
        interval_s=1.0,
    )
    keepalive = CameraKeepaliveStream()

    try:
        logger.start()
        print("Ensuring freezer and lamp are OFF...")
        logger.freezer_off()
        logger.lamp_off()

        if CAMERA_POWER_CONTROL_ENABLED:
            print("Powering camera OFF for 15 s...")
            logger.camera_power_off()
            time.sleep(15.0)

            print("Powering camera ON...")
            logger.camera_power_on()
            print(f"Waiting configured boot delay: {CAMERA_POWER_BOOT_WAIT_S} s")
            time.sleep(max(0.0, float(CAMERA_POWER_BOOT_WAIT_S)))

        print("Starting keepalive with readiness checks and retries...")
        event = keepalive.start(reason="cold_boot_test")
        print(json.dumps(event, indent=2))

        if not event.get("running", False):
            raise RuntimeError(
                "Keepalive failed after all configured attempts. Inspect "
                "event['attempts'], event['log_tail'] and event['diagnostics']."
            )

        print("RESULT: SUCCESS - keepalive is running after a cold camera boot.")

    finally:
        print("Stopping keepalive...")
        try:
            print(json.dumps(keepalive.stop(reason="cold_boot_test_cleanup"), indent=2))
        except Exception as exc:
            print(f"Keepalive cleanup warning: {exc}")

        record = logger.stop()
        print(json.dumps(record, indent=2))
        if not record or not record.get("safe_outputs_off_confirmed", False):
            raise RuntimeError("CRITICAL: Test cleanup could not confirm outputs OFF")


if __name__ == "__main__":
    main()
