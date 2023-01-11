"""
oec.device
~~~~~~~~~~
"""

import time
import logging
from more_itertools import chunked
from coax import read_feature_ids, parse_features, ReadTerminalId, ReadExtendedId, \
                 TerminalType, LoadAddressCounterLo, LoadSecondaryControl, \
                 SecondaryControl, ProtocolError
from coax.multiplexer import PORT_MAP_3299

from .interface import ExecuteError

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

    try:
        terminal_id = interface.execute(address_commands(device_address, ReadTerminalId()))
    except ProtocolError as error:
        logger.warning(f'READ_TERMINAL_ID error: {error}')

    extended_id = None

    if terminal_id is not None and terminal_id.type != TerminalType.DFT:
        # The READ_EXTENDED_ID command behaves similarly to the READ_MULTIPLE command and
        # will terminate when the two low order bits of the address counter are zero. In
        # order to read the entire 4 bytes of the extended ID reliably, we need to set
        # the secondary control register to disable "big read" and set the address counter
        # accordingly.
        #
        # The address counter will be reset later during device setup.
        commands = [LoadSecondaryControl(SecondaryControl(big=False)), LoadAddressCounterLo(0), ReadExtendedId()]

        try:
            extended_id = interface.execute(address_commands(device_address, commands))[-1]
        except ExecuteError as error:
            logger.warning(f'READ_EXTENDED_ID error: {error}')

    return (terminal_id, extended_id.hex() if extended_id is not None else None)

def get_features(interface, device_address):
    commands = read_feature_ids()

    ids = interface.execute(address_commands(device_address, commands))

    return parse_features(ids, commands)

def get_keyboard_description(terminal_id, extended_id):
    is_3278 = extended_id is None or not int(extended_id[0:2], 16) & 0x80

    if is_3278:
        description = '3278'

        id_map = {
            0b0001: 'APL',
            0b0010: 'TEXT',
            0b0100: 'TYPEWRITER-PSHICO',
            0b0101: 'APL',
            0b0110: 'TEXT',
            0b0111: 'APL-PSHICO',
            0b1000: 'DATAENTRY-2',
            0b1001: 'DATAENTRY-1',
            0b1010: 'TYPEWRITER',
            0b1100: 'DATAENTRY-2',
            0b1101: 'DATAENTRY-1',
            0b1110: 'TYPEWRITER'
        }

        if terminal_id.keyboard in id_map:
            description += '-' + id_map[terminal_id.keyboard]

        return description

    id_ = int(extended_id[0:2], 16) & 0x1f

    is_user = int(extended_id[0:2], 16) & 0x20

    if is_user:
        description = 'USER'

        if id_ in [1, 2, 3, 4]:
            description += f'-{id_}'

        return description

    is_ibm = not int(extended_id[6:8], 16) & 0x80

    description = 'IBM' if is_ibm else 'UNKNOWN'

    is_enhanced = int(extended_id[6:8], 16) & 0x01

    if is_enhanced:
        if id_ == 1:
            return description + '-ENHANCED'

        return None

    if id_ == 1:
        return description + '-TYPEWRITER'
    elif id_ == 2:
        return description + '-DATAENTRY'
    elif id_ == 3:
        return description + '-APL'

    return None

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
