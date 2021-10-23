"""
oec.interface
~~~~~~~~~~~~~
"""

import os
import logging
from textwrap import dedent

from more_itertools import chunked

logger = logging.getLogger(__name__)

class AggregateExecuteError(Exception):
    def __init__(self, errors, responses):
        super().__init__('One or more errors occurred')

        self.errors = errors
        self.responses = responses

class InterfaceWrapper:
    def __init__(self, interface):
        self.interface = interface

        self.timeout = 0.1

        self.jumbo_write_strategy = _get_jumbo_write_strategy()
        self.jumbo_write_max_length = None

        if self.legacy_firmware_detected and self.jumbo_write_strategy is None:
            _print_i1_jumbo_write_notice()

            self.jumbo_write_strategy = 'split'

        if self.jumbo_write_strategy == 'split':
            self.jumbo_write_max_length = 1024

    def __getattr__(self, attr):
        return getattr(self.interface, attr)

    def execute(self, commands):
        if not isinstance(commands, list):
            return self.interface.execute(commands, self.timeout)

        responses = self.interface.execute(commands, self.timeout)

        errors = [response for response in responses if isinstance(response, BaseException)]

        if any(errors):
            raise AggregateExecuteError(errors, responses)

        return responses

    def jumbo_write_split_data(self, data, first_chunk_max_length_adjustment=-1):
        if self.jumbo_write_strategy != 'split':
            return [data]

        if isinstance(data, tuple):
            length = len(data[0]) * data[1]
        else:
            length = len(data)

        first_chunk_max_length = self.jumbo_write_max_length + first_chunk_max_length_adjustment

        if length <= first_chunk_max_length:
            return [data]

        if isinstance(data, tuple):
            data = data[0] * data[1]

        return [data[:first_chunk_max_length], *chunked(data[first_chunk_max_length:], self.jumbo_write_max_length)]

def address_commands(device_address, commands):
    if isinstance(commands, list):
        return [(device_address, command) for command in commands]

    return (device_address, commands)

def _get_jumbo_write_strategy():
    value = os.environ.get('COAX_JUMBO')

    if value is None:
        return None

    if value in ['split', 'ignore']:
        return value

    logger.warning(f'Unsupported COAX_JUMBO option: {value}')

    return None

def _print_i1_jumbo_write_notice():
    notice = '''
    **** **** **** **** **** **** **** **** **** **** **** **** **** **** **** ****

    I think you are using an older firmware on the 1st generation, Arduino Mega
    based, interface which does not support the "jumbo write" required to write a
    full screen to the regen and EAB buffers.

    I'm going to split large writes into multiple smaller 1024-byte writes...

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
