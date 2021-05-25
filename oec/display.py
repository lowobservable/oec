"""
oec.display
~~~~~~~~~~~
"""

from collections import namedtuple
import logging
from more_itertools import interleave
from sortedcontainers import SortedSet
from coax import read_address_counter_hi, read_address_counter_lo, \
                 load_address_counter_hi, load_address_counter_lo, write_data, \
                 eab_load_mask, eab_write_alternate

_ASCII_CHAR_MAP = {
    '>': 0x08,
    '<': 0x09,
    '[': 0x0a,
    ']': 0x0b,
    ')': 0x0c,
    '(': 0x0d,
    '}': 0x0e,
    '{': 0x0f,

    # 0x10 - A real space?
    '=': 0x11,
    '\'': 0x12,
    '"': 0x13,
    '/': 0x14,
    '\\': 0x15,
    '|': 0x16,
    '¦': 0x17,
    '?': 0x18,
    '!': 0x19,
    '$': 0x1a,
    '¢': 0x1b,
    '£': 0x1c,
    '¥': 0x1d,
    # 0x1e - A P/T looking symbol
    # 0x1f - A intertwined parens symbol

    '0': 0x20,
    '1': 0x21,
    '2': 0x22,
    '3': 0x23,
    '4': 0x24,
    '5': 0x25,
    '6': 0x26,
    '7': 0x27,
    '8': 0x28,
    '9': 0x29,
    'ß': 0x2a,
    '§': 0x2b,
    '#': 0x2c,
    '@': 0x2d,
    '%': 0x2e,
    '_': 0x2f,

    '&': 0x30,
    '-': 0x31,
    '.': 0x32,
    ',': 0x33,
    ':': 0x34,
    '+': 0x35,
    '¬': 0x36,
    '¯': 0x37, # ???
    '°': 0x38,
    # 0x39 - Accent?
    '^': 0x3a, # More like an accent
    '~': 0x3b, # More like an accent
    '¨': 0x3c,
    # 0x3d - Accute accent?
    # 0x3e - Opposite of accute accent?
    # 0x3f - A more extreme comma?

    'a': 0x80,
    'b': 0x81,
    'c': 0x82,
    'd': 0x83,
    'e': 0x84,
    'f': 0x85,
    'g': 0x86,
    'h': 0x87,
    'i': 0x88,
    'j': 0x89,
    'k': 0x8a,
    'l': 0x8b,
    'm': 0x8c,
    'n': 0x8d,
    'o': 0x8e,
    'p': 0x8f,

    'q': 0x90,
    'r': 0x91,
    's': 0x92,
    't': 0x93,
    'u': 0x94,
    'v': 0x95,
    'w': 0x96,
    'x': 0x97,
    'y': 0x98,
    'z': 0x99,
    'æ': 0x9a,
    'ø': 0x9b,
    'å': 0x9c,
    'ç': 0x9d,
    # 0x9e - Semi colon with top line
    # 0x9f - Asterisk with top line

    'A': 0xa0,
    'B': 0xa1,
    'C': 0xa2,
    'D': 0xa3,
    'E': 0xa4,
    'F': 0xa5,
    'G': 0xa6,
    'H': 0xa7,
    'I': 0xa8,
    'J': 0xa9,
    'K': 0xaa,
    'L': 0xab,
    'M': 0xac,
    'N': 0xad,
    'O': 0xae,
    'P': 0xaf,

    'Q': 0xb0,
    'R': 0xb1,
    'S': 0xb2,
    'T': 0xb3,
    'U': 0xb4,
    'V': 0xb5,
    'W': 0xb6,
    'X': 0xb7,
    'Y': 0xb8,
    'Z': 0xb9,
    'Æ': 0xba,
    'Ø': 0xbb,
    'Å': 0xbc,
    'Ç': 0xbd,
    ';': 0xbe,
    '*': 0xbf
}

_EBCDIC_CHAR_MAP = {ascii_character.encode('cp500')[0]: byte for ascii_character, byte in _ASCII_CHAR_MAP.items()}

ASCII_CHAR_MAP = [_ASCII_CHAR_MAP.get(character, 0x00) for character in map(chr, range(256))]

EBCDIC_CHAR_MAP = [_EBCDIC_CHAR_MAP.get(character, 0x00) for character in range(256)]

def encode_ascii_character(character):
    """Map an ASCII character to a terminal display character."""
    if character > 255:
        return 0x00

    return ASCII_CHAR_MAP[character]

def encode_ebcdic_character(character):
    """Map an EBCDIC character to a terminal display character."""
    if character > 255:
        return 0x00

    return EBCDIC_CHAR_MAP[character]

def encode_string(string, errors='replace'):
    """Map a string to terminal display characters."""
    return bytes([encode_ascii_character(character) for character
                  in string.encode('ascii', errors)])

# Does not include the status line row.
Dimensions = namedtuple('Dimensions', ['rows', 'columns'])

class Display:
    def __init__(self, terminal, dimensions, eab_address, jumbo_write_strategy=None):
        self.logger = logging.getLogger(__name__)

        self.terminal = terminal
        self.dimensions = dimensions
        self.eab_address = eab_address

        (rows, columns) = self.dimensions

        self.regen_buffer = bytearray(rows * columns)
        self.eab_buffer = bytearray(rows * columns)
        self.dirty = SortedSet()

        self.address_counter = None

        self.status_line = StatusLine(self)

        self.jumbo_write_strategy = jumbo_write_strategy

    @property
    def has_eab(self):
        return self.eab_address is not None

    def move_cursor(self, index=None, row=None, column=None, force_load=False):
        """Load the address counter."""
        address = self._calculate_address(index=index, row=row, column=column)

        # TODO: Verify that the address is within range - exclude status line.

        return self._load_address_counter(address, force_load)

    def load_eab_mask(self, mask):
        """Load the EAB mask."""
        if not self.has_eab:
            raise RuntimeError('No EAB feature')

        eab_load_mask(self.terminal.interface, self.eab_address, mask)

    def buffered_write(self, regen_byte, eab_byte, index=None, row=None, column=None):
        if index is None:
            if row is None or column is None:
                raise ValueError('Either index or row and column is required')

            index = self._get_index(row, column)

        # TODO: Verify that index is within range.

        if self.regen_buffer[index] == regen_byte and (self.eab_buffer[index] == eab_byte or not self.has_eab):
            return False

        self.regen_buffer[index] = regen_byte
        self.eab_buffer[index] = eab_byte if self.has_eab else 0x00

        self.dirty.add(index)

        return True

    def flush(self):
        for (start_index, end_index) in self._get_dirty_ranges():
            self._flush_range(start_index, end_index)

    def clear(self, clear_status_line=False):
        """Clear the screen."""
        (rows, columns) = self.dimensions

        if clear_status_line:
            address = 0
            count = (rows + 1) * columns
        else:
            address = columns
            count = rows * columns

        self._write((b'\x00', count), (b'\x00', count) if self.has_eab else None, address=address)

        # Update the buffers and dirty indicators to reflect the cleared screen.
        for index in range(rows * columns):
            self.regen_buffer[index] = 0x00
            self.eab_buffer[index] = 0x00

        self.dirty.clear()

        self.move_cursor(row=0, column=0, force_load=True)

    def toggle_cursor_blink(self):
        self.terminal.control.cursor_blink = not self.terminal.control.cursor_blink

        self.terminal.load_control_register()

    def toggle_cursor_reverse(self):
        self.terminal.control.cursor_reverse = not self.terminal.control.cursor_reverse

        self.terminal.load_control_register()

    def _get_index(self, row, column):
        return (row * self.dimensions.columns) + column

    def _calculate_address(self, index=None, row=None, column=None):
        if index is not None:
            return self.dimensions.columns + index

        if row is not None and column is not None:
            return self.dimensions.columns + self._get_index(row, column)

        raise ValueError('Either index or row and column is required')

    def _calculate_address_after_write(self, address, count):
        if address is None:
            return None

        address += count

        (rows, columns) = self.dimensions

        # TODO: Determine the correct behavior here...
        if self.address_counter >= self._calculate_address((rows * columns) - 1):
            return None

        return address

    def _read_address_counter(self):
        hi = read_address_counter_hi(self.terminal.interface)
        lo = read_address_counter_lo(self.terminal.interface)

        return (hi << 8) | lo

    def _load_address_counter(self, address, force_load):
        if address == self.address_counter and not force_load:
            return False

        (hi, lo) = _split_address(address)
        (current_hi, current_lo) = _split_address(self.address_counter)

        if hi != current_hi or force_load:
            load_address_counter_hi(self.terminal.interface, hi)

        if lo != current_lo or force_load:
            load_address_counter_lo(self.terminal.interface, lo)

        self.address_counter = address

        return True

    def _get_dirty_ranges(self):
        if not self.dirty:
            return []

        # TODO: Implement multiple ranges with optimization.
        return [(self.dirty[0], self.dirty[-1])]

    def _flush_range(self, start_index, end_index):
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(f'Flushing changes for range {start_index}-{end_index}')

        regen_data = self.regen_buffer[start_index:end_index+1]
        eab_data = self.eab_buffer[start_index:end_index+1] if self.has_eab else None

        address = self._calculate_address(start_index)

        try:
            self._write(regen_data, eab_data, address=address)
        except Exception as error:
            # TODO: This could leave the address_counter incorrect.
            self.logger.error(f'Write error: {error}', exc_info=error)

        for index in range(start_index, end_index + 1):
            self.dirty.discard(index)

        return self.address_counter

    def _write(self, regen_data, eab_data, address=None, restore_original_address=False):
        if eab_data is not None:
            if not self.has_eab:
                raise RuntimeError('No EAB feature')

            if isinstance(regen_data, tuple) and isinstance(eab_data, tuple):
                if len(regen_data[0]) != len(eab_data[0]):
                    raise ValueError('Regen and EAB pattern length must be equal')

                if regen_data[1] != eab_data[1]:
                    raise ValueError('Regen and EAB pattern count must be equal')
            elif not isinstance(regen_data, tuple) and not isinstance(eab_data, tuple):
                if len(regen_data) != len(eab_data):
                    raise ValueError('Regen and EAB data length must be equal')
            else:
                raise ValueError('Regen and EAB data must be provided in same form')

        if restore_original_address:
            original_address = self.address_counter

            if original_address is None:
                original_address = self._read_address_counter()

        if address is not None:
            self._load_address_counter(address, force_load=False)

        if eab_data is not None:
            # Validation of regen and EAB data form has been performed.
            if isinstance(regen_data, tuple):
                data = (bytes(interleave(regen_data[0], eab_data[0])), regen_data[1])
            else:
                data = bytes(interleave(regen_data, eab_data))

            eab_write_alternate(self.terminal.interface, self.eab_address, data,
                    jumbo_write_strategy=self.jumbo_write_strategy)
        else:
            write_data(self.terminal.interface, regen_data,
                    jumbo_write_strategy=self.jumbo_write_strategy)

        if isinstance(regen_data, tuple):
            length = len(regen_data[0]) * regen_data[1]
        else:
            length = len(regen_data)

        self.address_counter = self._calculate_address_after_write(address, length)

        if restore_original_address:
            self._load_address_counter(original_address, force_load=True)

# TODO: add validation of column and data length for write() - must be inside status line
class StatusLine:
    def __init__(self, display):
        self.display = display

        self.columns = display.dimensions.columns

    def write(self, column, data):
        self.display._write(data, None, address=column, restore_original_address=True)

    def write_string(self, column, string):
        self.write(column, encode_string(string))

    def write_keyboard_modifiers(self, modifiers):
        indicators = bytearray(1)

        if modifiers.is_shift():
            indicators[0] = 0xda

        self.write(35, indicators)

    def write_keyboard_insert(self, insert):
        indicators = bytearray(1)

        if insert:
            indicators[0] = 0xd3

        self.write(45, indicators)

def _split_address(address):
    if address is None:
        return (None, None)

    return ((address >> 8) & 0xff, address & 0xff)
