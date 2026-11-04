"""Hardware-free regression tests; fake MCC/SSH only, no relay operations."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import types
import unittest
from unittest.mock import patch, Mock

# Match the real ULDAQ exception attribute and enum values. No native SDK load.
class ULException(Exception):
    def __init__(self, error_code):
        self.error_code = error_code
        super().__init__(f'UL error {error_code}')

sdk = types.ModuleType('uldaq')
for name in ('DaqDevice', 'get_net_daq_device_descriptor'):
    setattr(sdk, name, Mock())
sdk.ULException = ULException
sdk.TcType = types.SimpleNamespace(**{n: n for n in 'JKTERN SB'.replace(' ', '')})
sdk.TempScale = types.SimpleNamespace(CELSIUS=0)
sdk.TInFlag = types.SimpleNamespace(DEFAULT=0)
sdk.DigitalDirection = types.SimpleNamespace(INPUT=0, OUTPUT=1)
sdk.DigitalPortType = types.SimpleNamespace(AUXPORT0=0)
sys.modules['uldaq'] = sdk

from Config import system_config as config
# The host must supply LOCAL_DATA_ROOT through ignored local_config.py.
config.LOCAL_DATA_ROOT = tempfile.gettempdir()
from Control import temperature_control as tc
from Control.temperature_logger import TemperatureLogger
from Control.camera_keepalive_stream import CameraKeepaliveStream
from Scripts import run_long_test as runner
from Scripts import run_single_sweep_remote as sweep


class Hardware:
    def __init__(self):
        self.bits = {}
        self.writes = []
        self.devices = []
        self.offline = False
        self.fail_next_read = None
        self.fail_write_bit = None
        self.bad_readback = False
        self.active = 0
        self.overlap = False
        self.gate = threading.Lock()

    def call(self):
        with self.gate:
            self.active += 1
            self.overlap |= self.active > 1
        time.sleep(.0001)
        with self.gate:
            self.active -= 1
        if self.offline:
            raise ULException(7)

    def factory(self, desc):
        h = self
        class Device:
            def connect(self): h.call()
            def disconnect(self): h.call()
            def release(self): self.released = True
            def get_dio_device(self): return self
            def get_ai_device(self): return self
            def get_config(self): return self
            def set_chan_tc_type(self, *args): h.call()
            def d_config_bit(self, *args): h.call()
            def d_bit_out(self, port, bit, value):
                h.call()
                h.writes.append((bit, value))
                if bit == h.fail_write_bit:
                    raise ULException(7)
                h.bits[bit] = value
            def d_bit_in(self, port, bit):
                h.call()
                return 1 if h.bad_readback else h.bits.get(bit, 0)
            def t_in(self, *args):
                h.call()
                if h.fail_next_read is not None:
                    code, h.fail_next_read = h.fail_next_read, None
                    raise ULException(code)
                return 12.0
        device = Device()
        device.released = False
        h.devices.append(device)
        return device


class MCCSafetyTests(unittest.TestCase):
    def setUp(self):
        self.hw = Hardware()
        self.patches = [
            patch.object(tc, 'DaqDevice', self.hw.factory),
            patch.object(tc, 'get_net_daq_device_descriptor', lambda *args: 'MCC'),
        ]
        values = dict(MCC_AUTO_RECONNECT_ENABLED=True, MCC_RECONNECT_MAX_ATTEMPTS=2,
                      MCC_RECONNECT_DELAY_S=0, MCC_COMMAND_RETRY_COUNT=1,
                      MCC_SAFE_SHUTDOWN_RECONNECT_ATTEMPTS=2,
                      MCC_SAFE_SHUTDOWN_RETRY_DELAY_S=0,
                      FREEZER_CONTROL_ENABLED=True, CAMERA_POWER_CONTROL_ENABLED=True,
                      FREEZER_ACTIVE_STATE=1, CAMERA_POWER_ACTIVE_STATE=1)
        self.patches += [patch.object(config, k, v) for k, v in values.items()]
        for p in self.patches:
            p.start()
            self.addCleanup(p.stop)
        self.c = tc.TemperatureController()
        self.c.connect()

    def test_initial_connect_sets_all_outputs_off(self):
        self.assertEqual(self.hw.bits, {3: 0, 0: 0, 2: 0})

    def test_temperature_connection_loss_reconnects_and_restores_intent(self):
        self.c.camera_power_on()
        self.c.freezer_on()
        self.hw.fail_next_read = 7
        record = self.c.read_all()
        self.assertEqual(record['mcc_reconnect_count'], 1)
        self.assertEqual(self.hw.bits, {3: 1, 0: 0, 2: 1})
        self.assertTrue(self.hw.devices[0].released)

    def test_probe_fault_does_not_reconnect(self):
        self.hw.fail_next_read = 85
        record = self.c.read_all()
        self.assertIn('probe_1', record['errors'])
        self.assertEqual(self.c.mcc_reconnect_count, 0)

    def test_reconnect_disabled_still_allows_safety_retry(self):
        config.MCC_AUTO_RECONNECT_ENABLED = False
        self.hw.fail_next_read = 7
        with self.assertRaises(ULException): self.c.read_all()
        self.assertTrue(self.c.ensure_safe_outputs_off()['safe_outputs_off_confirmed'])

    def test_off_intent_is_updated_before_reconnect(self):
        self.c.camera_power_on()
        original = self.c._write_output
        def fail_once(*args):
            self.c._write_output = original
            raise ULException(7)
        self.c._write_output = fail_once
        self.hw.writes.clear()
        self.c.camera_power_off()
        self.assertNotIn((2, 1), self.hw.writes)

    def test_permanent_loss_is_bounded_and_unknown(self):
        self.hw.offline = True
        record = self.c.ensure_safe_outputs_off()
        self.assertFalse(record['safe_outputs_off_confirmed'])
        self.assertEqual(len(record['attempts']), 2)
        self.assertIsNone(self.c.camera_power_state)
        self.assertFalse(any(self.c.get_connection_status()['desired_outputs'].values()))

    def test_failed_freezer_write_does_not_skip_camera_or_lamp(self):
        self.c.camera_power_on()
        self.c.lamp_on()
        self.hw.fail_write_bit = 3
        record = self.c.ensure_safe_outputs_off()
        self.assertFalse(record['safe_outputs_off_confirmed'])
        self.assertEqual(self.hw.bits[2], 0)
        self.assertEqual(self.hw.bits[0], 0)

    def test_readback_mismatch_is_not_confirmed(self):
        self.hw.bad_readback = True
        self.assertFalse(self.c.ensure_safe_outputs_off()['safe_outputs_off_confirmed'])

    def test_shutdown_latches_off_across_later_reconnection(self):
        self.c.ensure_safe_outputs_off()
        with self.assertRaises(RuntimeError): self.c.camera_power_on()
        self.hw.fail_next_read = 103
        self.c.read_all()
        self.assertEqual(self.hw.bits, {3: 0, 0: 0, 2: 0})

    def test_active_low_outputs(self):
        config.CAMERA_POWER_ACTIVE_STATE = config.FREEZER_ACTIVE_STATE = 0
        record = self.c.ensure_safe_outputs_off()
        self.assertTrue(record['safe_outputs_off_confirmed'])
        self.assertEqual(self.hw.bits, {3: 1, 0: 0, 2: 1})

    def test_disabled_outputs_are_excluded_from_confirmation(self):
        config.CAMERA_POWER_CONTROL_ENABLED = False
        record = self.c.ensure_safe_outputs_off()
        self.assertIn('camera', record['disabled_outputs'])
        self.assertTrue(record['safe_outputs_off_confirmed'])

    def test_partial_connect_failure_releases_handle(self):
        self.hw.fail_write_bit = 3
        with self.assertRaises(ULException): self.c._open()
        self.assertTrue(self.hw.devices[-1].released)
        self.assertIsNone(self.c.daq_device)

    def test_direct_controller_threads_are_serialized(self):
        errors = []
        def run(fn):
            try:
                for _ in range(10): fn()
            except Exception as exc: errors.append(exc)
        threads = [threading.Thread(target=run, args=(fn,)) for fn in
                   (self.c.read_all, self.c.is_hall_active, self.c.lamp_off)]
        for thread in threads: thread.start()
        for thread in threads: thread.join()
        self.assertFalse(errors)
        self.assertFalse(self.hw.overlap)

    def test_background_logger_stop_serializes_disconnect(self):
        with tempfile.TemporaryDirectory() as directory:
            logger = TemperatureLogger(Path(directory) / 'log.jsonl', .001)
            logger.start()
            for _ in range(5): logger.is_hall_active()
            record = logger.stop()
            self.assertTrue(record['safe_outputs_off_confirmed'])
            self.assertFalse(logger._thread.is_alive())
            self.assertFalse(logger.get_connection_status()['connected'])
            self.assertFalse(self.hw.overlap)


class CameraTests(unittest.TestCase):
    def test_ssh_uses_stdin_and_timeout_is_a_failed_attempt(self):
        stream = CameraKeepaliveStream()
        with patch('subprocess.run', side_effect=subprocess.TimeoutExpired('ssh', 10)) as run:
            result = stream._run_ssh('echo READY', timeout=10)
        self.assertEqual(result.returncode, 124)
        self.assertEqual(run.call_args.kwargs['input'], 'echo READY')
        self.assertEqual(run.call_args.args[0][-2:], ['bash', '-s'])

    def test_readiness_recovers_after_ssh_timeout(self):
        stream = CameraKeepaliveStream(device_ready_poll_s=0)
        results = [subprocess.CompletedProcess([], 124, '', 'timeout'),
                   subprocess.CompletedProcess([], 0, 'DEVICE_READY', '')]
        with patch.object(stream, '_run_ssh', side_effect=results), patch('time.sleep'):
            self.assertTrue(stream.wait_until_device_ready()['ready'])

    def test_start_retries_failed_stream(self):
        stream = CameraKeepaliveStream(start_max_attempts=2, startup_wait_s=0,
                                       start_retry_delay_s=0)
        with patch.object(stream, '_cleanup_stale'), \
             patch.object(stream, 'wait_until_device_ready', return_value={'ready': True}), \
             patch.object(stream, '_start_once', return_value={'pid': '123', 'returncode': 0}), \
             patch.object(stream, 'status', side_effect=[{'running': False}, {'running': True}]), \
             patch.object(stream, 'log_tail', return_value=''):
            event = stream.start()
        self.assertTrue(event['running'])
        self.assertEqual(event['attempt_count'], 2)


class RunnerTests(unittest.TestCase):
    def run_cycle(self, directory, *, safe=True, failure=None, startup_recovery=False):
        self.stream = Mock()
        self.stream.start.return_value = {"running": False}
        self.stream.stop.return_value = {}
        logger = Mock()
        logger.camera_power_on.return_value = {}
        record = {'safe_outputs_off_confirmed': safe}
        logger.ensure_safe_outputs_off.return_value = record
        logger.stop.return_value = record
        logger.get_connection_status.return_value = {'connected': False}
        with patch.object(runner, 'create_test_folder', return_value=Path(directory)), \
             patch.object(runner, 'check_storage', return_value={}), \
             patch.object(runner, 'TemperatureLogger', return_value=logger), \
             patch.object(runner, 'wait_for_first_temperature_record', side_effect=failure), \
             patch.object(runner, 'precool_freezer', return_value={}), \
             patch.object(runner, 'CAMERA_KEEPALIVE_STREAM_ENABLED', startup_recovery), \
             patch.object(runner, 'CameraKeepaliveStream', return_value=self.stream), \
             patch.object(runner, 'CAMERA_AUTO_RECOVERY_ENABLED', True), \
             patch.object(runner, 'recover_camera_capture_path', return_value={'status': 'success'}), \
             patch.object(runner, 'CAMERA_POWER_CONTROL_ENABLED', True), \
             patch.object(runner, 'CAMERA_AUTO_RECOVERY_MAX_PER_TEST', 3), \
             patch.object(runner, 'REPEAT_CONTINUE_AFTER_FAILURE', False), \
             patch.object(runner, 'CAMERA_POWER_BOOT_WAIT_S', 0), \
             patch.object(runner, 'TEST_END_MODE', 'time'), \
             patch.object(runner, 'MAX_SWEEPS', 0):
            return runner.run_one_test(1, 1, 'group_20261102')

    def test_success_records_shutdown(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.run_cycle(directory)
            self.assertEqual(result['status'], 'completed')
            self.assertTrue(result['final_safe_output_shutdown_record']['safe_outputs_off_confirmed'])

    def test_unconfirmed_shutdown_overrides_success(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(runner.UnsafeShutdownError):
                self.run_cycle(directory, safe=False)
            summary = json.loads((Path(directory) / 'test_summary.json').read_text())
            self.assertEqual(summary['status'], 'unsafe_shutdown')

    def test_exception_and_interrupt_still_shutdown(self):
        for failure in (RuntimeError('start failed'), KeyboardInterrupt()):
            with self.subTest(failure=type(failure)), tempfile.TemporaryDirectory() as directory:
                with self.assertRaises(type(failure)):
                    self.run_cycle(directory, failure=failure)
                summary = json.loads((Path(directory) / 'test_summary.json').read_text())
                self.assertTrue(summary['final_safe_output_shutdown_record']['safe_outputs_off_confirmed'])
                self.assertEqual(summary['status'], 'aborted')

    def test_unsafe_shutdown_stops_repeats_even_when_continue_enabled(self):
        with patch.object(runner, 'REPEAT_CONTINUE_AFTER_FAILURE', True), \
             patch.object(runner, 'REPEAT_TEST_COUNT', 3), \
             patch.object(runner, 'repeat_stop_file_exists', return_value=False), \
             patch.object(runner, 'run_one_test', side_effect=runner.UnsafeShutdownError('unknown')) as run, \
             patch.object(runner.signal, 'signal'):
            runner.main()
        self.assertEqual(run.call_count, 1)

    def test_precool_off_failure_prevents_freezer_on(self):
        logger = Mock()
        logger.camera_power_off.side_effect = RuntimeError('camera off failed')
        with patch.object(runner, 'PRECOOL_BEFORE_TEST_ENABLED', True), \
             patch.object(runner, 'FREEZER_CONTROL_ENABLED', True), \
             patch.object(runner, 'CAMERA_POWER_CONTROL_ENABLED', True), \
             patch.object(runner, 'append_event'):
            with self.assertRaises(RuntimeError):
                runner.precool_freezer(logger, Path('/tmp'), Path('/tmp/log'), Path('/tmp/summary'), {})
        logger.freezer_on.assert_not_called()

    def test_startup_recovery_counts_toward_test_limit(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.run_cycle(directory, startup_recovery=True)
        self.assertEqual(result['camera_auto_recovery_count'], 1)
        self.assertEqual(len(result['camera_auto_recovery_events']), 1)
        self.assertEqual(result['camera_auto_recovery_events'][0]['recovery_context'],
                         'measurement_start_keepalive')

    def test_disk_error_cannot_bypass_unsafe_shutdown(self):
        original = runner.write_json
        def write(path, data):
            if data.get('status') == 'unsafe_shutdown':
                raise OSError('disk full')
            original(path, data)
        with tempfile.TemporaryDirectory() as directory, patch.object(runner, 'write_json', write):
            with self.assertRaises(runner.UnsafeShutdownError):
                self.run_cycle(directory, safe=False)

    def test_keepalive_restart_failure_marks_sweep_failed_and_cleans_up(self):
        stream, wheel, lamp_off = Mock(), Mock(), Mock()
        stream.stop.return_value = {}
        stream.start.return_value = {'running': False}
        with tempfile.TemporaryDirectory() as directory, \
             patch.object(sweep, 'FilterwheelController', return_value=wheel), \
             patch.object(sweep, 'FILTER_POSITIONS', {}), \
             patch.object(sweep, 'remote_make_dir'), \
             patch.object(sweep, 'remote_read_camera_temperatures', return_value={}), \
             patch.object(sweep, 'CAMERA_KEEPALIVE_RESTART_AFTER_SWEEP', True), \
             patch.object(sweep.time, 'sleep'):
            with self.assertRaisesRegex(RuntimeError, 'failed to restart'):
                sweep.run_single_sweep(Path(directory), 1, camera_keepalive_stream=stream,
                                       lamp_on_callback=Mock(), lamp_off_callback=lamp_off)
            summary = json.loads(next(Path(directory).glob('*/sweep_summary.json')).read_text())
        self.assertEqual(summary['status'], 'failed')
        lamp_off.assert_called_once()
        wheel.shutdown.assert_called_once()

    def test_no_camera_warm_start_symbols(self):
        for filename in ('Config/system_config.py', 'Scripts/run_long_test.py'):
            self.assertNotIn('PRECOOL_CAMERA_WARM_START', Path(filename).read_text())


if __name__ == '__main__':
    unittest.main()
