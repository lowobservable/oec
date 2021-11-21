import unittest
from unittest.mock import create_autospec
from coax import PollAction
from coax.protocol import TerminalId

import context

from oec.interface import InterfaceWrapper
from oec.device import UnsupportedDeviceError
from oec.terminal import Terminal
from oec.display import Display, StatusLine
from oec.keymap_3278_2 import KEYMAP as KEYMAP_3278_2

from mock_interface import MockInterface

class InitTerminalTestCase(unittest.TestCase):
    def test_supported_terminal_model(self):
        # Arrange
        terminal_id = TerminalId(0b11110100)

        # Act
        Terminal(None, None, terminal_id, None, { }, KEYMAP_3278_2)

    def test_unsupported_terminal_model(self):
        # Arrange
        terminal_id = TerminalId(0b11110100)

        terminal_id.model = 1

        # Act and assert
        with self.assertRaises(UnsupportedDeviceError):
            Terminal(None, None, terminal_id, None, { }, KEYMAP_3278_2)

class TerminalSetupTestCase(unittest.TestCase):
    def setUp(self):
        self.interface = MockInterface()

        self.terminal = _create_terminal(self.interface)

        self.terminal.display = create_autospec(Display, instance=True)
        self.terminal.display.status_line = create_autospec(StatusLine, instance=True)

    def test(self):
        self.terminal.setup()

class TerminalGetPollActionTestCase(unittest.TestCase):
    def setUp(self):
        self.interface = MockInterface()

        self.terminal = _create_terminal(self.interface)

        self.terminal.display = create_autospec(Display, instance=True)

        # The terminal will be initialized in a state where the terminal keyboard clicker
        # state is unknown, and this cannot be read. Therefore the first POLL will always
        # attempt to set the keyboard clicker state...
        self.terminal.get_poll_action()

    def test_with_no_queued_actions(self):
        self.assertEqual(self.terminal.get_poll_action(), PollAction.NONE)

    def test_with_sound_alarm_queued(self):
        # Arrange
        self.terminal.sound_alarm()

        # Act and assert
        self.assertEqual(self.terminal.get_poll_action(), PollAction.ALARM)

    def test_with_enable_keyboard_clicker_queued(self):
        # Arrange
        self.assertFalse(self.terminal.keyboard.clicker)

        self.terminal.keyboard.toggle_clicker()

        # Act and assert
        self.assertEqual(self.terminal.get_poll_action(), PollAction.ENABLE_KEYBOARD_CLICKER)

def _create_terminal(interface):
    terminal_id = TerminalId(0b11110100)
    extended_id = 'c1348300'
    features = { }
    keymap = KEYMAP_3278_2

    terminal = Terminal(InterfaceWrapper(interface), None, terminal_id, extended_id, features, keymap)

    return terminal
