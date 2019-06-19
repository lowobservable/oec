"""
oec.emulator
~~~~~~~~~~~~
"""

import logging
import pyte
from coax import write_data

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

        self.rows = self.terminal.dimensions.rows
        self.columns = self.terminal.dimensions.columns

        self.vt100_screen = pyte.Screen(self.columns, self.rows)

        self.vt100_screen.write_process_input = lambda data: host.write(data.encode())

        self.vt100_stream = pyte.ByteStream(self.vt100_screen)

        # TODO: Consider moving the following three attributes to the Terminal class
        # and moving the associated methods.
        self.buffer = bytearray(self.rows * self.columns)
        self.dirty = [False for index in range(self.rows * self.columns)]

        self.address_counter = self._calculate_address(0)

        # Clear the screen.
        self.terminal.clear_screen()

        # Update the status line.
        self.terminal.status_line.write_string(45, 'VT100')

        # Load the address counter.
        self.terminal.interface.offload_load_address_counter(self.address_counter)

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

    def _get_index(self, row, column):
        return (row * self.columns) + column

    def _calculate_address(self, cursor_index):
        return self.columns + cursor_index

    def _apply(self, screen):
        for row in screen.dirty:
            row_buffer = screen.buffer[row]

            for column in range(self.columns):
                character = row_buffer[column]

                # TODO: Investigate multi-byte or zero-byte cases further.
                # TODO: Add additional mapping for special cases such as '^'...
                byte = encode_ascii_character(ord(character.data)) if len(character.data) == 1 else 0x00

                index = self._get_index(row, column)

                if self.buffer[index] != byte:
                    self.buffer[index] = byte
                    self.dirty[index] = True

    def _flush(self):
        for (start_index, end_index) in self._get_dirty_ranges():
            self._flush_range(start_index, end_index)

        # Syncronize the cursor.
        cursor = self.vt100_screen.cursor

        address = self._calculate_address(self._get_index(cursor.y, cursor.x))

        # TODO: Investigate different approaches to reducing the need to syncronize the cursor
        # or make it more reliable.
        if address != self.address_counter:
            if self.logger.isEnabledFor(logging.DEBUG):
                self.logger.debug((f'Setting address counter: Address = {address}, '
                                   f'Address Counter = {self.address_counter}'))

            self.terminal.interface.offload_load_address_counter(address)

            self.address_counter = address
        else:
            if self.logger.isEnabledFor(logging.DEBUG):
                self.logger.debug((f'Skipping address counter: Address Counter = '
                                   f'{self.address_counter}'))

    def _get_dirty_ranges(self):
        ranges = []

        start_index = 0

        while start_index < len(self.dirty):
            if self.dirty[start_index]:
                break

            start_index += 1

        end_index = len(self.dirty) - 1

        while end_index >= 0:
            if self.dirty[end_index]:
                break

            end_index -= 1

        if start_index < len(self.dirty) and end_index >= 0:
            ranges.append((start_index, end_index))

        return ranges

    def _flush_range(self, start_index, end_index):
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(f'Flushing changes for range {start_index}-{end_index}')

        data = self.buffer[start_index:end_index+1]

        address = self._calculate_address(start_index)

        # TODO: Consider using offload for all writing - set address to None if it is the
        # same as the current address counter to avoid the additional load command.
        if address != self.address_counter:
            try:
                self.terminal.interface.offload_write(data, address=address)
            except Exception as error:
                self.logger.error(f'Offload write error: {error}', exc_info=error)

            self.address_counter = address + len(data)
        else:
            try:
                write_data(self.terminal.interface, data)
            except Exception as error:
                self.logger.error(f'WRITE_DATA error: {error}', exc_info=error)

            self.address_counter += len(data)

        # Force the address counter to be updated...
        if self.address_counter >= self._calculate_address((self.rows * self.columns) - 1):
            self.address_counter = None

        for index in range(start_index, end_index+1):
            self.dirty[index] = False

        return self.address_counter
