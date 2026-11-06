import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
import observer_control as c


def state(alive=True, ready=True, count=0, session='new'):
    return {'alive': alive, 'snapshot': {'state': 'monitoring' if ready else 'starting',
            'ready': ready, 'redirects': count, 'session': session}}


class ObserverControlTests(unittest.TestCase):
    def test_repeat_start_does_not_launch_another_process_or_inject_home(self):
        with patch.object(c, 'status', return_value=state()), patch.object(c, 'run') as run:
            self.assertTrue(c.start('adb', 'stick', Mock())['alive'])
            run.assert_not_called()

    def test_start_requires_native_counter_and_verified_foreground(self):
        records = []
        values = [state(alive=False, session='old'), state(), state(), state(count=1)]
        with patch.object(c, 'status', side_effect=values), patch.object(c, 'run', return_value='Started') as run, \
             patch.object(c, 'wait_for_firecube', return_value=(True, [c.TARGET])), patch.object(c.time, 'sleep'):
            value = c.start('adb', 'stick', lambda event, **kw: records.append(event))
        self.assertEqual(value['snapshot']['redirects'], 1)
        self.assertIn('device_home_test_verified', records)
        self.assertTrue(any(call.args[2:] == ('shell', 'input', 'keyevent', '3') for call in run.call_args_list))

    def test_absent_counter_increment_is_failure_and_stops_observer(self):
        values = [state(alive=False, session='old')] + [state()] * 42
        with patch.object(c, 'status', side_effect=values), patch.object(c, 'run', return_value=''), \
             patch.object(c, 'wait_for_firecube', return_value=(True, [c.TARGET])), \
             patch.object(c.time, 'sleep'), patch.object(c, 'stop') as stop:
            with self.assertRaisesRegex(RuntimeError, 'redirection not verified'):
                c.start('adb', 'stick', Mock())
            stop.assert_called_once()

    def test_start_does_not_reuse_stale_ready_snapshot(self):
        with patch.object(c, 'status', return_value=state(alive=False, session='old')), \
             patch.object(c, 'run', return_value='') as run, patch.object(c.time, 'sleep'), patch.object(c, 'stop') as stop:
            with self.assertRaisesRegex(RuntimeError, 'readiness not verified'):
                c.start('adb', 'stick', Mock())
            stop.assert_called_once()
            self.assertFalse(any(call.args[2:] == ('shell', 'input', 'keyevent', '3') for call in run.call_args_list))

    def test_stop_requires_lock_release(self):
        with patch.object(c, 'native'), patch.object(c, 'status', return_value=state()), patch.object(c.time, 'sleep'):
            with self.assertRaisesRegex(RuntimeError, 'stop not verified'):
                c.stop('adb', 'stick', Mock())
        with patch.object(c, 'native'), patch.object(c, 'status', return_value=state(alive=False)):
            self.assertFalse(c.stop('adb', 'stick', Mock())['alive'])

    def test_unknown_native_modes_never_reach_adb(self):
        with patch.object(c, 'run') as run:
            with self.assertRaises(ValueError):
                c.native('adb', 'stick', 'serve')
            run.assert_not_called()

    def test_bad_payload_hash_does_not_touch_device(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / 'tool.apk'; p.write_bytes(b'bad')
            with patch.object(c, 'run') as run:
                with self.assertRaisesRegex(RuntimeError, 'checksum mismatch'):
                    c.stage('adb', 'stick', p)
                run.assert_not_called()

    def test_verified_stage_uses_atomic_rename_and_never_truncates_live_path(self):
        with tempfile.TemporaryDirectory() as folder:
            payload = Path(folder) / 'tool.apk'; payload.write_bytes(b'fixture')
            def run(adb, serial, *args):
                if args[0] == 'pull':
                    Path(args[2]).write_bytes(b'fixture')
                return ''
            with patch.object(c, 'run', side_effect=run) as calls, \
                 patch.object(c, 'PAYLOAD_SHA256', hashlib.sha256(b'fixture').hexdigest()):
                c.stage('adb', 'stick', payload)
            self.assertEqual(calls.call_args_list[-1].args[2:], ('shell', 'mv', c.REMOTE + '.stage', c.REMOTE))
            self.assertFalse(any(call.args[2] == 'push' and call.args[-1] == c.REMOTE for call in calls.call_args_list))

    def test_boot_helper_bad_hash_is_rejected_before_install(self):
        with tempfile.TemporaryDirectory() as folder:
            apk = Path(folder) / 'helper.apk'; apk.write_bytes(b'bad')
            with patch.object(c, 'run') as run:
                with self.assertRaisesRegex(RuntimeError, 'checksum mismatch'):
                    c.install_boot_helper('adb', 'stick', apk, Mock())
                run.assert_not_called()

    def test_boot_helper_install_is_user_zero_and_verified_by_readback(self):
        with tempfile.TemporaryDirectory() as folder:
            apk = Path(folder) / 'helper.apk'; apk.write_bytes(b'fixture')
            def adb(adb, serial, *args):
                if args[0] == 'install': return 'Success'
                if args[:3] == ('shell', 'pm', 'path'): return 'package:/data/app/helper/base.apk'
                if args[0] == 'pull': Path(args[2]).write_bytes(b'fixture')
                return ''
            with patch.object(c, 'BOOT_HELPER_SHA256', hashlib.sha256(b'fixture').hexdigest()), \
                 patch.object(c, 'status', return_value=state()), patch.object(c, 'run', side_effect=adb) as run:
                result = c.install_boot_helper('adb', 'stick', apk, Mock())
            self.assertTrue(result['installed_verified'])
            self.assertFalse(result['reboot_autostart_verified'])
            self.assertTrue(any(call.args[2:6] == ('install', '--user', '0', '-r') for call in run.call_args_list))
