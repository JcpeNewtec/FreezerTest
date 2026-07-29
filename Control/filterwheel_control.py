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
        deenergize_after_move: bool = True,
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
        self.deenergize_after_move = deenergize_after_move
        self._is_energized = False

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

    def energize(self):
        """Enable motor current and exit safe-start before motion."""
        self._run("--energize")
        self._run("--exit-safe-start")
        self._is_energized = True

    def deenergize(self):
        """Disable motor current to avoid heating while idle."""
        self._run("--deenergize")
        self._is_energized = False

    def initialize(self, set_zero_here: bool = False):
        # Energize briefly so the Tic is in a known usable state, then apply settings.
        self.energize()

        self._run("--step-mode", str(self.step_mode))
        self._run("--current", str(self.current_limit_ma))
        self._run("--starting-speed", str(self.starting_speed))
        self._run("--max-speed", str(self.max_speed))
        self._run("--max-accel", str(self.max_accel))
        self._run("--max-decel", str(self.max_decel))

        if set_zero_here:
            self.set_zero_here()

        if self.deenergize_after_move:
            self.deenergize()

    def shutdown(self):
        try:
            self._run("--enter-safe-start")
        except Exception:
            pass

        try:
            self.deenergize()
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

    def move_to_position(self, position: int, keep_energized: bool = False):
        self.energize()

        try:
            self._run("--position", str(position))
            self.wait_until_reached(position)
        finally:
            if self.deenergize_after_move and not keep_energized:
                self.deenergize()

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
        fast_step: int = 50,
        slow_step: int = 2,
        max_steps: int = 3000,
    ):
        if search_direction not in (-1, 1):
            raise FilterwheelError("search_direction must be -1 or 1.")

        print("Starting Hall homing...")
        t0 = time.monotonic()

        # Keep the motor energized during the homing sequence itself,
        # but de-energize again afterward. This avoids repeated on/off cycles
        # for every small Hall-search step.
        self.energize()

        try:
            start_position = self.get_current_position()

            def step_relative(delta: int):
                current = self.get_current_position()
                target = current + delta
                self.move_to_position(target, keep_energized=True)
                return self.get_current_position()

            # Phase 1: if already on the magnet, move away until inactive.
            travelled = 0
            if is_hall_active():
                print("Hall already active. Moving away from magnet...")
            while is_hall_active():
                step_relative(-search_direction * fast_step)
                travelled += abs(fast_step)
                if travelled > max_steps:
                    raise FilterwheelError("Homing failed while moving away from Hall sensor.")

            # Phase 2: fast search toward magnet.
            print("Fast search toward Hall edge...")
            travelled = 0
            while not is_hall_active():
                step_relative(search_direction * fast_step)
                travelled += abs(fast_step)
                if travelled > max_steps:
                    raise FilterwheelError(
                        f"Homing failed: Hall sensor not found. Started at {start_position}."
                    )

            fast_hit_position = self.get_current_position()

            # Phase 3: back away slowly until inactive.
            print("Backing out of Hall active region...")
            while is_hall_active():
                step_relative(-search_direction * slow_step)

            inactive_edge_position = self.get_current_position()

            # Phase 4: final slow approach toward active edge.
            print("Final slow approach to Hall edge...")
            while not is_hall_active():
                step_relative(search_direction * slow_step)

            edge_position = self.get_current_position()

            self.set_zero_here()

            homing_duration_s = time.monotonic() - t0
            print(
                f"Hall edge found at motor position {edge_position}. "
                f"Homing duration: {homing_duration_s:.2f} s"
            )
            print("Filterwheel home set to 0.")

            return {
                "start_position": start_position,
                "fast_hit_position": fast_hit_position,
                "inactive_edge_position": inactive_edge_position,
                "edge_position_before_zero": edge_position,
                "search_direction": search_direction,
                "fast_step": fast_step,
                "slow_step": slow_step,
                "duration_s": round(homing_duration_s, 3),
            }

        finally:
            if self.deenergize_after_move:
                try:
                    self.deenergize()
                except Exception:
                    pass
