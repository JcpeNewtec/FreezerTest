#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Apr 22 10:32:53 2026

@author: jcpe
"""

import json
import time
from pathlib import Path

from temperature_control import TemperatureController

LOG_PATH = Path("temperature_log.jsonl")
INTERVAL_S = 1.0


def main():
    controller = TemperatureController()
    controller.connect()

    try:
        while True:
            data = controller.read_all()
            print(data)

            with open(LOG_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps(data) + "\n")

            time.sleep(INTERVAL_S)

    finally:
        controller.disconnect()


if __name__ == "__main__":
    main()