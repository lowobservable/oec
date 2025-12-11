import unittest
from unittest.mock import create_autospec
from coax import PollAction
from coax.protocol import TerminalId

import context

from oec.interface import InterfaceWrapper
from oec.device import UnsupportedDeviceError
from oec.terminal import Terminal, get_keyboard_description
from oec.display import Display, StatusLine
from oec.keymap_3278_typewriter import KEYMAP

from mock_interface import MockInterface

class InitTerminalTestCase(unittest.TestCase):
    def test_supported_terminal_model(self):
        # Arrange
        terminal_id = TerminalId(0b11110100)

        # Act
        Terminal(None, None, terminal_id, None, { }, KEYMAP)

    def test_unsupported_terminal_model(self):
        # Arrange
        terminal_id = TerminalId(0b11110100)

        terminal_id.model = 1

        # Act and assert
        with self.assertRaises(UnsupportedDeviceError):
            Terminal(None, None, terminal_id, None, { }, KEYMAP)

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

class GetKeyboardDescriptionTestCase(unittest.TestCase):
    def test(self):
        CASES = [
            (10, None, '3278-TYPEWRITER'),
            (0, 'c1347200', 'IBM-TYPEWRITER'),
            (10, '41347200', '3278-TYPEWRITER'),
            (0, 'c2347200', 'IBM-DATAENTRY'),
            (0, 'c3347200', 'IBM-APL'),
            (0, 'c1348301', 'IBM-ENHANCED'),
            (0, 'e1347200', 'USER-1'),
            (0, 'e4347200', 'USER-4')
        ]

        for (keyboard, extended_id, expected_description) in CASES:
            with self.subTest(keyboard=keyboard, extended_id=extended_id):
                terminal_id = TerminalId(0b0000_0100 | (keyboard << 4))

                description = get_keyboard_description(terminal_id, extended_id)

                self.assertEqual(description, expected_description)

def _create_terminal(interface):
    terminal_id = TerminalId(0b11110100)
    extended_id = 'c1348300'
    features = { }
    keymap = KEYMAP

    terminal = Terminal(InterfaceWrapper(interface), None, terminal_id, extended_id, features, keymap)

    return terminal
