import unittest
from unittest.mock import Mock, create_autospec, patch
from coax import Poll, PollAction, TerminalType, Feature, ReadTerminalId, ReadExtendedId, ReadFeatureId
from coax.protocol import TerminalId

import context

from oec.interface import InterfaceWrapper
from oec.terminal import create_terminal, Terminal, UnsupportedTerminalError, _jumbo_write_split_data
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

    def test_supported_terminal_with_no_features(self):
        # Arrange
        interface = InterfaceWrapper(self.interface)

        self.interface.mock_responses = [
            (None, ReadTerminalId, None, TerminalId(0b11110100)),
            (None, ReadExtendedId, None, bytes.fromhex('00 00 00 00'))
        ]

        # Act
        terminal = create_terminal(interface, None, None, self.get_keymap)

        # Assert
        self.assertEqual(terminal.terminal_id.type, TerminalType.CUT)
        self.assertEqual(terminal.terminal_id.model, 2)
        self.assertEqual(terminal.terminal_id.keyboard, 15)
        self.assertEqual(terminal.extended_id, '00000000')
        self.assertEqual(terminal.display.dimensions, Dimensions(24, 80))
        self.assertEqual(terminal.features, { })
        self.assertEqual(terminal.keyboard.keymap.name, '3278-2')

    def test_supported_terminal_with_eab_feature(self):
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

    def test_supported_terminal_features_override(self):
        # Arrange
        interface = InterfaceWrapper(self.interface)

        self.interface.mock_responses = [
            (None, ReadTerminalId, None, TerminalId(0b11110100)),
            (None, ReadExtendedId, None, bytes.fromhex('00 00 00 00'))
        ]

        # Act
        with patch.dict('oec.terminal.os.environ', { 'COAX_FEATURES': 'EAB@7' }):
            terminal = create_terminal(interface, None, None, self.get_keymap)

        # Assert
        self.assertEqual(terminal.terminal_id.type, TerminalType.CUT)
        self.assertEqual(terminal.terminal_id.model, 2)
        self.assertEqual(terminal.terminal_id.keyboard, 15)
        self.assertEqual(terminal.extended_id, '00000000')
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

class JumboWriteSplitDataTestCase(unittest.TestCase):
    def test_no_split_strategy(self):
        for data in [bytes(range(0, 64)), (bytes.fromhex('00'), 64)]:
            with self.subTest(data=data):
                result = _jumbo_write_split_data(data, None)

                self.assertEqual(len(result), 1)

                self.assertEqual(result[0], data)

    def test_split_strategy_one_chunk(self):
        for data in [bytes(range(0, 16)), (bytes.fromhex('00'), 16), bytes(range(0, 31)), (bytes.fromhex('00'), 31)]:
            with self.subTest(data=data):
                result = _jumbo_write_split_data(data, 32)

                self.assertEqual(len(result), 1)

                self.assertEqual(result[0], data)

    def test_split_strategy_two_chunks(self):
        for data in [bytes(range(0, 32)), (bytes.fromhex('00'), 32), bytes(range(0, 63)), (bytes.fromhex('00'), 63)]:
            with self.subTest(data=data):
                result = _jumbo_write_split_data(data, 32)

                self.assertEqual(len(result), 2)
                self.assertEqual(len(result[0]), 31)

    def test_split_strategy_three_chunks(self):
        for data in [bytes(range(0, 64)), (bytes.fromhex('00'), 64), bytes(range(0, 95)), (bytes.fromhex('00'), 95)]:
            with self.subTest(data=data):
                result = _jumbo_write_split_data(data, 32)

                self.assertEqual(len(result), 3)
                self.assertEqual(len(result[0]), 31)
                self.assertEqual(len(result[1]), 32)

def _create_terminal(interface):
    terminal_id = TerminalId(0b11110100)
    extended_id = 'c1348300'
    dimensions = Dimensions(24, 80)
    features = { }
    keymap = KEYMAP_3278_2

    terminal = Terminal(InterfaceWrapper(interface), None, terminal_id, extended_id, dimensions, features, keymap)

    return terminal
