#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Apr 22 10:32:15 2026

@author: jcpe
"""

from datetime import datetime

from uldaq import (
    DaqDevice,
    get_net_daq_device_descriptor,
    TempScale,
    TcType,
    TInFlag,
    ULException,
)

from temperature_config import HOST, PORT, IFACE, CHANNEL_CONFIG


def tc_type_from_string(name: str):
    mapping = {
        "J": TcType.J,
        "K": TcType.K,
        "T": TcType.T,
        "E": TcType.E,
        "N": TcType.N,
        "R": TcType.R,
        "S": TcType.S,
        "B": TcType.B,
    }
    return mapping[name]


class TemperatureController:
    def __init__(self, host=HOST, port=PORT, iface=IFACE, channel_config=CHANNEL_CONFIG):
        self.host = host
        self.port = port
        self.iface = iface
        self.channel_config = channel_config
        self.daq_device = None
        self.ai_device = None
        self.ai_config = None

    def connect(self):
        desc = get_net_daq_device_descriptor(self.host, self.port, self.iface, 5.0)
        self.daq_device = DaqDevice(desc)
        self.daq_device.connect()

        self.ai_device = self.daq_device.get_ai_device()
        self.ai_config = self.ai_device.get_config()

        for ch, cfg in self.channel_config.items():
            self.ai_config.set_chan_tc_type(ch, tc_type_from_string(cfg["tc_type"]))

    def disconnect(self):
        if self.daq_device:
            try:
                self.daq_device.disconnect()
            except Exception:
                pass

            try:
                self.daq_device.release()
            except Exception:
                pass

            self.daq_device = None
            self.ai_device = None
            self.ai_config = None
            
            
    def read_all(self):
        timestamp = datetime.now().isoformat(timespec="seconds")
        result = {
            "timestamp": timestamp,
            "temperatures_c": {},
            "errors": {},
        }

        for ch, cfg in self.channel_config.items():
            if not cfg["enabled"]:
                continue

            name = cfg["name"]
            try:
                temp_c = self.ai_device.t_in(
                    ch,
                    TempScale.CELSIUS,
                    TInFlag.DEFAULT,
                )
                result["temperatures_c"][name] = temp_c
            except ULException as e:
                result["errors"][name] = str(e)

        return result
    
def get_temperature_snapshot():
    controller = TemperatureController()
    controller.connect()
    try:
        return controller.read_all()
    finally:
        controller.disconnect()