"""
oec.terminal
~~~~~~~~~~~~
"""

from .display import Dimensions, Display 
from .keyboard import Keyboard
from .keymap_3278_2 import KEYMAP as KEYMAP_3278_2
from .keymap_3483 import KEYMAP as KEYMAP_3483

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

def get_keymap(terminal_id, extended_id):
    """Get terminal keymap."""
    keymap = KEYMAP_3278_2

    if extended_id == 'c1348300':
        keymap = KEYMAP_3483

    return keymap

class Terminal:
    """Terminal information, devices and helpers."""

    def __init__(self, interface, terminal_id, extended_id):
        self.interface = interface
        self.terminal_id = terminal_id
        self.extended_id = extended_id

        dimensions = get_dimensions(self.terminal_id, self.extended_id)
        keymap = get_keymap(self.terminal_id, self.extended_id)

        self.display = Display(interface, dimensions)
        self.keyboard = Keyboard(keymap)
