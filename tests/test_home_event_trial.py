import unittest
import io
from unittest.mock import Mock, patch
import home_event_trial as t

HOME = 'com.amazon.tv.launcher/.ui.HomeActivity_vNext'
LINE = '11-05 19:05:30.123  456  789 I am_resume_activity: [0,123,7,' + HOME + ']'


class HomeEventTests(unittest.TestCase):
    def test_only_exact_user_zero_home_resume_is_accepted(self):
        self.assertTrue(t.home_event(LINE))
        for line in [LINE.replace('[0,', '[10,'), LINE.replace(HOME, t.TARGET),
                     LINE.replace(HOME, HOME + 'Other'), LINE.replace('am_resume_activity', 'am_on_resume_called'),
                     LINE.replace('0,123,7,', '0,7,')]:
            self.assertFalse(t.home_event(line))

    def test_resumed_requires_unambiguous_user_zero(self):
        line = 'mResumedActivity: ActivityRecord{a u0 ' + HOME + ' t9}'
        self.assertEqual(t.resumed_component(line), HOME)
        self.assertIsNone(t.resumed_component(line.replace('u0', 'u10')))
        self.assertIsNone(t.resumed_component(line + '\n' + line))
        self.assertIsNone(t.resumed_component('mResumedActivity: null'))

    def test_stale_home_event_never_steals_streaming_foreground(self):
        launch = Mock()
        handler = t.Redirector(lambda: 'com.netflix.ninja/.MainActivity', launch, Mock())
        self.assertFalse(handler.handle(LINE))
        launch.assert_not_called()

    def test_loop_stops_instead_of_repeated_launches(self):
        launch = Mock()
        handler = t.Redirector(lambda: HOME, launch, Mock(), now=lambda: 10)
        self.assertTrue(handler.handle(LINE))
        with self.assertRaisesRegex(RuntimeError, 'loop'):
            handler.handle(LINE)
        self.assertEqual(launch.call_count, 1)

    def test_redirect_budget_is_enforced(self):
        launch = Mock()
        handler = t.Redirector(lambda: HOME, launch, Mock(), now=lambda: handler.count * 2)
        for _ in range(8):
            self.assertTrue(handler.handle(LINE))
        with self.assertRaisesRegex(RuntimeError, 'limit'):
            handler.handle(LINE)
        self.assertEqual(launch.call_count, 8)

    def test_wrong_build_stops_before_any_key_launch_or_stream(self):
        def run(adb, serial, *args):
            return 'device' if args == ('get-state',) else 'wrong'
        with patch.object(t, 'run', side_effect=run), patch.object(t.subprocess, 'Popen') as process:
            with self.assertRaisesRegex(RuntimeError, 'requires'):
                t.trial('adb', 'stick', Mock())
            process.assert_not_called()

    def test_no_home_event_never_launches(self):
        foreground, launch = Mock(), Mock()
        handler = t.Redirector(foreground, launch, Mock())
        self.assertFalse(handler.handle('unrelated log entry'))
        foreground.assert_not_called()
        launch.assert_not_called()

    def stream_test(self, content, foregrounds):
        process = Mock()
        process.stdout = io.StringIO(content)
        process.returncode = 0
        process.wait.return_value = 0
        records = []
        foreground = iter(foregrounds)
        def adb(adb, serial, *args):
            if args == ('shell', 'dumpsys', 'activity', 'activities'):
                return 'mResumedActivity: ActivityRecord{a u0 ' + next(foreground) + ' t9}'
            return ''
        with patch.object(t, 'check_device'), patch.object(t, 'run', side_effect=adb) as run, \
             patch.object(t.secrets, 'token_hex', return_value='freshmarker'), \
             patch.object(t.subprocess, 'Popen', return_value=process):
            with self.assertRaises(RuntimeError):
                t.trial('adb', 'stick', lambda event, **fields: records.append((event, fields)))
        process.terminate.assert_called_once()
        self.assertTrue(process.stdout.closed)
        return records, run.call_args_list

    def test_no_fresh_marker_ignores_old_home_and_never_injects_key(self):
        records, calls = self.stream_test(LINE + '\n', [t.TARGET])
        self.assertNotIn('fresh_stream_ready', [row[0] for row in records])
        self.assertFalse(any(call.args[2:] == ('shell', 'input', 'keyevent', '3') for call in calls))
        self.assertEqual(sum('am' in call.args for call in calls), 1)  # Initial explicit open only

    def test_fresh_event_redirect_verifies_foreground_and_stream_is_cleaned_up(self):
        content = LINE + '\n11-05 19:05:31.123  1  2 I FirecubeEventTrial: freshmarker\n' + LINE + '\n'
        records, calls = self.stream_test(content, [t.TARGET, HOME, t.TARGET])
        events = [row[0] for row in records]
        self.assertIn('automatic_home_test_passed', events)
        self.assertIn('pc_logcat_client_stopped', events)
        self.assertEqual(sum('am' in call.args for call in calls), 2)

    def test_delayed_launch_waits_instead_of_failing_on_first_snapshot(self):
        foreground = Mock(side_effect=[HOME, None, t.TARGET])
        with patch.object(t.time, 'sleep') as sleep:
            seen, observations = t.wait_for_firecube(foreground)
        self.assertTrue(seen)
        self.assertEqual(observations, [HOME, None, t.TARGET])
        self.assertEqual(sleep.call_count, 2)

    def test_launch_timeout_preserves_evidence_and_is_bounded(self):
        foreground = Mock(return_value=HOME)
        with patch.object(t.time, 'sleep') as sleep:
            seen, observations = t.wait_for_firecube(foreground)
        self.assertFalse(seen)
        self.assertEqual(observations, [HOME])
        self.assertEqual(foreground.call_count, 24)
        self.assertEqual(sleep.call_count, 23)

    def test_initial_failure_records_actual_foreground_without_starting_monitor(self):
        records = []
        def adb(adb, serial, *args):
            if args == ('shell', 'dumpsys', 'activity', 'activities'):
                return 'mResumedActivity: ActivityRecord{a u0 ' + HOME + ' t9}'
            return 'Starting: Intent { cmp=dev.firecube.launcher/.MainActivity }'
        with patch.object(t, 'check_device'), patch.object(t, 'run', side_effect=adb), \
             patch.object(t.time, 'sleep'), patch.object(t.subprocess, 'Popen') as stream:
            with self.assertRaisesRegex(RuntimeError, '24 checks'):
                t.trial('adb', 'stick', lambda event, **fields: records.append((event, fields)))
            stream.assert_not_called()
        self.assertEqual(records[-1][0], 'initial_launch_observation')
        self.assertEqual(records[-1][1]['foreground_transitions'], [HOME])
        self.assertEqual(records[1][0], 'explicit_launch_result')
        self.assertIn('foreground_snapshot', [row[0] for row in records])
