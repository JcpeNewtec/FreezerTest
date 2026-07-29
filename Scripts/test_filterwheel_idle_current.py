#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Quick test for filterwheel idle-current behavior.

This script initializes the Tic, moves through the configured filter positions,
and relies on FILTERWHEEL_DEENERGIZE_AFTER_MOVE to turn motor current off
after each move.

Run from repo root:

    PYTHONPATH=. python3 Scripts/test_filterwheel_idle_current.py

While it is waiting after each move, the motor should not be holding/heating
if FILTERWHEEL_DEENERGIZE_AFTER_MOVE = True.
"""

import time

from Control.filterwheel_control import FilterwheelController
from Config.system_config import (
    TIC_SERIAL,
    FILTER_POSITIONS,
    FILTERWHEEL_STEP_MODE,
    FILTERWHEEL_CURRENT_LIMIT_MA,
    FILTERWHEEL_MAX_SPEED,
    FILTERWHEEL_STARTING_SPEED,
    FILTERWHEEL_MAX_ACCEL,
    FILTERWHEEL_MAX_DECEL,
    FILTERWHEEL_POSITION_TOLERANCE,
    FILTERWHEEL_SETTLE_TIME_S,
    FILTERWHEEL_MOVE_TIMEOUT_S,
    FILTERWHEEL_DEENERGIZE_AFTER_MOVE,
)


def main():
    fw = FilterwheelController(
        tic_serial=TIC_SERIAL,
        filter_positions=FILTER_POSITIONS,
        step_mode=FILTERWHEEL_STEP_MODE,
        current_limit_ma=FILTERWHEEL_CURRENT_LIMIT_MA,
        max_speed=FILTERWHEEL_MAX_SPEED,
        starting_speed=FILTERWHEEL_STARTING_SPEED,
        max_accel=FILTERWHEEL_MAX_ACCEL,
        max_decel=FILTERWHEEL_MAX_DECEL,
        position_tolerance=FILTERWHEEL_POSITION_TOLERANCE,
        settle_time_s=FILTERWHEEL_SETTLE_TIME_S,
        move_timeout_s=FILTERWHEEL_MOVE_TIMEOUT_S,
        deenergize_after_move=FILTERWHEEL_DEENERGIZE_AFTER_MOVE,
    )

    print(f"FILTERWHEEL_DEENERGIZE_AFTER_MOVE = {FILTERWHEEL_DEENERGIZE_AFTER_MOVE}")

    try:
        fw.initialize(set_zero_here=False)

        for filter_number in sorted(FILTER_POSITIONS):
            print(f"Moving to filter {filter_number}...")
            target = fw.move_to_filter(filter_number)
            current = fw.get_current_position()
            print(f"Filter {filter_number}: target={target}, controller_position={current}")
            print("Waiting 10 s. Check that the motor is not holding/heating during this wait.")
            time.sleep(10)

        print("Returning to zero...")
        fw.return_to_zero()
        print(f"Final controller position: {fw.get_current_position()}")

    finally:
        print("Shutting down/de-energizing filterwheel...")
        fw.shutdown()


if __name__ == "__main__":
    main()
