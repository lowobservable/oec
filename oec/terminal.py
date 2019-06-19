"""
oec.terminal
~~~~~~~~~~~~
"""

from collections import namedtuple

from .display import StatusLine
from .keyboard import Keyboard
from .keymap_3278_2 import KEYMAP as KEYMAP_3278_2
from .keymap_3483 import KEYMAP as KEYMAP_3483

# Does not include the status line row.
Dimensions = namedtuple('Dimensions', ['rows', 'columns'])

MODEL_DIMENSIONS = {
    2: Dimensions(24, 80),
    3: Dimensions(32, 80),
    4: Dimensions(43, 80),
    5: Dimensions(27, 132)
}

def get_dimensions(terminal_id, extended_id):
    """Get terminal display dimensions."""
    if not terminal_id.model in MODEL_DIMENSIONS:
        raise ValueError(f'Model {terminal_id.model} is not supported')

    return MODEL_DIMENSIONS[terminal_id.model]

def get_keyboard(terminal_id, extended_id):
    """Get keyboard configured with terminal keymap."""
    keymap = KEYMAP_3278_2

    if extended_id == 'c1348300':
        keymap = KEYMAP_3483

    return Keyboard(keymap)

class Terminal:
    """Terminal information, devices and helpers."""

    def __init__(self, interface, terminal_id, extended_id):
        self.interface = interface
        self.terminal_id = terminal_id
        self.extended_id = extended_id

        self.dimensions = get_dimensions(self.terminal_id, self.extended_id)
        self.keyboard = get_keyboard(self.terminal_id, self.extended_id)

        self.status_line = StatusLine(self.interface, self.dimensions.columns)

    def clear_screen(self):
        """Clear the screen - including the status line."""
        (rows, columns) = self.dimensions

        self.interface.offload_write(b'\x00', address=0, repeat=((rows+1)*columns)-1)

        self.interface.offload_load_address_counter(columns)
