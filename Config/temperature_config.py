#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Apr 22 10:31:06 2026

@author: jcpe
"""
HOST = "10.100.10.101"
PORT = 54211
IFACE = None

CHANNEL_CONFIG = {
    0: {"name": "probe_1", "tc_type": "K", "enabled": True},
    1: {"name": "probe_2", "tc_type": "K", "enabled": True},
    2: {"name": "probe_3", "tc_type": "K", "enabled": True},
    3: {"name": "probe_4", "tc_type": "K", "enabled": True},
    4: {"name": "probe_5", "tc_type": "K", "enabled": True},
    5: {"name": "probe_6", "tc_type": "K", "enabled": False},
    6: {"name": "probe_7", "tc_type": "K", "enabled": False},
    7: {"name": "probe_8", "tc_type": "K", "enabled": False},
}
