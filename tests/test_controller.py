import unittest
from unittest.mock import Mock, PropertyMock, patch
from coax import PollAction, PowerOnResetCompletePollResponse, KeystrokePollResponse, ReceiveTimeout
from coax.protocol import TerminalId

import context

from oec.controller import Controller
from oec.session import SessionDisconnectedError
from oec.keyboard import KeyboardModifiers, Key
from oec.keymap_3278_2 import KEYMAP as KEYMAP_3278_2

TERMINAL_IDS = (TerminalId(0b11110100), 'c1348300')

class RunLoopTestCase(unittest.TestCase):
    def setUp(self):
        self.interface = Mock()

        self.session_mock = Mock()
        self.create_session_mock = Mock(return_value=self.session_mock)

        self.controller = Controller(self.interface, lambda terminal_id, extended_id: KEYMAP_3278_2, self.create_session_mock)

        self.controller.connected_poll_period = 1

        patcher = patch('oec.controller.poll')

        self.poll_mock = patcher.start()

        patcher = patch('oec.controller.poll_ack')

        self.poll_ack_mock = patcher.start()

        patcher = patch('oec.controller.read_terminal_ids')

        self.read_terminal_ids_mock = patcher.start()

        self.read_terminal_ids_mock.return_value = TERMINAL_IDS

        patcher = patch('oec.controller.load_control_register')

        self.load_control_register_mock = patcher.start()

        patcher = patch('oec.controller.time.perf_counter')

        self.perf_counter_mock = patcher.start()

        patcher = patch('oec.controller.time.sleep')

        self.sleep_mock = patcher.start()

        self.addCleanup(patch.stopall)

    def test_no_terminal(self):
        self._assert_run_loop(0, ReceiveTimeout, 0, False)
        self._assert_run_loop(1, ReceiveTimeout, 4, False)

        self.assertIsNone(self.controller.terminal)
        self.assertIsNone(self.controller.session)

    def test_terminal_attached(self):
        self._assert_run_loop(0, PowerOnResetCompletePollResponse(0xa), 0, True)
        self._assert_run_loop(0, None, 0, False)
        self._assert_run_loop(0.5, None, 0.5, False)

        self.assertIsNotNone(self.controller.terminal)
        self.assertIsNotNone(self.controller.session)

        self.controller.session.handle_host.assert_called()

    def test_keystroke(self):
        self._assert_run_loop(0, PowerOnResetCompletePollResponse(0xa), 0, True)
        self._assert_run_loop(0, KeystrokePollResponse(0b0110000010), 0, True)
        self._assert_run_loop(0, None, 0, False)

        self.assertIsNotNone(self.controller.terminal)
        self.assertIsNotNone(self.controller.session)

        self.controller.session.handle_key.assert_called_with(Key.LOWER_A, KeyboardModifiers.NONE, 96)

    def test_terminal_detached(self):
        self._assert_run_loop(0, PowerOnResetCompletePollResponse(0xa), 0, True)
        self._assert_run_loop(0, None, 0, False)
        self._assert_run_loop(0.5, ReceiveTimeout, 0.5, False)

        self.assertIsNone(self.controller.terminal)
        self.assertIsNone(self.controller.session)

        self.session_mock.terminate.assert_called()

    def test_session_disconnected(self):
        self.session_mock.handle_host.side_effect = [None, SessionDisconnectedError, None]

        self._assert_run_loop(0, PowerOnResetCompletePollResponse(0xa), 0, True)
        self._assert_run_loop(0, None, 0, False)
        self._assert_run_loop(0.5, None, 0.5, False)
        self._assert_run_loop(1.5, None, 0.5, False)

        self.assertIsNotNone(self.controller.terminal)
        self.assertIsNotNone(self.controller.session)

        self.assertEqual(self.create_session_mock.call_count, 2)

    def test_alarm(self):
        # Arrange
        self._assert_run_loop(0, PowerOnResetCompletePollResponse(0xa), 0, True)
        self._assert_run_loop(0, None, 0, False)

        self.assertIsNotNone(self.controller.terminal)

        # Act
        self.controller.terminal.sound_alarm()

        # Assert
        self._assert_run_loop(0.5, None, 0.5, False)

        self.assertEqual(self.poll_mock.call_args[0][1], PollAction.ALARM)

        self.assertFalse(self.controller.terminal.alarm)

    def test_toggle_cursor_blink(self):
        self._assert_run_loop(0, PowerOnResetCompletePollResponse(0xa), 0, True)

        self.assertFalse(self.controller.terminal.display.cursor_blink)

        self._assert_run_loop(0, KeystrokePollResponse(0b0101010010), 0, True)

        self.assertTrue(self.controller.terminal.display.cursor_blink)

        self.load_control_register_mock.assert_called()

        self.assertTrue(self.load_control_register_mock.call_args[0][1].cursor_blink)

        self.load_control_register_mock.reset_mock()

        self._assert_run_loop(0, KeystrokePollResponse(0b0101010010), 0, True)

        self.assertFalse(self.controller.terminal.display.cursor_blink)

        self.load_control_register_mock.assert_called()

        self.assertFalse(self.load_control_register_mock.call_args[0][1].cursor_blink)

    def test_toggle_cursor_reverse(self):
        self._assert_run_loop(0, PowerOnResetCompletePollResponse(0xa), 0, True)

        self.assertFalse(self.controller.terminal.display.cursor_reverse)

        self._assert_run_loop(0, KeystrokePollResponse(0b0100111110), 0, True)
        self._assert_run_loop(0, KeystrokePollResponse(0b0101010010), 0, True)
        self._assert_run_loop(0, KeystrokePollResponse(0b0100111110), 0, True)

        self.assertTrue(self.controller.terminal.display.cursor_reverse)

        self.load_control_register_mock.assert_called()

        self.assertTrue(self.load_control_register_mock.call_args[0][1].cursor_reverse)

        self.load_control_register_mock.reset_mock()

        self._assert_run_loop(0, KeystrokePollResponse(0b0100111110), 0, True)
        self._assert_run_loop(0, KeystrokePollResponse(0b0101010010), 0, True)
        self._assert_run_loop(0, KeystrokePollResponse(0b0100111110), 0, True)

        self.assertFalse(self.controller.terminal.display.cursor_reverse)

        self.load_control_register_mock.assert_called()

        self.assertFalse(self.load_control_register_mock.call_args[0][1].cursor_reverse)

    def test_toggle_clicker(self):
        self._assert_run_loop(0, PowerOnResetCompletePollResponse(0xa), 0, True)

        self.assertFalse(self.controller.terminal.keyboard.clicker)

        self._assert_run_loop(0, KeystrokePollResponse(0b0101011110), 0, True)
        self._assert_run_loop(0, None, 0, False)

        self.assertTrue(self.controller.terminal.keyboard.clicker)

        self.assertEqual(self.poll_mock.call_args[0][1], PollAction.ENABLE_KEYBOARD_CLICKER)

        self._assert_run_loop(0.5, KeystrokePollResponse(0b0101011110), 0.5, True)
        self._assert_run_loop(1, None, 0, False)

        self.assertFalse(self.controller.terminal.keyboard.clicker)

        self.assertEqual(self.poll_mock.call_args[0][1], PollAction.DISABLE_KEYBOARD_CLICKER)

    def _assert_run_loop(self, poll_time, poll_response, expected_delay, expected_poll_ack):
        # Arrange
        self.poll_mock.side_effect = [poll_response]

        self.poll_ack_mock.reset_mock()

        self.perf_counter_mock.side_effect = [poll_time, poll_time + expected_delay]

        self.sleep_mock.reset_mock()

        # Act
        self.controller._run_loop()

        # Assert
        if expected_delay > 0:
            self.sleep_mock.assert_called_once_with(expected_delay)
        else:
            self.sleep_mock.assert_not_called()

        if expected_poll_ack:
            self.poll_ack_mock.assert_called_once()
        else:
            self.poll_ack_mock.assert_not_called()
