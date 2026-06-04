# /root/scripts/filterwheel_control.py

import shutil
import subprocess
import time


class FilterwheelError(Exception):
    pass


class FilterwheelController:
    def __init__(
        self,
        tic_serial: str | None = None,
        filter_positions: dict[int, int] | None = None,
        step_mode: int = 8,
        current_limit_ma: int = 1200,
        max_speed: int = 3000000,
        starting_speed: int = 0,
        max_accel: int = 10000,
        max_decel: int = 10000,
        position_tolerance: int = 5,
        settle_time_s: float = 0.2,
        move_timeout_s: float = 10.0,
    ):
        self.tic_serial = tic_serial
        self.filter_positions = filter_positions or {}
        self.step_mode = step_mode
        self.current_limit_ma = current_limit_ma
        self.max_speed = max_speed
        self.starting_speed = starting_speed
        self.max_accel = max_accel
        self.max_decel = max_decel
        self.position_tolerance = position_tolerance
        self.settle_time_s = settle_time_s
        self.move_timeout_s = move_timeout_s

    def _base_cmd(self) -> list[str]:
        tic_path = shutil.which("ticcmd")
        if tic_path is None:
            raise FilterwheelError("ticcmd was not found in PATH.")
        cmd = [tic_path]
        if self.tic_serial:
            cmd += ["-d", self.tic_serial]
        return cmd

    def _run(self, *args: str) -> str:
        cmd = self._base_cmd() + list(args)
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise FilterwheelError(
                f"ticcmd failed.\n"
                f"Command: {' '.join(cmd)}\n"
                f"stdout:\n{result.stdout}\n"
                f"stderr:\n{result.stderr}"
            )

        return result.stdout.strip()


    def initialize(self, set_zero_here: bool = False):

        self._run("--energize")
        self._run("--exit-safe-start")

        self._run("--step-mode", str(self.step_mode))
        self._run("--current", str(self.current_limit_ma))
        self._run("--starting-speed", str(self.starting_speed))
        self._run("--max-speed", str(self.max_speed))
        self._run("--max-accel", str(self.max_accel))
        self._run("--max-decel", str(self.max_decel))

        if set_zero_here:
            self.set_zero_here()

    def shutdown(self):
        try:
            self._run("--enter-safe-start")
        except Exception:
            pass

        try:
            self._run("--deenergize")
        except Exception:
            pass

    def set_zero_here(self):
        self._run("--halt-and-set-position", "0")

    def get_status(self) -> str:
        return self._run("-s", "--full")

    def get_current_position(self) -> int:
        status = self.get_status()

        for line in status.splitlines():
            if "Current position" in line:
                return int(line.split()[-1])

        raise FilterwheelError("Could not parse current position from ticcmd status output.")

    def move_to_position(self, position: int):
        self._run("--position", str(position))
        self.wait_until_reached(position)

    def wait_until_reached(self, target: int):
        start_time = time.time()

        while True:
            current = self.get_current_position()

            if abs(current - target) <= self.position_tolerance:
                time.sleep(self.settle_time_s)
                return

            if (time.time() - start_time) > self.move_timeout_s:
                raise FilterwheelError(
                    f"Timed out waiting for target position {target}. "
                    f"Current position: {current}"
                )

            time.sleep(0.05)

    def move_to_filter(self, filter_number: int) -> int:
        if filter_number not in self.filter_positions:
            raise FilterwheelError(f"Filter {filter_number} is not defined in filter_positions.")

        target = self.filter_positions[filter_number]
        self.move_to_position(target)
        return target

    def return_to_zero(self):
        self.move_to_position(0)
    
    def home_with_hall(
        self,
        is_hall_active,
        search_direction: int = -1,
        fast_step: int = 10,
        slow_step: int = 1,
        max_steps: int = 3000,
    ):
        if search_direction not in (-1, 1):
            raise FilterwheelError("search_direction must be -1 or 1.")
    
        print("Starting Hall homing...")
    
        start_position = self.get_current_position()
        travelled = 0
    
        # If currently on the magnet, first move away until inactive.
        while is_hall_active():
            current = self.get_current_position()
            target = current - search_direction * fast_step
            self.move_to_position(target)
            travelled += abs(fast_step)
    
            if travelled > max_steps:
                raise FilterwheelError("Homing failed while moving away from Hall sensor.")
    
        # Move toward the magnet quickly until active.
        travelled = 0
        while not is_hall_active():
            current = self.get_current_position()
            target = current + search_direction * fast_step
            self.move_to_position(target)
            travelled += abs(fast_step)
    
            if travelled > max_steps:
                raise FilterwheelError(
                    f"Homing failed: Hall sensor not found. Started at {start_position}."
                )
    
        # Back out until inactive again.
        while is_hall_active():
            current = self.get_current_position()
            target = current - search_direction * slow_step
            self.move_to_position(target)
    
        # Slowly approach final edge.
        while not is_hall_active():
            current = self.get_current_position()
            target = current + search_direction * slow_step
            self.move_to_position(target)
    
        edge_position = self.get_current_position()
        print(f"Hall edge found at motor position {edge_position}")
    
        self.set_zero_here()
        print("Filterwheel home set to 0.")
        return edge_position