"""
oec.tn3270
~~~~~~~~~~
"""

import logging
import ssl
from tn3270 import Telnet, TN3270EFunction, Emulator, AttributeCell, CharacterCell, AID, Color, \
                   Highlight, OperatorError, ProtectedCellOperatorError, FieldOverflowOperatorError
from tn3270.ebcdic import DUP, FM

from .session import Session, SessionDisconnectedError
from .display import encode_character, encode_string
from .keyboard import Key, get_character_for_key

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

    def __init__(self, terminal, host, port, device_names, character_encoding, tn3270e_profile, ssl_enabled=False, no_starttls=False, ssl_no_verify=False, no_hostname_status=False):
        super().__init__(terminal)

        self.logger = logging.getLogger(__name__)

        self.host = host
        self.port = port
        self.device_names = device_names
        self.character_encoding = character_encoding
        self.tn3270e_profile = tn3270e_profile
        self.ssl_enabled = ssl_enabled
        self.no_starttls = no_starttls
        self.ssl_no_verify = ssl_no_verify
        self.no_hostname_status = no_hostname_status

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

        self._write_security_status()

        if not self.no_hostname_status:
            self._write_hostname_status()

        (rows, columns) = self.terminal.display.dimensions

        if self.terminal.display.has_eab:
            supported_colors = 8
            supported_highlights = [Highlight.BLINK, Highlight.REVERSE, Highlight.UNDERSCORE]
        else:
            supported_colors = 1
            supported_highlights = []

        self.emulator = Emulator(self.telnet, rows, columns, supported_colors, supported_highlights)

        self.emulator.alarm = lambda: self.terminal.sound_alarm()

    def terminate(self):
        if self.telnet:
            self._disconnect_host()

        self.emulator = None

    def fileno(self):
        return self.emulator.stream.socket.fileno()

    def has_pending_data(self):
        sock = self.emulator.stream.socket
        return isinstance(sock, ssl.SSLSocket) and sock.pending() > 0

    def handle_host(self):
        try:
            if not self.emulator.update(timeout=0):
                return False
        except (EOFError, ConnectionResetError):
            self._disconnect_host()

            raise SessionDisconnectedError

        self.waiting_on_host = False

        return True

    def handle_key(self, key, keyboard_modifiers, scan_code):
        aid = AID_KEY_MAP.get(key)

        try:
            if aid is not None:
                self._reset_insert()

                self.emulator.aid(aid)

                self.waiting_on_host = True
            #elif key == Key.RESET:
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
            elif key == Key.BACKSPACE:
                self.emulator.backspace()
            elif key == Key.DELETE:
                self.emulator.delete()
            elif key == Key.ERASE_EOF:
                self.emulator.erase_end_of_field()
            elif key == Key.ERASE_INPUT:
                self.emulator.erase_input()
            elif key == Key.INSERT:
                self._handle_insert_key()
            elif key == Key.DUP:
                self.emulator.dup()
            elif key == Key.FIELD_MARK:
                self.emulator.field_mark()
            else:
                character = get_character_for_key(key)

                if character:
                    byte = character.encode(self.character_encoding)[0]

                    self.emulator.input(byte, self.keyboard_insert)
        except OperatorError as error:
            self.operator_error = error

    def render(self):
        self._apply()
        self._flush()

    def _reset_insert(self):
        if not self.keyboard_insert:
            return

        self.keyboard_insert = False

        self.terminal.display.status_line.write_keyboard_insert(False)

    def _handle_insert_key(self):
        self.keyboard_insert = not self.keyboard_insert

        self.terminal.display.status_line.write_keyboard_insert(self.keyboard_insert)

    def _connect_host(self):
        # We will pretend a 3279 without EAB is a 3278.
        if self.terminal.display.has_eab:
            type = '3279'
        else:
            type = '3278'

        # Although a IBM 3278 does not support the formatting enabled by the extended
        # data stream, the capabilities will be reported in the query reply.
        terminal_type = f'IBM-{type}-{self.terminal.terminal_id.model}-E'

        self.logger.info(f'Terminal Type = {terminal_type}')

        tn3270e_args = _get_tn3270e_args(self.tn3270e_profile)

        self.telnet = Telnet(terminal_type, **tn3270e_args)

        ssl_args = {}
        starttls_enabled = not self.ssl_enabled and not self.no_starttls

        if self.ssl_enabled or starttls_enabled:
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)

            if self.ssl_no_verify:
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
            else:
                ssl_context.load_default_certs()

            if self.ssl_enabled:
                ssl_args['ssl_context'] = ssl_context
                ssl_args['ssl_server_hostname'] = self.host
            else:
                ssl_args['starttls_ssl_context'] = ssl_context
                ssl_args['starttls_server_hostname'] = self.host

        self.telnet.open(self.host, self.port, self.device_names, **ssl_args)

        if self.telnet.is_tn3270e_negotiated:
            self.logger.info(f'TN3270E mode negotiated: Device Type = {self.telnet.device_type}, Device Name = {self.telnet.device_name}, Functions = {self.telnet.tn3270e_functions}')
        else:
            self.logger.debug('Unable to negotiate TN3270E mode')

    def _write_security_status(self):
        is_secure = isinstance(self.telnet.socket, ssl.SSLSocket)

        self.terminal.display.status_line.write_string(20, 'encrypted' if is_secure else 'unencrypted')

    def _write_hostname_status(self):
        status_column = 46
        columns = self.terminal.display.status_line.columns
        max_length = columns - status_column

        if self.port == 23:
            text = self.host
        else:
            text = f'{self.host}:{self.port}'

        self.terminal.display.status_line.write_string(status_column, text[:max_length].rjust(max_length))

    def _disconnect_host(self):
        self.telnet.close()

        self.telnet = None

    def _apply(self):
        has_eab = self.terminal.display.has_eab

        for address in self.emulator.dirty:
            cell = self.emulator.cells[address]

            (regen_byte, eab_byte) = _map_cell(cell, self.character_encoding, has_eab)

            self.terminal.display.buffered_write_byte(regen_byte, eab_byte, index=address)

        self.emulator.dirty.clear()

        # Update the message area.
        self.message_area = self._format_message_area()

    def _flush(self):
        self.terminal.display.flush()

        # TODO: hmm we need a buffered status line...
        if self.message_area != self.last_message_area:
            self.terminal.display.status_line.write(8, self.message_area)

            self.last_message_area = self.message_area

        self.terminal.display.move_cursor(index=self.emulator.cursor_address)

        # TODO: This needs to be moved.
        self.operator_error = None

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

def _map_cell(cell, character_encoding, has_eab):
    regen_byte = 0x00

    if isinstance(cell, AttributeCell):
        # Only map the protected and display bits - ignore numeric, skip and modified.
        regen_byte = 0xc0 | (cell.attribute.value & 0x2c)
    elif isinstance(cell, CharacterCell):
        byte = cell.byte

        if cell.character_set is not None:
            # TODO: Temporary workaround until character set support is added.
            regen_byte = encode_character('ß')
        elif byte == DUP:
            regen_byte = encode_character('*')
        elif byte == FM:
            regen_byte = encode_character(';')
        else:
            character = bytes([byte]).decode(character_encoding)

            regen_byte = encode_character(character)

    if not has_eab:
        return (regen_byte, None)

    eab_byte = _map_formatting(cell.formatting)

    return (regen_byte, eab_byte)

def _map_formatting(formatting):
    if formatting is None:
        return 0x00

    byte = 0x00

    # Map the 3270 color to EAB color.
    if formatting.color == Color.BLUE:
        byte |= 0x08
    elif formatting.color == Color.RED:
        byte |= 0x10
    elif formatting.color == Color.PINK:
        byte |= 0x18
    elif formatting.color == Color.GREEN:
        byte |= 0x20
    elif formatting.color == Color.TURQUOISE:
        byte |= 0x28
    elif formatting.color == Color.YELLOW:
        byte |= 0x30
    elif formatting.color == Color.WHITE:
        byte |= 0x38

    # Map the 3270 highlight to EAB highlight.
    if formatting.blink:
        byte |= 0x40
    elif formatting.reverse:
        byte |= 0x80
    elif formatting.underscore:
        byte |= 0xc0

    return byte

def _get_tn3270e_args(profile):
    is_tn3270e_enabled = True
    tn3270e_functions = [TN3270EFunction.RESPONSES]

    if profile == 'off':
        is_tn3270e_enabled = False
        tn3270e_functions = None
    elif profile == 'basic':
        tn3270e_functions = []

    return {
        'is_tn3270e_enabled': is_tn3270e_enabled,
        'tn3270e_functions': tn3270e_functions
    }
