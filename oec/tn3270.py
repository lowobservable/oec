"""
oec.tn3270
~~~~~~~~~~
"""

import logging
from tn3270 import Telnet, Emulator, AttributeCell, CharacterCell, AID, OperatorError, \
                   ProtectedCellOperatorError, FieldOverflowOperatorError
from tn3270.ebcdic import DUP, FM

from .session import Session, SessionDisconnectedError
from .display import encode_ascii_character, encode_ebcdic_character, encode_string
from .keyboard import Key, get_ebcdic_character_for_key

AID_KEY_MAP = {
    Key.CLEAR: AID.CLEAR,
    Key.ENTER: AID.ENTER,
    Key.PA1: AID.PA1,
    Key.PA2: AID.PA2,
    Key.PA3: AID.PA3,
    Key.PF1: AID.PF1,
    Key.PF2: AID.PF2,
    Key.PF3: AID.PF3,
    Key.PF4: AID.PF4,
    Key.PF5: AID.PF5,
    Key.PF6: AID.PF6,
    Key.PF7: AID.PF7,
    Key.PF8: AID.PF8,
    Key.PF9: AID.PF9,
    Key.PF10: AID.PF10,
    Key.PF11: AID.PF11,
    Key.PF12: AID.PF12,
    Key.PF13: AID.PF13,
    Key.PF14: AID.PF14,
    Key.PF15: AID.PF15,
    Key.PF16: AID.PF16,
    Key.PF17: AID.PF17,
    Key.PF18: AID.PF18,
    Key.PF19: AID.PF19,
    Key.PF20: AID.PF20,
    Key.PF21: AID.PF21,
    Key.PF22: AID.PF22,
    Key.PF23: AID.PF23,
    Key.PF24: AID.PF24
}

class TN3270Session(Session):
    """TN3270 session."""

    def __init__(self, terminal, host, port, extended_data_stream=True):
        self.logger = logging.getLogger(__name__)

        self.terminal = terminal
        self.host = host
        self.port = port
        self.extended_data_stream = extended_data_stream

        self.telnet = None
        self.emulator = None

        self.keyboard_insert = False
        self.waiting_on_host = False
        self.operator_error = None

        # TODO: Should the message area be initialized here?
        self.message_area = None
        self.last_message_area = None

    def start(self):
        self._connect_host()

        (rows, columns) = self.terminal.display.dimensions

        self.emulator = Emulator(self.telnet, rows, columns)

        self.emulator.alarm = lambda: self.terminal.sound_alarm()

    def terminate(self):
        if self.telnet:
            self._disconnect_host()

        self.emulator = None

    def handle_host(self):
        try:
            if not self.emulator.update(timeout=0):
                return False
        except (EOFError, ConnectionResetError):
            self._disconnect_host()

            raise SessionDisconnectedError

        self.waiting_on_host = False

        self._apply()
        self._flush()

        return True

    def handle_key(self, key, keyboard_modifiers, scan_code):
        aid = AID_KEY_MAP.get(key)

        try:
            if aid is not None:
                self.emulator.aid(aid)

                self.waiting_on_host = True
            #elif key == Key.RESET:
            elif key == Key.BACKSPACE:
                self.emulator.backspace()
            elif key == Key.TAB:
                self.emulator.tab()
            elif key == Key.BACKTAB:
                self.emulator.tab(direction=-1)
            elif key == Key.NEWLINE:
                self.emulator.newline()
            elif key == Key.HOME:
                self.emulator.home()
            elif key == Key.UP:
                self.emulator.cursor_up()
            elif key == Key.DOWN:
                self.emulator.cursor_down()
            elif key == Key.LEFT:
                self.emulator.cursor_left()
            elif key == Key.LEFT_2:
                self.emulator.cursor_left(rate=2)
            elif key == Key.RIGHT:
                self.emulator.cursor_right()
            elif key == Key.RIGHT_2:
                self.emulator.cursor_right(rate=2)
            elif key == Key.INSERT:
                self._handle_insert_key()
            elif key == Key.DELETE:
                self.emulator.delete()
            elif key == Key.DUP:
                self.emulator.dup()
            elif key == Key.FIELD_MARK:
                self.emulator.field_mark()
            else:
                byte = get_ebcdic_character_for_key(key)

                if byte:
                    self.emulator.input(byte, self.keyboard_insert)
        except OperatorError as error:
            self.operator_error = error

        self._apply()
        self._flush()

    def _handle_insert_key(self):
        self.keyboard_insert = not self.keyboard_insert

        self.terminal.display.status_line.write_keyboard_insert(self.keyboard_insert)

    def _connect_host(self):
        terminal_type = f'IBM-3278-{self.terminal.terminal_id.model}'

        if self.extended_data_stream:
            terminal_type += '-E'

        self.telnet = Telnet(terminal_type)

        self.telnet.open(self.host, self.port)

    def _disconnect_host(self):
        self.telnet.close()

        self.telnet = None

    def _apply(self):
        for address in self.emulator.dirty:
            cell = self.emulator.cells[address]

            byte = 0x00

            if isinstance(cell, AttributeCell):
                byte = self._map_attribute(cell)
            elif isinstance(cell, CharacterCell):
                byte = self._map_character(cell)

            self.terminal.display.buffered_write(byte, index=address)

        self.emulator.dirty.clear()

        # Update the message area.
        self.message_area = self._format_message_area()

    def _flush(self):
        self.terminal.display.flush()

        # TODO: hmm we need a buffered status line...
        if self.message_area != self.last_message_area:
            self.terminal.display.status_line.write(8, self.message_area)

            self.last_message_area = self.message_area

        # TODO: see note in VT100 about forcing sync
        self.terminal.display.move_cursor(index=self.emulator.cursor_address)

        # TODO: eek, is this the correct place to do this?
        self.operator_error = None

    def _map_attribute(self, cell):
        # Only map the protected and display bits - ignore numeric, skip and modified.
        return 0xc0 | (cell.attribute.value & 0x2c)

    def _map_character(self, cell):
        byte = cell.byte

        if byte == DUP:
            return encode_ascii_character(ord('*'))

        if byte == FM:
            return encode_ascii_character(ord(';'))

        # TODO: Temporary workaround to show empty reverse video fields until EAB
        # support is added.
        if byte == 0x40 and cell.formatting is not None and cell.formatting.reverse:
            return encode_ascii_character(ord('#'))

        return encode_ebcdic_character(byte)

    def _format_message_area(self):
        message_area = b''

        if self.waiting_on_host:
            # X SPACE CLOCK_LEFT CLOCK_RIGHT
            message_area = b'\xf6\x00\xf4\xf5'
        elif isinstance(self.operator_error, ProtectedCellOperatorError):
            # X SPACE ARROW_LEFT OPERATOR ARROW_RIGHT
            message_area = b'\xf6\x00\xf8\xdb\xd8'
        elif isinstance(self.operator_error, FieldOverflowOperatorError):
            # X SPACE OPERATOR >
            message_area = b'\xf6\x00\xdb' + encode_string('>')
        elif self.emulator.keyboard_locked:
            # X SPACE SYSTEM
            message_area = b'\xf6\x00' + encode_string('SYSTEM')

        return message_area.ljust(9, b'\x00')
