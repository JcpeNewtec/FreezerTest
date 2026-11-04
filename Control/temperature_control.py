"""Serialized MCC E-TC access, bounded recovery, and explicit safe shutdown."""
from datetime import datetime
from functools import wraps
import threading
import time

from uldaq import (DaqDevice, get_net_daq_device_descriptor, TempScale, TcType,
                   TInFlag, ULException, DigitalDirection, DigitalPortType)
from Config.temperature_config import HOST, PORT, IFACE, CHANNEL_CONFIG
from Config import system_config as config

DIO_PORT = DigitalPortType.AUXPORT0
CAMERA_POWER_DIO_PORT = DIO_PORT
LAMP_DIO_PORT = DIO_PORT
LAMP_DIO_BIT = 0


def tc_type_from_string(name):
    return getattr(TcType, name)


def serialized(method):
    @wraps(method)
    def call(self, *args, **kwargs):
        with self._lock:
            return method(self, *args, **kwargs)
    return call


def is_connection_error(exc):
    # ULDAQ ULError values, including network/discovery failures. Probe faults
    # (OPEN_CONNECTION=85, TEMP_OUT_OF_RANGE=91) must not trigger reconnection.
    return isinstance(exc, ULException) and getattr(exc, 'error_code', None) in {
        2, 6, 7, 8, 20, 73, 94, 97, 98, 102, 103, 104,
    }


class TemperatureController:
    def __init__(self, host=HOST, port=PORT, iface=IFACE, channel_config=CHANNEL_CONFIG):
        self.host, self.port, self.iface = host, port, iface
        self.channel_config = channel_config
        self._lock = threading.RLock()
        self.daq_device = self.ai_device = self.ai_config = self.dio_device = None
        self.freezer_state = self.lamp_state = self.camera_power_state = None
        self._desired = {'freezer': False, 'lamp': False, 'camera': False}
        self._shutdown_requested = False
        self._connected = False
        self._ever_connected = False
        self.mcc_reconnect_count = 0
        self.last_connection_error = None
        self.last_safe_output_record = None

    def _outputs(self):
        return [
            ('freezer', config.FREEZER_DIO_BIT, config.FREEZER_ACTIVE_STATE,
             config.FREEZER_CONTROL_ENABLED),
            ('lamp', LAMP_DIO_BIT, 1, True),
            ('camera', config.CAMERA_POWER_DIO_BIT, config.CAMERA_POWER_ACTIVE_STATE,
             config.CAMERA_POWER_CONTROL_ENABLED),
        ]

    def _release(self):
        device = self.daq_device
        self._connected = False
        self.daq_device = self.ai_device = self.ai_config = self.dio_device = None
        self.freezer_state = self.lamp_state = self.camera_power_state = None
        if device is not None:
            for action in (device.disconnect, device.release):
                try:
                    action()
                except Exception:
                    pass

    def _write_output(self, name, bit, active, enabled):
        if not enabled:
            return
        value = active if self._desired[name] else 1 - active
        self.dio_device.d_bit_out(DIO_PORT, bit, value)
        setattr(self, {'camera': 'camera_power_state'}.get(name, name + '_state'),
                self._desired[name])

    def _open(self):
        self._release()
        try:
            desc = get_net_daq_device_descriptor(self.host, self.port, self.iface, 5.0)
            self.daq_device = DaqDevice(desc)
            self.daq_device.connect()
            self.dio_device = self.daq_device.get_dio_device()
            # Establish relay states before any thermocouple configuration.
            # Attempt every output even if an earlier output fails.
            failures = []
            for output in self._outputs():
                name, bit, active, enabled = output
                if enabled:
                    try:
                        self.dio_device.d_config_bit(DIO_PORT, bit, DigitalDirection.OUTPUT)
                        self._write_output(*output)
                    except Exception as exc:
                        failures.append(exc)
            if failures:
                raise failures[0]
            self.dio_device.d_config_bit(DIO_PORT, config.HALL_DIO_BIT, DigitalDirection.INPUT)
            self.ai_device = self.daq_device.get_ai_device()
            self.ai_config = self.ai_device.get_config()
            for ch, cfg in self.channel_config.items():
                self.ai_config.set_chan_tc_type(ch, tc_type_from_string(cfg['tc_type']))
            self._connected = True
            if self._ever_connected:
                self.mcc_reconnect_count += 1
            self._ever_connected = True
        except BaseException:
            self._release()
            raise

    def _reconnect(self, attempts, delay):
        last = None
        for attempt in range(max(1, int(attempts))):
            if attempt:
                time.sleep(max(0, float(delay)))
            try:
                self._open()
                return
            except Exception as exc:
                self.last_connection_error = str(exc)
                last = exc
                if not is_connection_error(exc):
                    raise
        raise last

    def _execute(self, operation):
        for retry in range(max(0, int(config.MCC_COMMAND_RETRY_COUNT)) + 1):
            try:
                if not self._connected:
                    self._open()
                return operation()
            except Exception as exc:
                if not is_connection_error(exc):
                    raise
                self.last_connection_error = str(exc)
                self._release()
                if not config.MCC_AUTO_RECONNECT_ENABLED or retry >= config.MCC_COMMAND_RETRY_COUNT:
                    raise
                self._reconnect(config.MCC_RECONNECT_MAX_ATTEMPTS, config.MCC_RECONNECT_DELAY_S)

    @serialized
    def connect(self):
        self._execute(lambda: None)

    @serialized
    def read_hall_raw(self):
        return self._execute(lambda: self.dio_device.d_bit_in(DIO_PORT, config.HALL_DIO_BIT))

    def is_hall_active(self):
        return self.read_hall_raw() == config.HALL_ACTIVE_STATE

    @serialized
    def _set_output(self, name, state):
        if state and self._shutdown_requested:
            raise RuntimeError('MCC shutdown is latched; create a new controller before enabling outputs.')
        # Update intent BEFORE attempting I/O: recovery must never restore the
        # old ON state while retrying an OFF command.
        self._desired[name] = state
        output = next(o for o in self._outputs() if o[0] == name)
        self._execute(lambda: self._write_output(*output))

    def lamp_on(self): self._set_output('lamp', True)
    def lamp_off(self): self._set_output('lamp', False)
    def freezer_on(self): self._set_output('freezer', True)
    def freezer_off(self): self._set_output('freezer', False)
    def camera_power_on(self): self._set_output('camera', True)
    def camera_power_off(self): self._set_output('camera', False)

    @serialized
    def get_connection_status(self):
        return {'connected': self._connected,
                'mcc_reconnect_count': self.mcc_reconnect_count,
                'last_connection_error': self.last_connection_error,
                'desired_outputs': dict(self._desired),
                'shutdown_requested': self._shutdown_requested}

    @serialized
    def ensure_safe_outputs_off(self):
        self._shutdown_requested = True
        self._desired = dict.fromkeys(self._desired, False)
        record = {'timestamp': datetime.now().isoformat(timespec='seconds'),
                  'safe_outputs_off_confirmed': False,
                  'confirmation_scope': 'MCC digital output readback; not relay contacts',
                  'disabled_outputs': [o[0] for o in self._outputs() if not o[3]],
                  'attempts': []}
        for attempt in range(max(1, int(config.MCC_SAFE_SHUTDOWN_RECONNECT_ATTEMPTS))):
            errors = {}
            if attempt:
                time.sleep(max(0, float(config.MCC_SAFE_SHUTDOWN_RETRY_DELAY_S)))
            try:
                if not self._connected:
                    self._open()
            except Exception as exc:
                errors['connect'] = str(exc)
                self.last_connection_error = str(exc)
            # Do not gate camera/lamp OFF on successful freezer OFF or on
            # temperature reads. All enabled outputs are attempted each time.
            if self.dio_device is not None:
                for output in self._outputs():
                    name, bit, active, enabled = output
                    if enabled:
                        try:
                            self._write_output(*output)
                            if self.dio_device.d_bit_in(DIO_PORT, bit) != 1 - active:
                                raise RuntimeError('Digital output OFF readback mismatch')
                        except Exception as exc:
                            errors[name] = str(exc)
            else:
                errors['outputs'] = 'No MCC digital I/O connection'
            record['attempts'].append({'attempt': attempt + 1, 'errors': errors})
            if not errors:
                record['safe_outputs_off_confirmed'] = True
                break
            self._release()
        record['connection_status'] = self.get_connection_status()
        self.last_safe_output_record = record
        return record

    @serialized
    def disconnect(self):
        try:
            return self.ensure_safe_outputs_off()
        finally:
            self._release()

    @serialized
    def read_all(self):
        def read():
            result = {'timestamp': datetime.now().isoformat(timespec='seconds'),
                      'temperatures_c': {}, 'errors': {}}
            for ch, cfg in self.channel_config.items():
                if cfg['enabled']:
                    try:
                        result['temperatures_c'][cfg['name']] = self.ai_device.t_in(
                            ch, TempScale.CELSIUS, TInFlag.DEFAULT)
                    except ULException as exc:
                        if is_connection_error(exc):
                            raise
                        result['errors'][cfg['name']] = str(exc)
            result.update(lamp_state=self.lamp_state, freezer_state=self.freezer_state,
                          camera_power_state=self.camera_power_state,
                          mcc_reconnect_count=self.mcc_reconnect_count)
            return result
        return self._execute(read)


def get_temperature_snapshot():
    controller = TemperatureController()
    try:
        controller.connect()
        return controller.read_all()
    finally:
        controller.disconnect()
