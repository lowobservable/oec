import unittest
from unittest.mock import Mock, create_autospec
from coax import Poll, PollAction, TerminalType, Feature, ReadTerminalId, ReadExtendedId, ReadFeatureId
from coax.protocol import TerminalId

import context

from oec.interface import InterfaceWrapper
from oec.terminal import create_terminal, Terminal, UnsupportedTerminalError
from oec.display import Display, Dimensions
from oec.keymap_3278_2 import KEYMAP as KEYMAP_3278_2

from mock_interface import MockInterface

class TerminalSetupTestCase(unittest.TestCase):
    def setUp(self):
        self.interface = MockInterface()

        self.terminal = _create_terminal(self.interface)

        self.terminal.display = create_autospec(Display, instance=True)

    def test(self):
        self.terminal.setup()

class TerminalPollTestCase(unittest.TestCase):
    def setUp(self):
        self.interface = MockInterface()

        self.terminal = _create_terminal(self.interface)

        self.terminal.display = create_autospec(Display, instance=True)

        # The terminal will be initialized in a state where the terminal keyboard clicker
        # state is unknown, and this cannot be read. Therefore the first POLL will always
        # attempt to set the keyboard clicker state...
        self.terminal.poll()

        self.interface.reset_mock()

    def test_with_no_queued_actions(self):
        # Act
        self.terminal.poll()

        # Assert
        self.assert_poll_with_poll_action(PollAction.NONE)

    def test_with_sound_alarm_queued(self):
        # Arrange
        self.terminal.sound_alarm()

        # Act
        self.terminal.poll()

        # Assert
        self.assert_poll_with_poll_action(PollAction.ALARM)

    def test_with_enable_keyboard_clicker_queued(self):
        # Arrange
        self.assertFalse(self.terminal.keyboard.clicker)

        self.terminal.keyboard.toggle_clicker()

        # Act
        self.terminal.poll()

        # Assert
        self.assert_poll_with_poll_action(PollAction.ENABLE_KEYBOARD_CLICKER)

    def assert_poll_with_poll_action(self, action):
        self.interface.assert_command_executed(None, Poll, lambda command: command.action == action)

class CreateTerminalTestCase(unittest.TestCase):
    def setUp(self):
        self.interface = MockInterface()

        self.get_keymap = lambda terminal_id, extended_id: KEYMAP_3278_2

    def test_supported_terminal(self):
        # Arrange
        interface = InterfaceWrapper(self.interface)

        self.interface.mock_responses = [
            (None, ReadTerminalId, None, TerminalId(0b11110100)),
            (None, ReadExtendedId, None, bytes.fromhex('c1 34 83 00')),
            (None, ReadFeatureId, lambda command: command.feature_address == 7, Feature.EAB.value)
        ]

        # Act
        terminal = create_terminal(interface, None, None, self.get_keymap)

        # Assert
        self.assertEqual(terminal.terminal_id.type, TerminalType.CUT)
        self.assertEqual(terminal.terminal_id.model, 2)
        self.assertEqual(terminal.terminal_id.keyboard, 15)
        self.assertEqual(terminal.extended_id, 'c1348300')
        self.assertEqual(terminal.display.dimensions, Dimensions(24, 80))
        self.assertEqual(terminal.features, { Feature.EAB: 7 })
        self.assertEqual(terminal.keyboard.keymap.name, '3278-2')

    def test_unsupported_terminal_type(self):
        # Arrange
        interface = InterfaceWrapper(self.interface)

        self.interface.mock_responses = [(None, ReadTerminalId, None, TerminalId(0b00000001))]

        # Act and assert
        with self.assertRaises(UnsupportedTerminalError):
            create_terminal(interface, None, None, self.get_keymap)

    def test_unsupported_terminal_model(self):
        # Arrange
        interface = InterfaceWrapper(self.interface)
        terminal_id = TerminalId(0b11110100)

        terminal_id.model = 1

        self.interface.mock_responses = [(None, ReadTerminalId, None, terminal_id)]

        # Act and assert
        with self.assertRaises(UnsupportedTerminalError):
            create_terminal(interface, None, None, self.get_keymap)

def _create_terminal(interface):
    terminal_id = TerminalId(0b11110100)
    extended_id = 'c1348300'
    dimensions = Dimensions(24, 80)
    features = { }
    keymap = KEYMAP_3278_2

    terminal = Terminal(InterfaceWrapper(interface), None, terminal_id, extended_id, dimensions, features, keymap)

    return terminal
