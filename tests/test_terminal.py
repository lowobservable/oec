import unittest
from unittest.mock import Mock, patch
from coax import Feature, PollAction
from coax.protocol import TerminalId, TerminalType

import context

from oec.terminal import create_terminal, Terminal, UnsupportedTerminalError
from oec.display import Dimensions
from oec.keymap_3278_2 import KEYMAP as KEYMAP_3278_2

class TerminalSetupTestCase(unittest.TestCase):
    def setUp(self):
        self.interface = Mock()

        terminal_id = TerminalId(0b11110100)
        extended_id = 'c1348300'
        dimensions = Dimensions(24, 80)
        features = { }
        keymap = KEYMAP_3278_2

        self.terminal = Terminal(self.interface, terminal_id, extended_id, dimensions, features, keymap)

        self.terminal.display = Mock()

        patcher = patch('oec.terminal.load_control_register')

        self.load_control_register_mock = patcher.start()

        self.addCleanup(patch.stopall)

    def test(self):
        self.terminal.setup()

class TerminalPollTestCase(unittest.TestCase):
    def setUp(self):
        self.interface = Mock()

        terminal_id = TerminalId(0b11110100)
        extended_id = 'c1348300'
        dimensions = Dimensions(24, 80)
        features = { }
        keymap = KEYMAP_3278_2

        self.terminal = Terminal(self.interface, terminal_id, extended_id, dimensions, features, keymap)

        patcher = patch('oec.terminal.poll')

        self.poll_mock = patcher.start()

        self.addCleanup(patch.stopall)

        # The terminal will be initialized in a state where the terminal keyboard clicker
        # state is unknown, and this cannot be read. Therefore the first POLL will always
        # attempt to set the keyboard clicker state...
        self.terminal.poll()

        self.poll_mock.reset_mock()

    def test_with_no_queued_actions(self):
        # Act
        self.terminal.poll()

        # Assert
        self.poll_mock.assert_called_with(self.interface, PollAction.NONE)

    def test_with_sound_alarm_queued(self):
        # Arrange
        self.terminal.sound_alarm()

        # Act
        self.terminal.poll()

        # Assert
        self.poll_mock.assert_called_with(self.interface, PollAction.ALARM)

    def test_with_enable_keyboard_clicker_queued(self):
        # Arrange
        self.assertFalse(self.terminal.keyboard.clicker)

        self.terminal.keyboard.toggle_clicker()

        # Act
        self.terminal.poll()

        # Assert
        self.poll_mock.assert_called_with(self.interface, PollAction.ENABLE_KEYBOARD_CLICKER)

class CreateTerminalTestCase(unittest.TestCase):
    def setUp(self):
        self.interface = Mock()

        self.interface.legacy_firmware_detected = False

        self.get_keymap = lambda terminal_id, extended_id: KEYMAP_3278_2

        patcher = patch('oec.terminal.read_terminal_id')

        self.read_terminal_id_mock = patcher.start()

        patcher = patch('oec.terminal.read_extended_id')

        self.read_extended_id_mock = patcher.start()

        patcher = patch('oec.terminal.get_features')

        self.get_features_mock = patcher.start()

        self.addCleanup(patch.stopall)

    def test_supported_terminal(self):
        # Arrange
        self.read_terminal_id_mock.return_value = TerminalId(0b11110100)
        self.read_extended_id_mock.return_value = bytes.fromhex('c1 34 83 00')
        self.get_features_mock.return_value = { Feature.EAB: 7 }

        # Act
        terminal = create_terminal(self.interface, None, self.get_keymap)

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
        self.read_terminal_id_mock.return_value = TerminalId(0b00000001)

        # Act and assert
        with self.assertRaises(UnsupportedTerminalError):
            create_terminal(self.interface, None, self.get_keymap)

    def test_unsupported_terminal_model(self):
        # Arrange
        terminal_id = TerminalId(0b11110100)

        terminal_id.model = 1

        self.read_terminal_id_mock.return_value = terminal_id

        # Act and assert
        with self.assertRaises(UnsupportedTerminalError):
            create_terminal(self.interface, None, self.get_keymap)

    def test_eab_feature_removed_on_legacy_interface_without_strategy(self):
        # Arrange
        self.interface.legacy_firmware_detected = True

        self.read_terminal_id_mock.return_value = TerminalId(0b11110100)
        self.read_extended_id_mock.return_value = bytes.fromhex('c1 34 83 00')
        self.get_features_mock.return_value = { Feature.EAB: 7 }

        patcher = patch('oec.terminal._print_no_i1_eab_notice')

        print_no_i1_eab_notice_mock = patcher.start()

        # Act
        terminal = create_terminal(self.interface, None, self.get_keymap)

        # Assert
        self.assertEqual(terminal.terminal_id.type, TerminalType.CUT)
        self.assertEqual(terminal.terminal_id.model, 2)
        self.assertEqual(terminal.terminal_id.keyboard, 15)
        self.assertEqual(terminal.extended_id, 'c1348300')
        self.assertEqual(terminal.display.dimensions, Dimensions(24, 80))
        self.assertEqual(terminal.features, { })
        self.assertEqual(terminal.keyboard.keymap.name, '3278-2')

        print_no_i1_eab_notice_mock.assert_called_once()
