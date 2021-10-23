import unittest
from unittest.mock import Mock, create_autospec, patch

import selectors
from selectors import BaseSelector
from logging import Logger
from coax import Poll, PollAction, PowerOnResetCompletePollResponse, KeystrokePollResponse, PollAck, ReceiveTimeout
from coax.protocol import TerminalId

import context

from oec.interface import InterfaceWrapper
from oec.controller import Controller
from oec.terminal import Terminal, UnsupportedTerminalError
from oec.display import Dimensions
from oec.keyboard import KeyboardModifiers, Key
from oec.keymap_3278_2 import KEYMAP as KEYMAP_3278_2
from oec.session import Session, SessionDisconnectedError

from mock_interface import MockInterface

class RunLoopTestCase(unittest.TestCase):
    def setUp(self):
        self.interface = MockInterface()

        self.session = create_autospec(Session, instance=True)
        self.create_session = Mock(return_value=self.session)

        self.controller = Controller(InterfaceWrapper(self.interface), lambda terminal_id, extended_id: KEYMAP_3278_2, self.create_session)

        self.controller.logger = create_autospec(Logger, instance=True)

        self.controller.connected_poll_period = 1

        self.controller.session_selector = create_autospec(BaseSelector, instance=True)

        self.controller._update_session = Mock()

        self.terminal = Terminal(self.interface, None, TerminalId(0b11110100), 'c1348300', Dimensions(24, 80), { }, KEYMAP_3278_2)

        self.terminal.setup = Mock()

        self.terminal.display.write = Mock()
        self.terminal.display.toggle_cursor_blink = Mock()
        self.terminal.display.toggle_cursor_reverse = Mock()

        self.terminal.keyboard.toggle_clicker = Mock()

        patcher = patch('oec.controller.time.perf_counter')

        self.perf_counter = patcher.start()

        patcher = patch('oec.controller.time.sleep')

        self.sleep = patcher.start()

        patcher = patch('oec.controller.create_terminal')

        self.create_terminal = patcher.start()

        self.create_terminal.return_value = self.terminal

        self.addCleanup(patch.stopall)

    def test_no_terminal(self):
        self._assert_run_loop(0, ReceiveTimeout, False, 0, False)
        self._assert_run_loop(1, ReceiveTimeout, False, 4, False)

        self.assertIsNone(self.controller.terminal)
        self.assertIsNone(self.controller.session)

    def test_terminal_attached(self):
        self._assert_run_loop(0, PowerOnResetCompletePollResponse(0xa), False, 0, True)
        self._assert_run_loop(0, None, False, 0, False)
        self._assert_run_loop(0.5, None, True, 0.5, False)

        self.assertIsNotNone(self.controller.terminal)
        self.assertIsNotNone(self.controller.session)

        self.controller._update_session.assert_called()

    def test_unsupported_terminal_attached(self):
        self.create_terminal.side_effect = [UnsupportedTerminalError]

        self._assert_run_loop(0, PowerOnResetCompletePollResponse(0xa), False, 0, True)

        self.assertIsNone(self.controller.terminal)
        self.assertIsNone(self.controller.session)

    def test_keystroke(self):
        self._assert_run_loop(0, PowerOnResetCompletePollResponse(0xa), False, 0, True)
        self._assert_run_loop(0, KeystrokePollResponse(0b0110000010), False, 0, True)
        self._assert_run_loop(0, None, False, 0, False)
        self._assert_run_loop(0.5, None, True, 0.5, False)

        self.assertIsNotNone(self.controller.terminal)
        self.assertIsNotNone(self.controller.session)

        self.controller.session.handle_key.assert_called_with(Key.LOWER_A, KeyboardModifiers.NONE, 96)

    def test_terminal_detached(self):
        self._assert_run_loop(0, PowerOnResetCompletePollResponse(0xa), False, 0, True)
        self._assert_run_loop(0, None, False, 0, False)
        self._assert_run_loop(0.5, ReceiveTimeout, True, 0.5, False)

        self.assertIsNone(self.controller.terminal)
        self.assertIsNone(self.controller.session)

        self.session.terminate.assert_called()

    def test_session_disconnected(self):
        self.controller._update_session.side_effect = [None, SessionDisconnectedError, None]

        self._assert_run_loop(0, PowerOnResetCompletePollResponse(0xa), False, 0, True)
        self._assert_run_loop(0, None, False, 0, False)
        self._assert_run_loop(0.5, None, True, 0.5, False)
        self._assert_run_loop(1.5, None, True, 0.5, False)

        self.assertIsNotNone(self.controller.terminal)
        self.assertIsNotNone(self.controller.session)

        self.assertEqual(self.create_session.call_count, 2)

    def test_toggle_cursor_blink(self):
        self._assert_run_loop(0, PowerOnResetCompletePollResponse(0xa), False, 0, True)

        self._assert_run_loop(0, KeystrokePollResponse(0b0101010010), False, 0, True)

        self.terminal.display.toggle_cursor_blink.assert_called_once()

        self.terminal.display.toggle_cursor_blink.reset_mock()

        self._assert_run_loop(0, KeystrokePollResponse(0b0101010010), False, 0, True)

        self.terminal.display.toggle_cursor_blink.assert_called_once()

    def test_toggle_cursor_reverse(self):
        self._assert_run_loop(0, PowerOnResetCompletePollResponse(0xa), False, 0, True)

        self._assert_run_loop(0, KeystrokePollResponse(0b0100111110), False, 0, True)
        self._assert_run_loop(0, KeystrokePollResponse(0b0101010010), False, 0, True)
        self._assert_run_loop(0, KeystrokePollResponse(0b0100111110), False, 0, True)

        self.terminal.display.toggle_cursor_reverse.assert_called_once()

        self.terminal.display.toggle_cursor_reverse.reset_mock()

        self._assert_run_loop(0, KeystrokePollResponse(0b0100111110), False, 0, True)
        self._assert_run_loop(0, KeystrokePollResponse(0b0101010010), False, 0, True)
        self._assert_run_loop(0, KeystrokePollResponse(0b0100111110), False, 0, True)

        self.terminal.display.toggle_cursor_reverse.assert_called_once()

    def test_toggle_clicker(self):
        self._assert_run_loop(0, PowerOnResetCompletePollResponse(0xa), False, 0, True)

        self._assert_run_loop(0, KeystrokePollResponse(0b0101011110), False, 0, True)
        self._assert_run_loop(0, None, False, 0, False)

        self.terminal.keyboard.toggle_clicker.assert_called_once()

        self.terminal.keyboard.toggle_clicker.reset_mock()

        self._assert_run_loop(0.5, KeystrokePollResponse(0b0101011110), True, 0.5, True)
        self._assert_run_loop(1, None, False, 0, False)

        self.terminal.keyboard.toggle_clicker.assert_called_once()

    def _assert_run_loop(self, poll_time, poll_response, expected_update_session, expected_poll_delay, expected_poll_ack):
        # Arrange
        self.controller._update_session.reset_mock()

        self.interface.mock_responses = [(None, Poll, None, poll_response)]

        self.interface.reset_mock()

        self.perf_counter.side_effect = [poll_time, poll_time + expected_poll_delay]

        self.sleep.reset_mock()

        # Act
        self.controller._run_loop()

        # Assert
        if expected_update_session:
            self.controller._update_session.assert_called_once_with(expected_poll_delay)
            self.sleep.assert_not_called()
        else:
            self.controller._update_session.assert_not_called()

            if expected_poll_delay > 0:
                self.sleep.assert_called_once_with(expected_poll_delay)
            else:
                self.sleep.assert_not_called()

        if expected_poll_ack:
            self.interface.assert_command_executed(None, PollAck)
        else:
            self.interface.assert_command_not_executed(None, PollAck)

class UpdateSessionTestCase(unittest.TestCase):
    def setUp(self):
        self.controller = Controller(None, None, None)

        self.controller.session = create_autospec(Session, instance=True)

        self.controller.session_selector = create_autospec(BaseSelector, instance=True)

        patcher = patch('oec.controller.time.perf_counter')

        self.perf_counter = patcher.start()

    def test_zero_duration(self):
        # Act
        self.controller._update_session(0)

        # Assert
        self.controller.session.handle_host.assert_not_called()
        self.controller.session.render.assert_not_called()

        self.controller.session_selector.select.assert_not_called()

    def test_select_timeout(self):
        # Arrange
        self.controller.session_selector.select.return_value = []

        # Act
        self.controller._update_session(1)

        # Assert
        self.controller.session.handle_host.assert_not_called()
        self.controller.session.render.assert_not_called()

        self.controller.session_selector.select.assert_called_once()

    def test_select_available(self):
        # Arrange
        self.perf_counter.side_effect = [0, 0.75, 0.75]

        selector_key = Mock(fileobj=self.controller.session)

        self.controller.session_selector.select.side_effect = [[(selector_key, selectors.EVENT_READ)], []]

        # Act
        self.controller._update_session(1)

        # Assert
        self.controller.session.handle_host.assert_called_once()
        self.controller.session.render.assert_called_once()

        self.assertEqual(self.controller.session_selector.select.call_count, 2)

        call_args_list = self.controller.session_selector.select.call_args_list

        self.assertEqual(call_args_list[0][0][0], 1)
        self.assertEqual(call_args_list[1][0][0], 0.25)
