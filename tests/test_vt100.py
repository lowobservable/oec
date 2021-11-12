import unittest
from unittest.mock import Mock, create_autospec

from logging import Logger
from ptyprocess import PtyProcess
from coax.protocol import TerminalId

import context

from oec.interface import InterfaceWrapper
from oec.terminal import Terminal
from oec.display import Dimensions, BufferedDisplay
from oec.keyboard import Key, KeyboardModifiers
from oec.keymap_3278_2 import KEYMAP as KEYMAP_3278_2
from oec.session import SessionDisconnectedError
from oec.vt100 import VT100Session

from mock_interface import MockInterface

class SessionHandleHostTestCase(unittest.TestCase):
    def setUp(self):
        self.interface = MockInterface()

        self.terminal = _create_terminal(self.interface)

        self.terminal.sound_alarm = Mock(wraps=self.terminal.sound_alarm)

        self.session = VT100Session(self.terminal, None)

        self.session.host_process = create_autospec(PtyProcess, instance=True)

    def test(self):
        # Arrange
        self.session.host_process.read = Mock(return_value=b'abc')

        # Act
        self.session.handle_host()

        # Assert
        row_buffer = self.session.vt100_screen.buffer[0]

        self.assertEqual(row_buffer[0].data, 'a')
        self.assertEqual(row_buffer[1].data, 'b')
        self.assertEqual(row_buffer[2].data, 'c')

    def test_eof(self):
        # Arrange
        self.session.host_process.read = Mock(side_effect=EOFError)

        # Act and assert
        with self.assertRaises(SessionDisconnectedError):
            self.session.handle_host()

        self.assertIsNone(self.session.host_process)

    def test_bell(self):
        # Arrange
        self.session.host_process.read = Mock(return_value=b'\a')

        # Act
        self.session.handle_host()

        # Assert
        self.terminal.sound_alarm.assert_called()

class SessionHandleKeyTestCase(unittest.TestCase):
    def setUp(self):
        self.interface = MockInterface()

        self.terminal = _create_terminal(self.interface)

        self.session = VT100Session(self.terminal, None)

        self.session.host_process = create_autospec(PtyProcess, instance=True)

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
        self.session.logger = create_autospec(Logger, instance=True)

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

class SessionRenderTestCase(unittest.TestCase):
    def setUp(self):
        self.interface = MockInterface()

        self.terminal = _create_terminal(self.interface)

        self.terminal.display.buffered_write_byte = Mock(wraps=self.terminal.display.buffered_write_byte)
        self.terminal.display.move_cursor = Mock(wraps=self.terminal.display.move_cursor)
        self.terminal.display.flush = Mock(wraps=self.terminal.display.flush)

        self.session = VT100Session(self.terminal, None)

        self.session.host_process = create_autospec(PtyProcess, instance=True)

    def test_with_no_eab_feature(self):
        # Arrange
        self.session.host_process.read = Mock(return_value=b'abc')

        self.session.handle_host()

        # Act
        self.session.render()

        # Assert
        self.terminal.display.buffered_write_byte.assert_any_call(0x80, None, row=0, column=0)
        self.terminal.display.buffered_write_byte.assert_any_call(0x81, None, row=0, column=1)
        self.terminal.display.buffered_write_byte.assert_any_call(0x82, None, row=0, column=2)

        self.terminal.display.flush.assert_called()

        self.terminal.display.move_cursor.assert_called_with(row=0, column=3)

        self.assertFalse(self.session.vt100_screen.dirty)

    def test_with_eab_feature(self):
        # Arrange
        self.terminal.display = BufferedDisplay(self.terminal, Dimensions(24, 80), 7)

        self.terminal.display.buffered_write_byte = Mock(wraps=self.terminal.display.buffered_write_byte)
        self.terminal.display.move_cursor = Mock(wraps=self.terminal.display.move_cursor)
        self.terminal.display.flush = Mock(wraps=self.terminal.display.flush)

        self.session.host_process.read = Mock(return_value=b'abc')

        self.session.handle_host()

        # Act
        self.session.render()

        # Assert
        self.terminal.display.buffered_write_byte.assert_any_call(0x80, 0x00, row=0, column=0)
        self.terminal.display.buffered_write_byte.assert_any_call(0x81, 0x00, row=0, column=1)
        self.terminal.display.buffered_write_byte.assert_any_call(0x82, 0x00, row=0, column=2)

        self.terminal.display.flush.assert_called()

        self.terminal.display.move_cursor.assert_called_with(row=0, column=3)

        self.assertFalse(self.session.vt100_screen.dirty)

def _create_terminal(interface):
    terminal_id = TerminalId(0b11110100)
    extended_id = 'c1348300'
    features = { }
    keymap = KEYMAP_3278_2

    terminal = Terminal(InterfaceWrapper(interface), None, terminal_id, extended_id, features, keymap)

    return terminal
