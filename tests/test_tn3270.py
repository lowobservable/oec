import unittest
from unittest.mock import Mock

import context

from oec.session import SessionDisconnectedError
from oec.keyboard import Key, KeyboardModifiers
from oec.tn3270 import TN3270Session
from tn3270 import AttributeCell, CharacterCell, AID, ProtectedCellOperatorError

class SessionHandleHostTestCase(unittest.TestCase):
    def setUp(self):
        self.terminal = Mock()

        self.terminal.display = MockDisplay(24, 80)

        self.session = TN3270Session(self.terminal, 'mainframe', 23)

        self.telnet = Mock()

        self.session.telnet = self.telnet
        self.session.emulator = Mock()

    def test_no_changes(self):
        # Arrange
        self.session.emulator.update = Mock(return_value=False)

        # Act and assert
        self.assertFalse(self.session.handle_host())

    def test_changes(self):
        # Arrange
        self.session.emulator.update = Mock(return_value=True)

        cells = _create_screen_cells(24, 80)

        _set_attribute(cells, 0, MockAttribute(protected=True))
        _set_characters(cells, 1, 'PROTECTED'.encode('cp500'))
        _set_attribute(cells, 10, MockAttribute(protected=True, intensified=True))
        _set_characters(cells, 11, 'PROTECTED INTENSIFIED'.encode('cp500'))
        _set_attribute(cells, 32, MockAttribute(protected=True, hidden=True))
        _set_characters(cells, 33, 'PROTECTED HIDDEN'.encode('cp500'))
        _set_attribute(cells, 49, MockAttribute(protected=False))
        _set_characters(cells, 50, 'UNPROTECTED'.encode('cp500'))
        _set_attribute(cells, 61, MockAttribute(protected=False, intensified=True))
        _set_characters(cells, 62, 'UNPROTECTED INTENSIFIED'.encode('cp500'))
        _set_attribute(cells, 85, MockAttribute(protected=False, hidden=True))
        _set_characters(cells, 86, 'UNPROTECTED HIDDEN'.encode('cp500'))
        _set_attribute(cells, 104, MockAttribute(protected=True))

        self.session.emulator.cells = cells
        self.session.emulator.dirty = set(range(105))

        self.session.emulator.cursor_address = 8

        # Act and assert
        self.assertTrue(self.session.handle_host())

        self.terminal.display.flush.assert_called()

        self.assertEqual(self.terminal.display.buffer[:105], bytes.fromhex('e0afb1aeb3a4a2b3a4a3e8afb1aeb3a4a2b3a4a300a8adb3a4adb2a8a5a8a4a3ccafb1aeb3a4a2b3a4a300a7a8a3a3a4adc0b4adafb1aeb3a4a2b3a4a3c8b4adafb1aeb3a4a2b3a4a300a8adb3a4adb2a8a5a8a4a3ccb4adafb1aeb3a4a2b3a4a300a7a8a3a3a4ade0'))
        self.assertTrue(all([byte == 0x00 for byte in self.terminal.display.buffer[105:]]))

        self.assertEqual(self.terminal.display.cursor_index, 8)

    def test_eof(self):
        # Arrange
        self.session.emulator.update = Mock(side_effect=EOFError)

        # Act and assert
        with self.assertRaises(SessionDisconnectedError):
            self.session.handle_host()

        self.telnet.close.assert_called()

    def test_keyboard_locked(self):
        # Arrange
        self.session.emulator.update = Mock(return_value=True)

        self.session.emulator.cells = _create_screen_cells(24, 80)
        self.session.emulator.dirty = set()

        # Act
        self.session.handle_host()

        # Assert
        self.terminal.display.status_line.write.assert_called_with(8, bytes.fromhex('f600b2b8b2b3a4ac00'))

class SessionHandleKeyTestCase(unittest.TestCase):
    def setUp(self):
        self.terminal = Mock()

        self.session = TN3270Session(self.terminal, 'mainframe', 23)

        self.session.emulator = Mock()

        self.session.emulator.cells = []
        self.session.emulator.dirty = set()

    def test_enter(self):
        # Act
        self.session.handle_key(Key.ENTER, KeyboardModifiers.NONE, None)

        # Assert
        self.session.emulator.aid.assert_called_with(AID.ENTER)

    def test_backspace(self):
        # Act
        self.session.handle_key(Key.BACKSPACE, KeyboardModifiers.NONE, None)

        # Assert
        self.session.emulator.backspace.assert_called()

    def test_tab(self):
        # Act
        self.session.handle_key(Key.TAB, KeyboardModifiers.NONE, None)

        # Assert
        self.session.emulator.tab.assert_called()

    def test_backtab(self):
        # Act
        self.session.handle_key(Key.BACKTAB, KeyboardModifiers.NONE, None)

        # Assert
        self.session.emulator.tab.assert_called_with(direction=-1)

    def test_newline(self):
        # Act
        self.session.handle_key(Key.NEWLINE, KeyboardModifiers.NONE, None)

        # Assert
        self.session.emulator.newline.assert_called()

    def test_field_exit(self):
        # Act
        self.session.handle_key(Key.FIELD_EXIT, KeyboardModifiers.NONE, None)

        # Assert
        self.session.emulator.newline.assert_called()

    def test_home(self):
        # Act
        self.session.handle_key(Key.HOME, KeyboardModifiers.NONE, None)

        # Assert
        self.session.emulator.home.assert_called()

    def test_up(self):
        # Act
        self.session.handle_key(Key.UP, KeyboardModifiers.NONE, None)

        # Assert
        self.session.emulator.cursor_up.assert_called()

    def test_down(self):
        # Act
        self.session.handle_key(Key.DOWN, KeyboardModifiers.NONE, None)

        # Assert
        self.session.emulator.cursor_down.assert_called()

    def test_left(self):
        # Act
        self.session.handle_key(Key.LEFT, KeyboardModifiers.NONE, None)

        # Assert
        self.session.emulator.cursor_left.assert_called()

    def test_right(self):
        # Act
        self.session.handle_key(Key.RIGHT, KeyboardModifiers.NONE, None)

        # Assert
        self.session.emulator.cursor_right.assert_called()

    def test_delete(self):
        # Act
        self.session.handle_key(Key.DELETE, KeyboardModifiers.NONE, None)

        # Assert
        self.session.emulator.delete.assert_called()

    def test_input(self):
        # Act
        self.session.handle_key(Key.LOWER_A, KeyboardModifiers.NONE, None)

        # Assert
        self.session.emulator.input.assert_called_with(0x81)

    def test_protected_cell_operator_error(self):
        # Arrange
        self.session.emulator.input = Mock(side_effect=ProtectedCellOperatorError)

        # Act
        self.session.handle_key(Key.LOWER_A, KeyboardModifiers.NONE, None)

        # Assert
        self.terminal.display.status_line.write.assert_called_with(8, bytes.fromhex('f600f8dbd800000000'))

class MockDisplay:
    def __init__(self, rows, columns):
        self.buffer = bytearray(rows * columns)
        self.cursor_index = None

        self.status_line = Mock()

        self.flush = Mock()

    def buffered_write(self, byte, index):
        self.buffer[index] = byte

    def move_cursor(self, index):
        self.cursor_index = index

class MockAttribute:
    def __init__(self, protected=False, intensified=False, hidden=False):
        self.protected = protected
        self.intensified = intensified
        self.hidden = hidden

def _create_screen_cells(rows, columns):
    return [CharacterCell(0x00) for address in range(rows * columns)]

def _set_attribute(screen, index, attribute):
    screen[index] = AttributeCell(attribute)

def _set_characters(screen, index, bytes_):
    for byte in bytes_:
        screen[index] = CharacterCell(byte)

        index += 1
