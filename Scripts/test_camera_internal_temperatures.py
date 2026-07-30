#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Read internal camera temperatures once via SSH.

Run from repo root after deploying Camera_scripts/read_camera_temperatures.py:

    PYTHONPATH=. python3 Scripts/test_camera_internal_temperatures.py
"""

import json

from Scripts.run_single_sweep_remote import remote_read_camera_temperatures


def main():
    record = remote_read_camera_temperatures("manual_test")
    print(json.dumps(record, indent=4))


if __name__ == "__main__":
    main()
