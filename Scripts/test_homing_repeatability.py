#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jun 11 12:19:03 2026

@author: jcpe
"""

import json
from datetime import datetime
from pathlib import Path

from Control.filterwheel_control import FilterwheelController
from Control.temperature_logger import TemperatureLogger
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
    FILTERWHEEL_HOME_SEARCH_DIRECTION,
    FILTERWHEEL_HOME_FAST_STEP,
    FILTERWHEEL_HOME_SLOW_STEP,
    FILTERWHEEL_HOME_MAX_STEPS,
)

N_CYCLES = 3
TEST_OFFSET_AFTER_HOME = 250
OUTPUT_PATH = Path("homing_repeatability_test.json")


def make_filterwheel():
    return FilterwheelController(
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
    )


def main():
    logger = TemperatureLogger(
        log_path="homing_repeatability_temperature_log.jsonl",
        interval_s=1.0,
    )
    fw = make_filterwheel()

    results = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "n_cycles": N_CYCLES,
        "test_offset_after_home": TEST_OFFSET_AFTER_HOME,
        "homing_settings": {
            "search_direction": FILTERWHEEL_HOME_SEARCH_DIRECTION,
            "fast_step": FILTERWHEEL_HOME_FAST_STEP,
            "slow_step": FILTERWHEEL_HOME_SLOW_STEP,
            "max_steps": FILTERWHEEL_HOME_MAX_STEPS,
        },
        "cycles": [],
    }

    logger.start()
    fw.initialize(set_zero_here=False)

    try:
        for i in range(1, N_CYCLES + 1):
            print(f"\n=== Homing cycle {i}/{N_CYCLES} ===")

            homing_result = fw.home_with_hall(
                is_hall_active=logger.is_hall_active,
                search_direction=FILTERWHEEL_HOME_SEARCH_DIRECTION,
                fast_step=FILTERWHEEL_HOME_FAST_STEP,
                slow_step=FILTERWHEEL_HOME_SLOW_STEP,
                max_steps=FILTERWHEEL_HOME_MAX_STEPS,
            )

            position_after_zero = fw.get_current_position()

            # Move away so the next cycle has to find home again.
            fw.move_to_position(TEST_OFFSET_AFTER_HOME)
            position_after_offset = fw.get_current_position()

            cycle = {
                "cycle": i,
                "homing_result": homing_result,
                "position_after_zero": position_after_zero,
                "position_after_offset": position_after_offset,
            }

            results["cycles"].append(cycle)
            print(json.dumps(cycle, indent=4))

    finally:
        try:
            fw.return_to_zero()
        except Exception:
            pass

        fw.shutdown()
        logger.stop()

        with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=4)

        print(f"\nSaved results to: {OUTPUT_PATH.resolve()}")


if __name__ == "__main__":
    main()