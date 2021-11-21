"""
oec.vt100
~~~~~~~~~
"""

import os
import logging
from ptyprocess import PtyProcess
import pyte

from .session import Session, SessionDisconnectedError
from .display import encode_ascii_character
from .keyboard import Key, get_ascii_character_for_key, MODIFIER_KEYS

VT100_KEY_MAP = {
    Key.NOT: b'^',
    Key.CENT: b'[',
    Key.BROKEN_BAR: b']',

    Key.ATTN: b'\x1b', # Escape

    Key.NEWLINE: b'\r',
    Key.ENTER: b'\r',

    Key.BACKSPACE: b'\b',
    Key.TAB: b'\t',

    Key.UP: b'\x1b[A',
    Key.DOWN: b'\x1b[B',
    Key.LEFT: b'\x1b[D',
    Key.RIGHT: b'\x1b[C'
}

VT100_KEY_MAP_ALT = {
    Key.SPACE: b'\x00',
    Key.LOWER_A: b'\x01',
    Key.LOWER_B: b'\x02',
    Key.LOWER_C: b'\x03',
    Key.LOWER_D: b'\x04',
    Key.LOWER_E: b'\x05',
    Key.LOWER_F: b'\x06',
    Key.LOWER_G: b'\x07',
    Key.LOWER_H: b'\x08',
    Key.LOWER_I: b'\x09',
    Key.LOWER_J: b'\x0a',
    Key.LOWER_K: b'\x0b',
    Key.LOWER_L: b'\x0c',
    Key.LOWER_M: b'\x0d',
    Key.LOWER_N: b'\x0e',
    Key.LOWER_O: b'\x0f',
    Key.LOWER_P: b'\x10',
    Key.LOWER_Q: b'\x11',
    Key.LOWER_R: b'\x12',
    Key.LOWER_S: b'\x13',
    Key.LOWER_T: b'\x14',
    Key.LOWER_U: b'\x15',
    Key.LOWER_V: b'\x16',
    Key.LOWER_W: b'\x17',
    Key.LOWER_X: b'\x18',
    Key.LOWER_Y: b'\x19',
    Key.LOWER_Z: b'\x1a',
    Key.CENT: b'\x1b',  # Ctrl + [
    Key.BACKSLASH: b'\x1c',
    Key.EQUAL: b'\x1d', # Ctrl + ]
    Key.LESS: b'\x1e',  # Ctrl + ~
    Key.SLASH: b'\x1f', # Ctrl + ?
    Key.NEWLINE: b'\n'
}

class VT100Session(Session):
    """VT100 session."""

    def __init__(self, terminal, host_command):
        super().__init__(terminal)

        self.logger = logging.getLogger(__name__)

        self.host_command = host_command
        self.host_process = None

        # Initialize the VT100 screen.
        (rows, columns) = self.terminal.display.dimensions

        self.vt100_screen = pyte.Screen(columns, rows)

        self.vt100_screen.write_process_input = lambda data: self.host_process.write(data.encode())

        # Unfortunately multiple VT100 bells will be replaced with a single 3270 terminal
        # alarm - also because the alarm is only sounded on terminal POLL the alarm sound
        # may appear out of sync with the terminal.
        #
        # A better approach may be to perform a flush when the bell is encountered but
        # that does not appear possible with the standard pyte ByteStream.
        self.vt100_screen.bell = lambda: self.terminal.sound_alarm()

        self.vt100_stream = pyte.ByteStream(self.vt100_screen)

        self.is_first_render = True

    def start(self):
        self._start_host_process()

    def terminate(self):
        if self.host_process:
            self._terminate_host_process()

    def fileno(self):
        return self.host_process.fileno()

    def handle_host(self):
        data = None

        try:
            data = self.host_process.read()
        except EOFError:
            self.host_process = None

            raise SessionDisconnectedError

        self.vt100_stream.feed(data)

        return True

    def handle_key(self, key, keyboard_modifiers, scan_code):
        bytes_ = self._map_key(key, keyboard_modifiers)

        if bytes_ is None:
            return

        self.host_process.write(bytes_)

    def render(self):
        if self.is_first_render:
            self.terminal.display.status_line.write_string(45, 'VT100')

            self.is_first_render = False

        self._apply()
        self._flush()

    def _map_key(self, key, keyboard_modifiers):
        if keyboard_modifiers.is_alt():
            # Ignore any modifiers... this would fall through and result in a warning
            # if they are not explicitly ignored.
            if key in MODIFIER_KEYS:
                return None

            bytes_ = VT100_KEY_MAP_ALT.get(key)

            if bytes_ is not None:
                return bytes_

            self.logger.warning(f'No key mapping found for ALT + {key}')
        else:
            bytes_ = VT100_KEY_MAP.get(key)

            if bytes_ is not None:
                return bytes_

            character = get_ascii_character_for_key(key)

            if character and character.isprintable():
                return character.encode()

        return None

    def _start_host_process(self):
        environment = os.environ.copy()

        environment['TERM'] = 'vt100'
        environment['LC_ALL'] = 'C'

        self.host_process = PtyProcess.spawn(self.host_command, env=environment,
                                             dimensions=self.terminal.display.dimensions)

    def _terminate_host_process(self):
        self.logger.debug('Terminating host process')

        if not self.host_process.terminate(force=True):
            self.logger.error('Unable to terminate host process')
        else:
            self.logger.debug('Host process terminated')

        self.host_process = None

    def _apply(self):
        has_eab = self.terminal.display.has_eab

        for row in self.vt100_screen.dirty:
            row_buffer = self.vt100_screen.buffer[row]

            for column in range(self.terminal.display.dimensions.columns):
                character = row_buffer[column]

                # TODO: Investigate multi-byte or zero-byte cases further.
                regen_byte = encode_ascii_character(ord(character.data)) if len(character.data) == 1 else 0x00
                eab_byte = 0x00 if has_eab else None

                self.terminal.display.buffered_write_byte(regen_byte, eab_byte, row=row, column=column)

        self.vt100_screen.dirty.clear()

    def _flush(self):
        self.terminal.display.flush()

        cursor = self.vt100_screen.cursor

        if cursor.y < self.terminal.display.dimensions.rows and cursor.x < self.terminal.display.dimensions.columns:
            self.terminal.display.move_cursor(row=cursor.y, column=cursor.x)
        else:
            self.logger.warn(f'Out of bounds cursor move to row={cursor.y}, column={cursor.x} ignored')
