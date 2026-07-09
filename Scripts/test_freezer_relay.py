#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test freezer contactor control through MCC DIO3.

This uses the existing FreezerTest control architecture:
    TemperatureLogger -> TemperatureController -> uldaq DIO

Run from repo root:

    PYTHONPATH=. python3 Scripts/test_freezer_relay.py

Default behavior:
    freezer OFF
    freezer ON for 10 minutes
    freezer OFF
    wait 10 minutes

The long waits protect the compressor from rapid cycling.
"""

import argparse
import time
from datetime import datetime

from Control.temperature_logger import TemperatureLogger
from Config.system_config import (
    FREEZER_MIN_OFF_TIME_S,
    FREEZER_TEST_ON_TIME_S,
)


def log(message: str):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now}] {message}", flush=True)


def wait_with_countdown(seconds: int, label: str):
    log(f"Waiting {seconds} s: {label}")

    remaining = int(seconds)

    while remaining > 0:
        step = min(60, remaining)
        time.sleep(step)
        remaining -= step
        log(f"{label}: {remaining} s remaining")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--on-time-s",
        type=int,
        default=int(FREEZER_TEST_ON_TIME_S),
        help="How long to keep the freezer ON.",
    )
    parser.add_argument(
        "--off-time-s",
        type=int,
        default=int(FREEZER_MIN_OFF_TIME_S),
        help="How long to wait after turning freezer OFF.",
    )
    parser.add_argument(
        "--skip-final-wait",
        action="store_true",
        help="Turn freezer OFF at the end but do not wait afterward.",
    )
    args = parser.parse_args()

    logger = TemperatureLogger(
        log_path="freezer_relay_test_log.jsonl",
        interval_s=1.0,
    )

    log("Starting TemperatureLogger / MCC connection")
    logger.start()

    try:
        log("Initial safe state: freezer OFF")
        record = logger.freezer_off()
        print(record, flush=True)

        time.sleep(2)

        log("Turning freezer ON")
        record = logger.freezer_on()
        print(record, flush=True)

        wait_with_countdown(args.on_time_s, "freezer ON period")

        log("Turning freezer OFF")
        record = logger.freezer_off()
        print(record, flush=True)

        if not args.skip_final_wait:
            wait_with_countdown(args.off_time_s, "compressor OFF protection period")

        log("Freezer relay test complete")

    except KeyboardInterrupt:
        log("Interrupted by user")

    finally:
        log("Safety shutdown: freezer OFF")
        try:
            record = logger.freezer_off()
            print(record, flush=True)
        except Exception as e:
            log(f"Could not turn freezer OFF cleanly: {e}")

        logger.stop()
        log("Logger stopped")


if __name__ == "__main__":
    main()