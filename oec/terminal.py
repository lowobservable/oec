"""
oec.terminal
~~~~~~~~~~~~
"""

import os
import time
import logging
from textwrap import dedent
from coax import poll, read_terminal_id, read_extended_id, get_features, \
                 load_control_register, TerminalType, Feature, PollAction, Control, \
                 ReceiveError, ProtocolError

from .display import Dimensions, BufferedDisplay
from .keyboard import Keyboard

logger = logging.getLogger(__name__)

MODEL_DIMENSIONS = {
    2: Dimensions(24, 80),
    3: Dimensions(32, 80),
    4: Dimensions(43, 80),
    5: Dimensions(27, 132)
}

class Terminal:
    """The terminal."""

    def __init__(self, interface, terminal_id, extended_id, dimensions, features,
                 keymap, jumbo_write_strategy=None):
        self.interface = interface
        self.terminal_id = terminal_id
        self.extended_id = extended_id
        self.features = features

        self.control = Control(step_inhibit=False, display_inhibit=False,
                               cursor_inhibit=False, cursor_reverse=False,
                               cursor_blink=False)

        self.display = BufferedDisplay(self, dimensions, features.get(Feature.EAB),
                                       jumbo_write_strategy=jumbo_write_strategy)
        self.keyboard = Keyboard(keymap)

        self.alarm = False
        self.last_poll_keyboard_clicker = None

    def setup(self):
        """Load registers and clear the display."""
        self.load_control_register()

        if self.display.has_eab:
            self.display.load_eab_mask(0xff)

        self.display.clear(clear_status_line=True)

    def poll(self, **kwargs):
        """Execute a POLL command with queued actions."""
        poll_action = PollAction.NONE

        # Convert a queued alarm or keyboard clicker change to POLL action.
        if self.alarm:
            poll_action = PollAction.ALARM
        elif self.keyboard.clicker != self.last_poll_keyboard_clicker:
            if self.keyboard.clicker:
                poll_action = PollAction.ENABLE_KEYBOARD_CLICKER
            else:
                poll_action = PollAction.DISABLE_KEYBOARD_CLICKER

        poll_response = poll(self.interface, poll_action, **kwargs)

        # Clear the queued alarm and keyboard clicker change if the POLL was
        # successful.
        if poll_action == PollAction.ALARM:
            self.alarm = False
        elif poll_action in [PollAction.ENABLE_KEYBOARD_CLICKER,
                             PollAction.DISABLE_KEYBOARD_CLICKER]:
            self.last_poll_keyboard_clicker = self.keyboard.clicker

        return poll_response

    def sound_alarm(self):
        """Queue an alarm on next POLL command."""
        self.alarm = True

    def load_control_register(self):
        """Execute a LOAD_CONTROL_REGISTER command."""
        load_control_register(self.interface, self.control)

class UnsupportedTerminalError(Exception):
    """Unsupported terminal."""

def create_terminal(interface, poll_response, get_keymap):
    """Terminal factory."""
    jumbo_write_strategy = _get_jumbo_write_strategy()

    # Read the terminal identifiers.
    (terminal_id, extended_id) = _read_terminal_ids(interface)

    logger.info(f'Terminal ID = {terminal_id}, Extended ID = {extended_id}')

    if terminal_id.type != TerminalType.CUT:
        raise UnsupportedTerminalError('Only CUT type terminals are supported')

    # Get the terminal dimensions.
    dimensions = MODEL_DIMENSIONS.get(terminal_id.model)

    if dimensions is None:
        raise UnsupportedTerminalError(f'Model {terminal_id.model} is not supported')

    logger.info(f'Rows = {dimensions.rows}, Columns = {dimensions.columns}')

    # Get the terminal features.
    features = get_features(interface)

    logger.info(f'Features = {features}')

    if Feature.EAB in features:
        if interface.legacy_firmware_detected and jumbo_write_strategy is None:
            del features[Feature.EAB]

            _print_no_i1_eab_notice()

    # Get the keymap.
    keymap = get_keymap(terminal_id, extended_id)

    logger.info(f'Keymap = {keymap.name}')

    # Create the terminal.
    terminal = Terminal(interface, terminal_id, extended_id, dimensions, features,
                        keymap, jumbo_write_strategy=jumbo_write_strategy)

    return terminal

def _read_terminal_ids(interface, extended_id_retry_attempts=3):
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

def _get_jumbo_write_strategy():
    value = os.environ.get('COAX_JUMBO')

    if value is None:
        return None

    if value in ['split', 'ignore']:
        return value

    logger.warning(f'Unsupported COAX_JUMBO option: {value}')

    return None

def _print_no_i1_eab_notice():
    notice = '''
    **** **** **** **** **** **** **** **** **** **** **** **** **** **** **** ****

    Your terminal is reporting the existence of an EAB feature that allows extended
    colors and formatting, however...

    I think you are using an older firmware on the 1st generation, Arduino Mega
    based, interface which does not support the "jumbo write" required to write a
    full screen to the regen and EAB buffers.

    I'm going to continue as if the EAB feature did not exist...

    If you want to override this behavior, you can set the COAX_JUMBO environment
    variable as follows:

    - COAX_JUMBO=split  - split large writes into multiple smaller 32-byte writes
                          before sending to the interface, this will result in
                          additional round trips to the interface which may
                          manifest as visible incremental changes being applied
                          to the screen
    - COAX_JUMBO=ignore - try a jumbo write, anyway, use this option if you
                          believe you are seeing this behavior in error

    **** **** **** **** **** **** **** **** **** **** **** **** **** **** **** ****
    '''

    print(dedent(notice))
