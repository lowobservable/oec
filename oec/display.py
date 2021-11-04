"""
oec.display
~~~~~~~~~~~
"""

from collections import namedtuple
from itertools import zip_longest
import logging
from more_itertools import interleave
from sortedcontainers import SortedSet
from coax import ReadAddressCounterHi, ReadAddressCounterLo, LoadAddressCounterHi, \
                 LoadAddressCounterLo, WriteData, EABLoadMask, EABWriteAlternate, Data

# Does not include the status line row.
Dimensions = namedtuple('Dimensions', ['rows', 'columns'])

class Display:
    def __init__(self, terminal, dimensions, eab_address):
        self.logger = logging.getLogger(__name__)

        self.terminal = terminal
        self.dimensions = dimensions
        self.eab_address = eab_address

        self.address_counter = None
        self.last_address = ((dimensions.rows + 1) * dimensions.columns) - 1

        self.status_line = StatusLine(self)

    def clear(self, clear_status_line=False):
        """Clear the screen."""
        (rows, columns) = self.dimensions

        if clear_status_line:
            address = 0
            count = (rows + 1) * columns
        else:
            address = columns
            count = rows * columns

        regen_data = (b'\x00', count)
        eab_data = (b'\x00', count) if self.has_eab else None

        self.write(regen_data, eab_data, address=address)

        self.move_cursor(row=0, column=0, force_load=True)

    def move_cursor(self, address=None, index=None, row=None, column=None, force_load=False):
        """Load the address counter."""
        address = self._calculate_address(address, index, row, column)

        if address is None:
            raise ValueError('Either address, index or row and column is required')

        return self._load_address_counter(address, force_load)

    def write(self, regen_data, eab_data, address=None, index=None, row=None, column=None, restore_original_address=False):
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
            original_address = self.address_counter if self.address_counter is not None else self._read_address_counter()

        address = self._calculate_address(address, index, row, column)

        if address is not None:
            self._load_address_counter(address, force_load=False)

        if eab_data is not None:
            if isinstance(regen_data, tuple):
                data = (bytes(interleave(regen_data[0], eab_data[0])), regen_data[1])
            else:
                data = bytes(interleave(regen_data, eab_data))

            self._eab_write_alternate(data)
        else:
            self._write_data(regen_data)

        if isinstance(regen_data, tuple):
            count = len(regen_data[0]) * regen_data[1]
        else:
            count = len(regen_data)

        self.address_counter = self._calculate_address_after_write(self.address_counter, count)

        if restore_original_address:
            self._load_address_counter(original_address, force_load=True)

    @property
    def has_eab(self):
        return self.eab_address is not None

    def load_eab_mask(self, mask):
        if not self.has_eab:
            raise RuntimeError('No EAB feature')

        self.terminal.execute(EABLoadMask(self.eab_address, mask))

    def toggle_cursor_blink(self):
        self.terminal.control.cursor_blink = not self.terminal.control.cursor_blink

        self.terminal.load_control_register()

    def toggle_cursor_reverse(self):
        self.terminal.control.cursor_reverse = not self.terminal.control.cursor_reverse

        self.terminal.load_control_register()

    def _calculate_address(self, address=None, index=None, row=None, column=None):
        if index is not None:
            address = self.dimensions.columns + index

        if row is not None and column is not None:
            address = self.dimensions.columns + (row * self.dimensions.columns) + column

        if address is None:
            return None

        if address > self.last_address:
            raise ValueError('Address is out of range')

        return address

    def _calculate_address_after_write(self, address, count):
        if address is None:
            return None

        address += count

        # TODO: Determine the correct behavior here...
        if address > self.last_address:
            return None

        return address

    def _read_address_counter(self):
        [hi, lo] = self.terminal.execute([ReadAddressCounterHi(), ReadAddressCounterLo()])

        self.address_counter = (hi << 8) | lo

        return self.address_counter

    def _load_address_counter(self, address, force_load):
        if address == self.address_counter and not force_load:
            return False

        (hi, lo) = _split_address(address)
        (current_hi, current_lo) = _split_address(self.address_counter)

        commands = []

        if hi != current_hi or force_load:
            commands.append(LoadAddressCounterHi(hi))

        if lo != current_lo or force_load:
            commands.append(LoadAddressCounterLo(lo))

        self.terminal.execute(commands)

        self.address_counter = address

        return True

    def _write_data(self, data):
        self.terminal.execute_jumbo_write(data, WriteData, Data, -1)

    def _eab_write_alternate(self, data):
        # The EAB_WRITE_ALTERNATE command data must be split so that the two bytes
        # do not get separated, otherwise the write will be incorrect.
        self.terminal.execute_jumbo_write(data, lambda chunk: EABWriteAlternate(self.eab_address, chunk), Data, -2)

def _split_address(address):
    if address is None:
        return (None, None)

    return ((address >> 8) & 0xff, address & 0xff)

class StatusLine:
    def __init__(self, display):
        self.display = display

        self.columns = display.dimensions.columns

    def write(self, column, data):
        if column >= self.columns:
            raise ValueError('Column is out of range')

        if column + len(data) > self.columns:
            raise ValueError('Length is out of range')

        self.display.write(data, None, address=column, restore_original_address=True)

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

class BufferedDisplay(Display):
    def __init__(self, terminal, dimensions, eab_address):
        super().__init__(terminal, dimensions, eab_address)

        length = (self.dimensions.rows + 1) * self.dimensions.columns

        self.regen_buffer = bytearray(length)
        self.eab_buffer = bytearray(length) if self.has_eab else None
        self.dirty = SortedSet()

    def buffered_write_byte(self, regen_byte, eab_byte, address=None, index=None, row=None, column=None):
        if eab_byte is not None:
            if not self.has_eab:
                raise RuntimeError('No EAB feature')

        address = self._calculate_address(address, index, row, column)

        if address is None:
            raise ValueError('Either address, index or row and column is required')

        if self.regen_buffer[address] == regen_byte and (not self.has_eab or self.eab_buffer[address] == eab_byte):
            return False

        self.regen_buffer[address] = regen_byte

        if self.has_eab:
            self.eab_buffer[address] = eab_byte

        self.dirty.add(address)

        return True

    def flush(self):
        dirty_ranges = self._get_dirty_ranges()

        if not dirty_ranges:
            return False

        for (start_address, end_address) in dirty_ranges:
            self._write_range(start_address, end_address)

        return True

    def write(self, regen_data, eab_data, address=None, index=None, row=None, column=None, restore_original_address=False):
        start_address = self._calculate_address(address, index, row, column)

        # Unlike a unbuffered write, the current address is required in order to commit the write.
        if start_address is None:
            start_address = self.address_counter if self.address_counter is not None else self._read_address_counter()

        super().write(regen_data, eab_data, address=address, index=index, row=row, column=column,
                      restore_original_address=restore_original_address)

        self._commit(start_address, regen_data, eab_data)

    def _commit(self, start_address, regen_data, eab_data):
        if isinstance(regen_data, tuple):
            expanded_regen_data = regen_data[0] * regen_data[1]
            expanded_eab_data = eab_data[0] * eab_data[1] if eab_data is not None else []
        else:
            expanded_regen_data = regen_data
            expanded_eab_data = eab_data if eab_data is not None else []

        address = start_address

        for (regen_byte, eab_byte) in zip_longest(expanded_regen_data, expanded_eab_data):
            self.regen_buffer[address] = regen_byte

            if eab_byte is not None:
                self.eab_buffer[address] = eab_byte

            self.dirty.discard(address)

            address += 1

    def _write_range(self, start_address, end_address):
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(f'Writing range {start_address}-{end_address}')

        regen_data = self.regen_buffer[start_address:end_address+1]
        eab_data = self.eab_buffer[start_address:end_address+1] if self.has_eab else None

        try:
            self.write(regen_data, eab_data, address=start_address)
        except Exception as error:
            # TODO: This could leave the address_counter incorrect.
            self.logger.error(f'Write error: {error}', exc_info=error)

    def _get_dirty_ranges(self):
        if not self.dirty:
            return []

        # TODO: Implement multiple ranges with optimization.
        return [(self.dirty[0], self.dirty[-1])]

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
