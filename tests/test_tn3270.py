import unittest
from unittest.mock import Mock, create_autospec

from coax.protocol import TerminalId
from tn3270 import Telnet, Emulator, AttributeCell, CharacterCell, AID, Color, ProtectedCellOperatorError, FieldOverflowOperatorError
from tn3270.attributes import Attribute
from tn3270.emulator import CellFormatting

import context

from oec.interface import InterfaceWrapper
from oec.terminal import Terminal
from oec.display import Dimensions, BufferedDisplay, StatusLine
from oec.keyboard import Key, KeyboardModifiers
from oec.keymap_3278_2 import KEYMAP as KEYMAP_3278_2
from oec.session import SessionDisconnectedError
from oec.tn3270 import TN3270Session

from mock_interface import MockInterface

class SessionHandleHostTestCase(unittest.TestCase):
    def setUp(self):
        self.interface = MockInterface()

        self.terminal = _create_terminal(self.interface)

        self.session = TN3270Session(self.terminal, 'mainframe', 23, 'ibm037')

        self.telnet = create_autospec(Telnet, instance=True)

        self.session.telnet = self.telnet
        self.session.emulator = create_autospec(Emulator, instance=True)

    def test_no_changes(self):
        # Arrange
        self.session.emulator.update = Mock(return_value=False)

        # Act and assert
        self.assertFalse(self.session.handle_host())

    def test_changes(self):
        # Arrange
        self.session.emulator.update = Mock(return_value=True)

        # Act and assert
        self.assertTrue(self.session.handle_host())

    def test_eof(self):
        # Arrange
        self.session.emulator.update = Mock(side_effect=EOFError)

        # Act and assert
        with self.assertRaises(SessionDisconnectedError):
            self.session.handle_host()

        self.telnet.close.assert_called()

    def test_connection_reset(self):
        # Arrange
        self.session.emulator.update = Mock(side_effect=ConnectionResetError)

        # Act and assert
        with self.assertRaises(SessionDisconnectedError):
            self.session.handle_host()

        self.telnet.close.assert_called()

class SessionHandleKeyTestCase(unittest.TestCase):
    def setUp(self):
        self.interface = MockInterface()

        self.terminal = _create_terminal(self.interface)

        self.session = TN3270Session(self.terminal, 'mainframe', 23, 'ibm037')

        self.session.emulator = create_autospec(Emulator, instance=True)

        self.session.emulator.cells = []
        self.session.emulator.dirty = set()

    def test_enter(self):
        # Act
        self.session.handle_key(Key.ENTER, KeyboardModifiers.NONE, None)

        # Assert
        self.session.emulator.aid.assert_called_with(AID.ENTER)

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

    def test_left_2(self):
        # Act
        self.session.handle_key(Key.LEFT_2, KeyboardModifiers.NONE, None)

        # Assert
        self.session.emulator.cursor_left.assert_called_with(rate=2)

    def test_right(self):
        # Act
        self.session.handle_key(Key.RIGHT, KeyboardModifiers.NONE, None)

        # Assert
        self.session.emulator.cursor_right.assert_called()

    def test_right_2(self):
        # Act
        self.session.handle_key(Key.RIGHT_2, KeyboardModifiers.NONE, None)

        # Assert
        self.session.emulator.cursor_right.assert_called_with(rate=2)

    def test_backspace(self):
        # Act
        self.session.handle_key(Key.BACKSPACE, KeyboardModifiers.NONE, None)

        # Assert
        self.session.emulator.backspace.assert_called()

    def test_delete(self):
        # Act
        self.session.handle_key(Key.DELETE, KeyboardModifiers.NONE, None)

        # Assert
        self.session.emulator.delete.assert_called()

    def test_erase_eof(self):
        # Act
        self.session.handle_key(Key.ERASE_EOF, KeyboardModifiers.NONE, None)

        # Assert
        self.session.emulator.erase_end_of_field.assert_called()

    def test_erase_input(self):
        # Act
        self.session.handle_key(Key.ERASE_INPUT, KeyboardModifiers.NONE, None)

        # Assert
        self.session.emulator.erase_input.assert_called()

    def test_dup(self):
        # Act
        self.session.handle_key(Key.DUP, KeyboardModifiers.NONE, None)

        # Assert
        self.session.emulator.dup.assert_called()

    def test_field_mark(self):
        # Act
        self.session.handle_key(Key.FIELD_MARK, KeyboardModifiers.NONE, None)

        # Assert
        self.session.emulator.field_mark.assert_called()

    def test_input(self):
        # Act
        self.session.handle_key(Key.LOWER_A, KeyboardModifiers.NONE, None)

        # Assert
        self.session.emulator.input.assert_called_with(0x81, False)

    def test_insert(self):
        # Act
        self.session.handle_key(Key.INSERT, KeyboardModifiers.NONE, None)

        self.session.handle_key(Key.LOWER_A, KeyboardModifiers.NONE, None)

        self.session.handle_key(Key.INSERT, KeyboardModifiers.NONE, None)

        # Assert
        self.assertFalse(self.session.keyboard_insert)

        self.session.emulator.input.assert_called_with(0x81, True)

    def test_operator_error(self):
        # Arrange
        self.session.emulator.input = Mock(side_effect=ProtectedCellOperatorError)

        self.assertIsNone(self.session.operator_error)

        # Act
        self.session.handle_key(Key.LOWER_A, KeyboardModifiers.NONE, None)

        # Assert
        self.assertIsInstance(self.session.operator_error, ProtectedCellOperatorError)

class SessionRenderTestCase(unittest.TestCase):
    def setUp(self):
        self.interface = MockInterface()

        self.terminal = _create_terminal(self.interface)

        self.terminal.display.buffered_write_byte = Mock(wraps=self.terminal.display.buffered_write_byte)
        self.terminal.display.move_cursor = Mock(wraps=self.terminal.display.move_cursor)
        self.terminal.display.flush = Mock(wraps=self.terminal.display.flush)
        self.terminal.display.status_line.write = Mock(wraps=self.terminal.display.status_line.write)

        self.session = TN3270Session(self.terminal, 'mainframe', 23, 'ibm037')

        self.session.telnet = create_autospec(Telnet, instance=True)
        self.session.emulator = create_autospec(Emulator, instance=True)

        self.session.emulator.keyboard_locked = False

    def test_with_no_eab_feature(self):
        # Arrange
        cells = _create_screen_cells(24, 80)

        _set_attribute(cells, 0, protected=True)
        _set_characters(cells, 1, 'PROTECTED'.encode('ibm037'))
        _set_attribute(cells, 10, protected=True, intensified=True)
        _set_characters(cells, 11, 'PROTECTED INTENSIFIED'.encode('ibm037'))
        _set_attribute(cells, 32, protected=True, hidden=True)
        _set_characters(cells, 33, 'PROTECTED HIDDEN'.encode('ibm037'))
        _set_attribute(cells, 49, protected=False)
        _set_characters(cells, 50, 'UNPROTECTED'.encode('ibm037'))
        _set_attribute(cells, 61, protected=False, intensified=True)
        _set_characters(cells, 62, 'UNPROTECTED INTENSIFIED'.encode('ibm037'))
        _set_attribute(cells, 85, protected=False, hidden=True)
        _set_characters(cells, 86, 'UNPROTECTED HIDDEN'.encode('ibm037'))
        _set_attribute(cells, 104, protected=True)
        _set_formatting(cells, 104, color=Color.YELLOW)
        _set_characters(cells, 105, 'EAB'.encode('ibm037'))
        _set_formatting(cells, 105, blink=True)
        _set_formatting(cells, 106, reverse=True)
        _set_formatting(cells, 107, underscore=True)
        _set_attribute(cells, 108, protected=True)

        self.session.emulator.cells = cells
        self.session.emulator.dirty = set(range(109))
        self.session.emulator.cursor_address = 8

        # Act
        self.session.render()

        # Assert
        regen_bytes = bytes.fromhex('e0afb1aeb3a4a2b3a4a3e8afb1aeb3a4a2b3a4a300a8adb3a4adb2a8a5a8a4a3ecafb1aeb3a4a2b3a4a300a7a8a3a3a4adc0b4adafb1aeb3a4a2b3a4a3c8b4adafb1aeb3a4a2b3a4a300a8adb3a4adb2a8a5a8a4a3ccb4adafb1aeb3a4a2b3a4a300a7a8a3a3a4ade0a4a0a1e0')

        for (index, regen_byte) in enumerate(regen_bytes):
            self.terminal.display.buffered_write_byte.assert_any_call(regen_byte, None, index=index)

        self.terminal.display.flush.assert_called()

        self.terminal.display.move_cursor.assert_called_with(index=8)

        self.assertFalse(self.session.emulator.dirty)

    def test_with_eab_feature(self):
        # Arrange
        self.terminal.display = BufferedDisplay(self.terminal, Dimensions(24, 80), 7)

        self.terminal.display.buffered_write_byte = Mock(wraps=self.terminal.display.buffered_write_byte)
        self.terminal.display.move_cursor = Mock(wraps=self.terminal.display.move_cursor)
        self.terminal.display.flush = Mock(wraps=self.terminal.display.flush)

        cells = _create_screen_cells(24, 80)

        _set_attribute(cells, 0, protected=True)
        _set_characters(cells, 1, 'PROTECTED'.encode('ibm037'))
        _set_attribute(cells, 10, protected=True, intensified=True)
        _set_characters(cells, 11, 'PROTECTED INTENSIFIED'.encode('ibm037'))
        _set_attribute(cells, 32, protected=True, hidden=True)
        _set_characters(cells, 33, 'PROTECTED HIDDEN'.encode('ibm037'))
        _set_attribute(cells, 49, protected=False)
        _set_characters(cells, 50, 'UNPROTECTED'.encode('ibm037'))
        _set_attribute(cells, 61, protected=False, intensified=True)
        _set_characters(cells, 62, 'UNPROTECTED INTENSIFIED'.encode('ibm037'))
        _set_attribute(cells, 85, protected=False, hidden=True)
        _set_characters(cells, 86, 'UNPROTECTED HIDDEN'.encode('ibm037'))
        _set_attribute(cells, 104, protected=True)
        _set_formatting(cells, 104, color=Color.YELLOW)
        _set_characters(cells, 105, 'EAB'.encode('ibm037'))
        _set_formatting(cells, 105, blink=True)
        _set_formatting(cells, 106, reverse=True)
        _set_formatting(cells, 107, underscore=True)
        _set_attribute(cells, 108, protected=True)

        self.session.emulator.cells = cells
        self.session.emulator.dirty = set(range(109))
        self.session.emulator.cursor_address = 8

        # Act
        self.session.render()

        # Assert
        regen_bytes = bytes.fromhex('e0afb1aeb3a4a2b3a4a3e8afb1aeb3a4a2b3a4a300a8adb3a4adb2a8a5a8a4a3ecafb1aeb3a4a2b3a4a300a7a8a3a3a4adc0b4adafb1aeb3a4a2b3a4a3c8b4adafb1aeb3a4a2b3a4a300a8adb3a4adb2a8a5a8a4a3ccb4adafb1aeb3a4a2b3a4a300a7a8a3a3a4ade0a4a0a1e0')
        eab_bytes = bytes.fromhex('0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000304080c000')

        for (index, (regen_byte, eab_byte)) in enumerate(zip(regen_bytes, eab_bytes)):
            self.terminal.display.buffered_write_byte.assert_any_call(regen_byte, eab_byte, index=index)

        self.terminal.display.flush.assert_called()

        self.terminal.display.move_cursor.assert_called_with(index=8)

        self.assertFalse(self.session.emulator.dirty)

    def test_keyboard_locked(self):
        # Arrange
        self.session.emulator.cells = _create_screen_cells(24, 80)
        self.session.emulator.dirty = set()
        self.session.emulator.cursor_address = 8
        self.session.emulator.keyboard_locked = True

        # Act
        self.session.render()

        # Assert
        self.terminal.display.status_line.write.assert_called_with(8, bytes.fromhex('f600b2b8b2b3a4ac00'))

    def test_protected_cell_operator_error(self):
        # Arrange
        self.session.emulator.cells = _create_screen_cells(24, 80)
        self.session.emulator.dirty = set()
        self.session.emulator.cursor_address = 8

        self.session.operator_error = ProtectedCellOperatorError()

        # Act
        self.session.render()

        # Assert
        self.terminal.display.status_line.write.assert_called_with(8, bytes.fromhex('f600f8dbd800000000'))

    def test_field_overflow_operator_error(self):
        # Arrange
        self.session.emulator.cells = _create_screen_cells(24, 80)
        self.session.emulator.dirty = set()
        self.session.emulator.cursor_address = 8

        self.session.operator_error = FieldOverflowOperatorError()

        # Act
        self.session.render()

        # Assert
        self.terminal.display.status_line.write.assert_called_with(8, bytes.fromhex('f600db080000000000'))

def _create_terminal(interface):
    terminal_id = TerminalId(0b11110100)
    extended_id = 'c1348300'
    features = { }
    keymap = KEYMAP_3278_2

    terminal = Terminal(InterfaceWrapper(interface), None, terminal_id, extended_id, features, keymap)

    terminal.display.status_line = create_autospec(StatusLine, instance=True)

    return terminal

def _create_screen_cells(rows, columns):
    return [CharacterCell(0x00) for address in range(rows * columns)]

def _set_attribute(cells, index, protected=False, intensified=False, hidden=False):
    display = 2 if intensified else 3 if hidden else 0

    attribute = Attribute((0x20 if protected else 0) | (display << 2))

    cells[index] = AttributeCell(attribute)

def _set_characters(cells, index, bytes_):
    for byte in bytes_:
        cells[index] = CharacterCell(byte)

        index += 1

def _set_formatting(cells, index, color=0x00, blink=False, reverse=False, underscore=False):
    if color == 0x00 and not blink and not reverse and not underscore:
        cells[index].formatting = None
        return

    formatting = CellFormatting()

    formatting.color = color
    formatting.blink = blink
    formatting.reverse = reverse
    formatting.underscore = underscore

    cells[index].formatting = formatting
