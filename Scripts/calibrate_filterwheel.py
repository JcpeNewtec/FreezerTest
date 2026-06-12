#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jun  4 10:34:30 2026

@author: jcpe
"""

import json
from pathlib import Path

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
    FILTERWHEEL_HOME_SEARCH_DIRECTION,
    FILTERWHEEL_HOME_FAST_STEP,
    FILTERWHEEL_HOME_SLOW_STEP,
    FILTERWHEEL_HOME_MAX_STEPS,
)

try:
    from Control.temperature_logger import TemperatureLogger
    HAS_LAMP = True
except Exception:
    HAS_LAMP = False


OUTPUT_FILE = Path("calibrated_filter_positions.json")


def print_help():
    print("""
Commands:
  p                 show current motor position
  home              run Hall sensor homing and set position to 0
  g <pos>           go to absolute position, e.g. g 600
  j <steps>         jog relative steps, e.g. j 10 or j -10
  f <1-8>           go to configured filter position
  s <1-8>           save current position as filter number
  l on              lamp on
  l off             lamp off
  show              show saved calibration
  save              write calibration to calibrated_filter_positions.json
  q                 quit
""")


def main():
    positions = dict(FILTER_POSITIONS)

    fw = FilterwheelController(
        tic_serial=TIC_SERIAL,
        filter_positions=positions,
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

    lamp = None

    print("Initializing filterwheel...")
    fw.initialize(set_zero_here=False)

    if HAS_LAMP:
        try:
            lamp = TemperatureLogger(log_path="calibration_temperature_log.jsonl", interval_s=1.0)
            lamp.start()
            print("Lamp control available.")
        except Exception as e:
            lamp = None
            print(f"Lamp control unavailable: {e}")

    print_help()

    try:
        while True:
            cmd = input("cal> ").strip().split()
            if not cmd:
                continue

            if cmd[0] == "q":
                break

            elif cmd[0] == "p":
                print(f"Current position: {fw.get_current_position()}")

            elif cmd[0] == "g" and len(cmd) == 2:
                pos = int(cmd[1])
                fw.move_to_position(pos)
                print(f"Moved to {pos}. Current: {fw.get_current_position()}")

            elif cmd[0] == "j" and len(cmd) == 2:
                delta = int(cmd[1])
                current = fw.get_current_position()
                target = current + delta
                fw.move_to_position(target)
                print(f"Jogged to {target}. Current: {fw.get_current_position()}")

            elif cmd[0] == "f" and len(cmd) == 2:
                filt = int(cmd[1])
                if filt not in positions:
                    print(f"Filter {filt} is not defined.")
                    continue
                fw.move_to_position(positions[filt])
                print(f"Moved to filter {filt} at {positions[filt]}.")

            elif cmd[0] == "s" and len(cmd) == 2:
                filt = int(cmd[1])
                current = fw.get_current_position()
                positions[filt] = current
                fw.filter_positions = positions
                print(f"Saved filter {filt} = {current}")
                
            elif cmd[0] == "home":
                if lamp is None:
                    print("Hall reader unavailable because TemperatureLogger is not running.")
                    continue

                homing_result = fw.home_with_hall(
                    is_hall_active=lamp.is_hall_active,
                    search_direction=FILTERWHEEL_HOME_SEARCH_DIRECTION,
                    fast_step=FILTERWHEEL_HOME_FAST_STEP,
                    slow_step=FILTERWHEEL_HOME_SLOW_STEP,
                    max_steps=FILTERWHEEL_HOME_MAX_STEPS,
                )

                print("Homing complete:")
                print(json.dumps(homing_result, indent=4))
                print(f"Current position after homing: {fw.get_current_position()}")

            elif cmd[0] == "l" and len(cmd) == 2:
                if lamp is None:
                    print("Lamp control not available.")
                    continue
                if cmd[1] == "on":
                    lamp.lamp_on()
                    print("Lamp ON")
                elif cmd[1] == "off":
                    lamp.lamp_off()
                    print("Lamp OFF")
                else:
                    print("Use: l on OR l off")

            elif cmd[0] == "show":
                print(json.dumps(positions, indent=4))

            elif cmd[0] == "save":
                with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                    json.dump(positions, f, indent=4)
                print(f"Saved to {OUTPUT_FILE.resolve()}")

            else:
                print("Unknown command.")
                print_help()

    finally:
        print("Turning lamp off and shutting down...")
        if lamp is not None:
            try:
                lamp.lamp_off()
                lamp.stop()
            except Exception:
                pass

        try:
            fw.return_to_zero()
        except Exception:
            pass

        fw.shutdown()


if __name__ == "__main__":
    main()