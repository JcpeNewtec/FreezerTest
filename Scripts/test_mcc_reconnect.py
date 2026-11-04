"""Attended MCC network recovery test. All controlled outputs stay OFF.

Run: PYTHONPATH=. python3 Scripts/test_mcc_reconnect.py
Disconnect/reconnect only the MCC Ethernet cable, then stop with Ctrl+C.
"""
import json
import time
from Control.temperature_logger import TemperatureLogger


def main():
    logger = TemperatureLogger('mcc_reconnect_test.jsonl')
    try:
        logger.start()
        # Latch OFF: this diagnostic cannot subsequently turn any output ON.
        record = logger.ensure_safe_outputs_off()
        print(json.dumps(record, indent=2))
        if not record['safe_outputs_off_confirmed']:
            raise RuntimeError('Could not confirm outputs OFF')
        while True:
            try:
                print(json.dumps({'temperatures': logger.get_latest_record(),
                                  'hall_active': logger.is_hall_active(),
                                  'connection': logger.get_connection_status()}))
            except Exception as exc:
                print(f'MCC read failed: {exc}')
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        record = logger.stop()
        print(json.dumps(record, indent=2))
        if not record or not record.get('safe_outputs_off_confirmed', False):
            raise RuntimeError('CRITICAL: Could not confirm outputs OFF')


if __name__ == '__main__':
    main()
