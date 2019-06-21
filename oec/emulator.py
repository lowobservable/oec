"""
oec.emulator
~~~~~~~~~~~~
"""

import logging
import pyte

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

class VT100Emulator:
    """VT100 emulator."""

    def __init__(self, terminal, host):
        self.logger = logging.getLogger(__name__)

        self.terminal = terminal
        self.host = host

        # Initialize the VT100 screen.
        (rows, columns) = self.terminal.display.dimensions

        self.vt100_screen = pyte.Screen(columns, rows)

        self.vt100_screen.write_process_input = lambda data: host.write(data.encode())

        self.vt100_stream = pyte.ByteStream(self.vt100_screen)

        # Clear the screen.
        self.terminal.display.clear_screen()

        # Update the status line.
        self.terminal.display.status_line.write_string(45, 'VT100')

        # Load the address counter.
        self.terminal.display.load_address_counter(index=0)

    def handle_key(self, key, keyboard_modifiers, scan_code):
        """Handle a terminal keystroke."""
        bytes_ = self._map_key(key, keyboard_modifiers)

        if bytes_ is not None:
            self.host.write(bytes_)

    def handle_host_output(self, data):
        """Handle output from the host process."""
        self.vt100_stream.feed(data)

        self.update()

    def update(self):
        """Update the terminal with dirty changes from the VT100 screen - clears
        dirty lines after updating terminal.
        """
        self._apply(self.vt100_screen)

        self.vt100_screen.dirty.clear()

        self._flush()

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
        display = self.terminal.display

        display.flush()

        # Syncronize the cursor.
        cursor = self.vt100_screen.cursor

        address = display.calculate_address(row=cursor.y, column=cursor.x)

        # TODO: Investigate different approaches to reducing the need to syncronize the cursor
        # or make it more reliable.
        if address != display.address_counter:
            if self.logger.isEnabledFor(logging.DEBUG):
                self.logger.debug((f'Setting address counter: Address = {address}, '
                                   f'Address Counter = {display.address_counter}'))

            display.load_address_counter(address)
        else:
            if self.logger.isEnabledFor(logging.DEBUG):
                self.logger.debug((f'Skipping address counter: Address Counter = '
                                   f'{display.address_counter}'))
