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
import time
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
        self._lock = threading.Lock()

    def start(self):
        if self._thread is not None and self._thread.is_alive():
            raise RuntimeError("TemperatureLogger is already running.")

        self.log_path.parent.mkdir(parents=True, exist_ok=True)

        self._controller = TemperatureController()
        self._controller.connect()

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()

        if self._thread is not None:
            self._thread.join(timeout=5.0)

        if self._controller is not None:
            try:
                self._controller.lamp_off()
            except Exception:
                pass
            self._controller.disconnect()
            self._controller = None

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
                }

                with self._lock:
                    self._latest_record = error_record

                with open(self.log_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(error_record) + "\n")

            time.sleep(self.interval_s)
            
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