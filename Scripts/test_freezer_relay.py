#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Simple freezer relay test.

Purpose:
    Toggle the freezer contactor through MCC DIO3 with long delays
    so the compressor is not rapidly cycled.

Run from repo root:

    PYTHONPATH=. python3 Scripts/test_freezer_relay.py

Stop safely with Ctrl+C. The script will try to turn the freezer OFF.
"""

import time
from datetime import datetime

from mcculw import ul
from mcculw.enums import DigitalPortType, DigitalIODirection


BOARD_NUM = 0
PORT_TYPE = DigitalPortType.AUXPORT

FREEZER_DIO_BIT = 3
FREEZER_ACTIVE_STATE = 1
FREEZER_INACTIVE_STATE = 0

# Use 600 s = 10 min for compressor-friendly testing.
ON_TIME_S = 10 * 60
OFF_TIME_S = 10 * 60


def log(message: str):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now}] {message}", flush=True)


def configure_dio():
    ul.d_config_bit(
        BOARD_NUM,
        PORT_TYPE,
        FREEZER_DIO_BIT,
        DigitalIODirection.OUT,
    )


def set_freezer(state: bool):
    value = FREEZER_ACTIVE_STATE if state else FREEZER_INACTIVE_STATE

    ul.d_bit_out(
        BOARD_NUM,
        PORT_TYPE,
        FREEZER_DIO_BIT,
        value,
    )

    if state:
        log(f"FREEZER ON  - DIO{FREEZER_DIO_BIT} = {value}")
    else:
        log(f"FREEZER OFF - DIO{FREEZER_DIO_BIT} = {value}")


def wait_with_countdown(seconds: int, label: str):
    log(f"Waiting {seconds} s: {label}")

    remaining = seconds
    while remaining > 0:
        step = min(60, remaining)
        time.sleep(step)
        remaining -= step
        log(f"{label}: {remaining} s remaining")


def main():
    log("Configuring MCC DIO")
    configure_dio()

    try:
        # Start from a known safe state.
        set_freezer(False)
        time.sleep(2)

        set_freezer(True)
        wait_with_countdown(ON_TIME_S, "freezer ON period")

        set_freezer(False)
        wait_with_countdown(OFF_TIME_S, "compressor OFF protection period")

        set_freezer(True)
        wait_with_countdown(ON_TIME_S, "freezer ON period")

        set_freezer(False)
        log("Freezer relay test complete")

    except KeyboardInterrupt:
        log("Interrupted by user")

    finally:
        log("Safety shutdown: turning freezer OFF")
        try:
            set_freezer(False)
        except Exception as e:
            log(f"Failed to turn freezer OFF: {e}")


if __name__ == "__main__":
    main()