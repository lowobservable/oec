import unittest
from unittest.mock import Mock, patch

import context

from oec.display import Dimensions
from oec.keyboard import Key, KeyboardModifiers
from oec.vt100 import VT100Session, select

class SessionHandleHostTestCase(unittest.TestCase):
    def setUp(self):
        self.terminal = Mock()

        self.terminal.display.dimensions = Dimensions(24, 80)

        self.session = VT100Session(self.terminal, None)

        self.session.host_process = Mock()

        patcher = patch('oec.vt100.select')

        select_mock = patcher.start()

        select_mock.return_value = [[self.session.host_process]]

        self.addCleanup(patch.stopall)

    def test(self):
        # Arrange
        self.session.host_process.read = Mock(return_value=b'abc')

        # Act
        self.session.handle_host()

        # Assert
        self.terminal.display.buffered_write.assert_any_call(0x80, row=0, column=0)
        self.terminal.display.buffered_write.assert_any_call(0x81, row=0, column=1)
        self.terminal.display.buffered_write.assert_any_call(0x82, row=0, column=2)

        self.terminal.display.flush.assert_called()

        self.terminal.display.move_cursor.assert_called_with(row=0, column=3)

        self.assertFalse(self.session.vt100_screen.dirty)

    def test_bell(self):
        # Arrange
        self.session.host_process.read = Mock(return_value=b'\a')

        # Act
        self.session.handle_host()

        # Assert
        self.terminal.sound_alarm.assert_called()

class SessionHandleKeyTestCase(unittest.TestCase):
    def setUp(self):
        self.terminal = Mock()

        self.terminal.display.dimensions = Dimensions(24, 80)

        self.session = VT100Session(self.terminal, None)

        self.session.host_process = Mock()

    def test_printable(self):
        # Act
        self.session.handle_key(Key.LOWER_A, KeyboardModifiers.NONE, None)

        # Assert
        self.session.host_process.write.assert_called_with(b'a')

    # TODO: Test the unprintable branch.

    def test_mapped(self):
        # Act
        self.session.handle_key(Key.ENTER, KeyboardModifiers.NONE, None)

        # Assert
        self.session.host_process.write.assert_called_with(b'\r')

    def test_mapped_alt_modifier(self):
        # Act
        self.session.handle_key(Key.LOWER_C, KeyboardModifiers.LEFT_ALT, None)

        # Assert
        self.session.host_process.write.assert_called_with(b'\x03')

    def test_unmapped_alt_modifier(self):
        # Arrange
        self.session.logger = Mock()

        # Act
        self.session.handle_key(Key.THREE, KeyboardModifiers.LEFT_ALT, None)

        # Assert
        self.session.host_process.write.assert_not_called()

        self.session.logger.warning.assert_called()

    def test_alt_modifier_with_modifier_key(self):
        # Act
        self.session.handle_key(Key.LEFT_ALT, KeyboardModifiers.LEFT_ALT, None)

        # Assert
        self.session.host_process.write.assert_not_called()
