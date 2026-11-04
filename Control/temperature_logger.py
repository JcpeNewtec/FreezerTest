#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Apr 22 15:22:43 2026

@author: jcpe
"""

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import threading
from datetime import datetime
from pathlib import Path

from Control.temperature_control import TemperatureController


class TemperatureLogger:
    def __init__(self, log_path: str | Path, interval_s: float = 1.0):
        self.log_path = Path(log_path)
        self.interval_s = interval_s
        self._stop_event = threading.Event()
        self._thread = None
        self._controller = None
        self._latest_record = None
        self._lock = threading.RLock()
        self._last_connection_status = {"connected": False}
        self._last_safe_output_record = None

    def start(self):
        if self._thread is not None and self._thread.is_alive():
            raise RuntimeError("TemperatureLogger is already running.")

        self.log_path.parent.mkdir(parents=True, exist_ok=True)

        self._last_safe_output_record = None
        self._last_connection_status = {"connected": False}
        self._controller = TemperatureController()
        self._controller.connect()

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        # Wait for in-flight MCC work to finish before releasing its handle.
        if self._thread is not None:
            self._thread.join()
        with self._lock:
            if self._controller is not None:
                try:
                    self._last_safe_output_record = self._controller.disconnect()
                finally:
                    self._last_connection_status = self._controller.get_connection_status()
                    self._controller = None
            return self._last_safe_output_record

    def ensure_safe_outputs_off(self):
        with self._lock:
            if self._controller is None:
                return {"safe_outputs_off_confirmed": False,
                        "error": "No MCC controller; output state unknown"}
            self._last_safe_output_record = self._controller.ensure_safe_outputs_off()
            return self._last_safe_output_record

    def get_connection_status(self):
        with self._lock:
            if self._controller is not None:
                return self._controller.get_connection_status()
            return dict(self._last_connection_status)

    def get_latest_record(self):
        with self._lock:
            return self._latest_record
    
    def is_hall_active(self) -> bool:
        with self._lock:
            if self._controller is None:
                raise RuntimeError("TemperatureLogger is not running.")
            return self._controller.is_hall_active()

    def _run_loop(self):
        while not self._stop_event.is_set():
            try:
                with self._lock:
                    record = self._controller.read_all()
                record["logger_timestamp"] = datetime.now().isoformat(timespec="seconds")

                with self._lock:
                    self._latest_record = record

                with open(self.log_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(record) + "\n")

            except Exception as e:
                error_record = {
                    "logger_timestamp": datetime.now().isoformat(timespec="seconds"),
                    "logger_status": "error",
                    "error": str(e),
                    "mcc_connection_status": self.get_connection_status(),
                }

                with self._lock:
                    self._latest_record = error_record

                with open(self.log_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(error_record) + "\n")

            self._stop_event.wait(self.interval_s)
            
    def lamp_on(self):
        with self._lock:
            if self._controller is None:
                raise RuntimeError("TemperatureLogger is not running.")
            self._controller.lamp_on()
            self._latest_record = self._controller.read_all()
            return self._latest_record
    
    def lamp_off(self):
        with self._lock:
            if self._controller is None:
                raise RuntimeError("TemperatureLogger is not running.")
            self._controller.lamp_off()
            self._latest_record = self._controller.read_all()
            return self._latest_record
        
        
    def freezer_on(self):
        with self._lock:
            if self._controller is None:
                raise RuntimeError("TemperatureLogger is not running.")
    
            self._controller.freezer_on()
            self._latest_record = self._controller.read_all()
            return self._latest_record
    
    
    def freezer_off(self):
        with self._lock:
            if self._controller is None:
                raise RuntimeError("TemperatureLogger is not running.")
    
            self._controller.freezer_off()
            self._latest_record = self._controller.read_all()
            return self._latest_record
        
    def camera_power_on(self):
        with self._lock:
            if self._controller is None:
                raise RuntimeError("TemperatureLogger is not running.")
    
            self._controller.camera_power_on()
            self._latest_record = self._controller.read_all()
            return self._latest_record
    
    
    def camera_power_off(self):
        with self._lock:
            if self._controller is None:
                raise RuntimeError("TemperatureLogger is not running.")
    
            self._controller.camera_power_off()
            self._latest_record = self._controller.read_all()
            return self._latest_record