"""
oec.device
~~~~~~~~~~
"""

import time
import logging
from more_itertools import chunked
from coax import read_feature_ids, parse_features, ReadTerminalId, ReadExtendedId, \
                 ProtocolError
from coax.multiplexer import PORT_MAP_3299

logger = logging.getLogger(__name__)

class Device:
    """A device."""

    def __init__(self, interface, device_address):
        self.interface = interface
        self.device_address = device_address

    def setup(self):
        """Setup the device."""
        raise NotImplementedError

    def get_poll_action(self):
        """Get the POLL action."""
        raise NotImplementedError

    def execute(self, commands):
        """Execute one or more commands."""
        return self.interface.execute(address_commands(self.device_address, commands))

    def execute_jumbo_write(self, data, create_first, create_subsequent, first_chunk_max_length_adjustment=-1):
        """Execute a jumbo write command that can be split."""
        max_length = None

        # The 3299 multiplexer appears to have some frame length limit, after which it will
        # stop transmitting. I've not determined the actual limit, but 1024 appears to work.
        if self.device_address is not None:
            max_length = 1024
        elif self.interface.jumbo_write_strategy == 'split':
            max_length = self.interface.jumbo_write_max_length

        chunks = _jumbo_write_split_data(data, max_length, first_chunk_max_length_adjustment)

        commands = [create_first(chunks[0])]

        for chunk in chunks[1:]:
            commands.append(create_subsequent(chunk))

        if len(commands) > 1 and logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'Jumbo write split into {len(commands)}')

        return self.execute(commands)

class UnsupportedDeviceError(Exception):
    """Unsupported device."""

def address_commands(device_address, commands):
    """Add device address to commands."""
    if isinstance(commands, list):
        return [(device_address, command) for command in commands]

    return (device_address, commands)

def format_address(interface, device_address):
    """Format a device address."""
    if device_address is None:
        return f'{interface.identifier}#0'

    try:
        return f'{interface.identifier}#{PORT_MAP_3299.index(device_address)}'
    except ValueError:
        return f'{interface.identifier}?{device_address:06b}'

def get_ids(interface, device_address, extended_id_retry_attempts=3):
    terminal_id = None
    extended_id = None

    try:
        terminal_id = interface.execute(address_commands(device_address, ReadTerminalId()))
    except ProtocolError as error:
        logger.warning(f'READ_TERMINAL_ID protocol error: {error}')

    # Retry the READ_EXTENDED_ID command as it appears to fail frequently on the
    # first request - unlike the READ_TERMINAL_ID command,
    extended_id = None

    for attempt in range(extended_id_retry_attempts):
        try:
            extended_id = interface.execute(address_commands(device_address, ReadExtendedId()))

            break
        except ProtocolError as error:
            logger.warning(f'READ_EXTENDED_ID protocol error: {error}')

        time.sleep(0.1)

    return (terminal_id, extended_id.hex() if extended_id is not None else None)

def get_features(interface, device_address):
    commands = read_feature_ids()

    ids = interface.execute(address_commands(device_address, commands))

    return parse_features(ids, commands)

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
