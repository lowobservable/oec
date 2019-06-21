"""
oec.terminal
~~~~~~~~~~~~
"""

import time
import logging
from coax import read_terminal_id, read_extended_id, ReceiveError, ProtocolError

from .display import Dimensions, Display 
from .keyboard import Keyboard
from .keymap_3278_2 import KEYMAP as KEYMAP_3278_2
from .keymap_3483 import KEYMAP as KEYMAP_3483

logger = logging.getLogger(__name__)

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

def read_terminal_ids(interface, extended_id_retry_attempts=3):
    terminal_id = None
    extended_id = None

    try:
        terminal_id = read_terminal_id(interface)
    except ReceiveError as error:
        logger.warning(f'READ_TERMINAL_ID receive error: {error}', exc_info=error)
    except ProtocolError as error:
        logger.warning(f'READ_TERMINAL_ID protocol error: {error}', exc_info=error)

    # Retry the READ_EXTENDED_ID command as it appears to fail frequently on the
    # first request - unlike the READ_TERMINAL_ID command,
    extended_id = None

    for attempt in range(extended_id_retry_attempts):
        try:
            extended_id = read_extended_id(interface)

            break
        except ReceiveError as error:
            logger.warning(f'READ_EXTENDED_ID receive error: {error}', exc_info=error)
        except ProtocolError as error:
            logger.warning(f'READ_EXTENDED_ID protocol error: {error}', exc_info=error)

        time.sleep(0.25)

    return (terminal_id, extended_id.hex() if extended_id is not None else None)

class Terminal:
    """Terminal information and devices."""

    def __init__(self, interface, terminal_id, extended_id):
        self.interface = interface
        self.terminal_id = terminal_id
        self.extended_id = extended_id

        dimensions = get_dimensions(self.terminal_id, self.extended_id)
        keymap = get_keymap(self.terminal_id, self.extended_id)

        self.display = Display(interface, dimensions)
        self.keyboard = Keyboard(keymap)
