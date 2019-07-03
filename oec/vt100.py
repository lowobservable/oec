"""
oec.vt100
~~~~~~~~~
"""

import os
from select import select
import logging
from ptyprocess import PtyProcess
import pyte

from .session import Session, SessionDisconnectedError
from .display import encode_ascii_character
from .keyboard import Key, get_ascii_character_for_key

VT100_KEY_MAP = {
    Key.NOT: b'^',
    Key.CENT: b'[',
    Key.BROKEN_BAR: b']',

    Key.ATTN: b'\x1b', # Escape

    Key.NEWLINE: b'\r',
    Key.ENTER: b'\r',
    Key.FIELD_EXIT: b'\r',

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
        self.logger = logging.getLogger(__name__)

        self.terminal = terminal
        self.host_command = host_command
        self.host_process = None

        # Initialize the VT100 screen.
        (rows, columns) = self.terminal.display.dimensions

        self.vt100_screen = pyte.Screen(columns, rows)

        self.vt100_screen.write_process_input = lambda data: self.host_process.write(data.encode())

        self.vt100_stream = pyte.ByteStream(self.vt100_screen)

    def start(self):
        # Start the host process.
        self._start_host_process()

        # Clear the screen.
        self.terminal.display.clear()

        # Update the status line.
        self.terminal.display.status_line.write_string(45, 'VT100')

        # Reset the cursor.
        self.terminal.display.move_cursor(row=0, column=0)

    def terminate(self):
        if self.host_process:
            self._terminate_host_process()

    def handle_host(self):
        try:
            if self.host_process not in select([self.host_process], [], [], 0)[0]:
                return False

            data = self.host_process.read()

            self._handle_host_output(data)

            return True
        except EOFError:
            self.host_process = None

            raise SessionDisconnectedError

    def handle_key(self, key, keyboard_modifiers, scan_code):
        bytes_ = self._map_key(key, keyboard_modifiers)

        if bytes_ is not None:
            self.host_process.write(bytes_)

    def _map_key(self, key, keyboard_modifiers):
        if keyboard_modifiers.is_alt():
            # Ignore any modifiers... this would fall through and result in a warning
            # if they are not explicitly ignored.
            if key in [Key.LEFT_ALT, Key.RIGHT_ALT, Key.LEFT_SHIFT, Key.RIGHT_SHIFT,
                       Key.CAPS_LOCK]:
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

    def _handle_host_output(self, data):
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(f'Host process output: {data}')

        self.vt100_stream.feed(data)

        self._apply(self.vt100_screen)

        self.vt100_screen.dirty.clear()

        self._flush()

    def _apply(self, screen):
        for row in screen.dirty:
            row_buffer = screen.buffer[row]

            for column in range(self.terminal.display.dimensions.columns):
                character = row_buffer[column]

                # TODO: Investigate multi-byte or zero-byte cases further.
                # TODO: Add additional mapping for special cases such as '^'...
                byte = encode_ascii_character(ord(character.data)) if len(character.data) == 1 else 0x00

                self.terminal.display.write_buffer(byte, row=row, column=column)

    def _flush(self):
        self.terminal.display.flush()

        # TODO: Investigate different approaches to making cursor syncronization more
        # reliable - maybe it needs to be forced sometimes.
        cursor = self.vt100_screen.cursor

        self.terminal.display.move_cursor(row=cursor.y, column=cursor.x)
