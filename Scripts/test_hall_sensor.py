#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jun  4 15:47:53 2026

@author: jcpe
"""

from uldaq import (
    DaqDevice,
    get_net_daq_device_descriptor,
    DigitalDirection,
    DigitalPortType,
)

HOST = "10.100.10.101"
PORT = 54211
IFACE = None

daq_device = None

try:
    desc = get_net_daq_device_descriptor(HOST, PORT, IFACE, 5.0)
    daq_device = DaqDevice(desc)
    daq_device.connect()

    dio = daq_device.get_dio_device()

    port = DigitalPortType.AUXPORT0
    bit = 1

    dio.d_config_bit(port, bit, DigitalDirection.INPUT)

    print("Watching Hall sensor. Move the wheel by hand.")
    print("Ctrl-C to stop.\n")

    last = None

    while True:
        value = dio.d_bit_in(port, bit)

        if value != last:
            print(f"Hall state = {value}")
            last = value

except KeyboardInterrupt:
    pass

finally:
    if daq_device:
        daq_device.disconnect()
        daq_device.release()