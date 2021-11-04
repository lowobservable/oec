"""
oec.terminal
~~~~~~~~~~~~
"""

import os
import time
import logging
from more_itertools import chunked
from coax import read_feature_ids, parse_features, Poll, ReadTerminalId, ReadExtendedId, \
                 LoadControlRegister, TerminalType, Feature, PollAction, Control, \
                 ProtocolError

from .interface import address_commands
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

    def __init__(self, interface, device_address, terminal_id, extended_id, dimensions,
                 features, keymap):
        self.interface = interface
        self.device_address = device_address
        self.terminal_id = terminal_id
        self.extended_id = extended_id
        self.features = features

        self.control = Control(step_inhibit=False, display_inhibit=False,
                               cursor_inhibit=False, cursor_reverse=False,
                               cursor_blink=False)

        self.display = BufferedDisplay(self, dimensions, features.get(Feature.EAB))
        self.keyboard = Keyboard(keymap)

        self.alarm = False
        self.last_poll_keyboard_clicker = None

    def setup(self):
        """Load registers and clear the display."""
        self.load_control_register()

        if self.display.has_eab:
            self.display.load_eab_mask(0xff)

        self.display.clear(clear_status_line=True)

    def poll(self):
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

        poll_response = self.execute(Poll(poll_action))

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
        self.execute(LoadControlRegister(self.control))

    def execute(self, commands):
        return self.interface.execute(address_commands(self.device_address, commands))

    def execute_jumbo_write(self, data, create_first, create_subsequent, first_chunk_max_length_adjustment=-1):
        max_length = None

        if self.interface.jumbo_write_strategy == 'split':
            max_length = self.interface.jumbo_write_max_length

        chunks = _jumbo_write_split_data(data, max_length, first_chunk_max_length_adjustment)

        commands = [create_first(chunks[0])]

        for chunk in chunks[1:]:
            commands.append(create_subsequent(chunk))

        return self.execute(commands)

class UnsupportedTerminalError(Exception):
    """Unsupported terminal."""

def create_terminal(interface, device_address, poll_response, get_keymap):
    """Terminal factory."""
    # Read the terminal identifiers.
    (terminal_id, extended_id) = _read_terminal_ids(interface, device_address)

    logger.info(f'Terminal ID = {terminal_id}, Extended ID = {extended_id}')

    if terminal_id.type != TerminalType.CUT:
        raise UnsupportedTerminalError('Only CUT type terminals are supported')

    # Get the terminal dimensions.
    dimensions = MODEL_DIMENSIONS.get(terminal_id.model)

    if dimensions is None:
        raise UnsupportedTerminalError(f'Model {terminal_id.model} is not supported')

    logger.info(f'Rows = {dimensions.rows}, Columns = {dimensions.columns}')

    # Get the terminal features.
    features = _get_features(interface, device_address)

    logger.info(f'Features = {features}')

    # Get the keymap.
    keymap = get_keymap(terminal_id, extended_id)

    logger.info(f'Keymap = {keymap.name}')

    # Create the terminal.
    terminal = Terminal(interface, device_address, terminal_id, extended_id, dimensions,
                        features, keymap)

    return terminal

def _read_terminal_ids(interface, device_address, extended_id_retry_attempts=3):
    terminal_id = None
    extended_id = None

    try:
        terminal_id = interface.execute(address_commands(device_address, ReadTerminalId()))
    except ProtocolError as error:
        logger.warning(f'READ_TERMINAL_ID protocol error: {error}', exc_info=error)

    # Retry the READ_EXTENDED_ID command as it appears to fail frequently on the
    # first request - unlike the READ_TERMINAL_ID command,
    extended_id = None

    for attempt in range(extended_id_retry_attempts):
        try:
            extended_id = interface.execute(address_commands(device_address, ReadExtendedId()))

            break
        except ProtocolError as error:
            logger.warning(f'READ_EXTENDED_ID protocol error: {error}', exc_info=error)

        time.sleep(0.25)

    return (terminal_id, extended_id.hex() if extended_id is not None else None)

def _get_features(interface, device_address):
    commands = read_feature_ids()

    ids = interface.execute([address_commands(device_address, command) for command in commands])

    features = parse_features(ids, commands)

    # Add override features - for example, this can be used to add an unreported
    # EAB feature to a IBM 3179 terminal.
    if 'COAX_FEATURES' in os.environ:
        for override in os.environ['COAX_FEATURES'].split(','):
            if '@' not in override:
                logger.warning(f'Invalid feature override: {override}')
                continue

            (name, address) = override.split('@')

            try:
                feature = Feature[name]
            except KeyError:
                logger.warning(f'Invalid feature override: {override}')
                continue

            try:
                address = int(address)
            except ValueError:
                logger.warning(f'Invalid feature override: {override}')
                continue

            logger.info(f'Adding override feature {feature} @ {address}')

            features[feature] = address

    return features

def _jumbo_write_split_data(data, max_length, first_chunk_max_length_adjustment=-1):
    if max_length is None:
        return [data]

    if isinstance(data, tuple):
        length = len(data[0]) * data[1]
    else:
        length = len(data)

    first_chunk_max_length = max_length + first_chunk_max_length_adjustment

    if length <= first_chunk_max_length:
        return [data]

    if isinstance(data, tuple):
        data = data[0] * data[1]

    return [data[:first_chunk_max_length], *chunked(data[first_chunk_max_length:], max_length)]
