"""
oec.interface
~~~~~~~~~~~~~
"""

import os
import logging
from textwrap import dedent

from coax import ReceiveTimeout

logger = logging.getLogger(__name__)

class ExecuteError(Exception):
    def __init__(self, errors, responses):
        if len(errors) == 1:
            message = str(errors[0])
        else:
            message = f'{len(errors)} occurred'

        super().__init__(message)

        self.errors = errors
        self.responses = responses

class InterfaceWrapper:
    def __init__(self, interface):
        self.interface = interface

        self.timeout = 0.001

        self.jumbo_write_strategy = _get_jumbo_write_strategy()
        self.jumbo_write_max_length = None

        if self.legacy_firmware_detected and self.jumbo_write_strategy is None:
            self.jumbo_write_strategy = 'split'
            self.jumbo_write_max_length = 1024

            _print_i1_jumbo_write_notice(self.jumbo_write_max_length)

    def __getattr__(self, attr):
        if attr == 'identifier':
            return self.interface.serial.port

        return getattr(self.interface, attr)

    def execute(self, commands, receive_timeout_is_error=True):
        if not isinstance(commands, list):
            return self.interface.execute(commands, self.timeout)

        responses = self.interface.execute(commands, self.timeout)
        errors = get_errors(responses, receive_timeout_is_error)

        if any(errors):
            raise ExecuteError(errors, responses)

        return responses

def get_errors(responses, receive_timeout_is_error):
    return [response for response in responses if isinstance(response, BaseException) and (receive_timeout_is_error or not isinstance(response, ReceiveTimeout))]

def _get_jumbo_write_strategy():
    value = os.environ.get('COAX_JUMBO')

    if value is None:
        return None

    if value == 'ignore':
        return value

    logger.warning(f'Unsupported COAX_JUMBO option: {value}')

    return None

def _print_i1_jumbo_write_notice(max_length):
    notice = f'''
    **** **** **** **** **** **** **** **** **** **** **** **** **** **** **** ****

    I think you are using an older firmware on the 1st generation, Arduino Mega
    based, interface which does not support the "jumbo write" required to write a
    full screen to the regen and EAB buffers.

    I'm going to split large writes into multiple smaller {max_length}-byte writes...

    If you want to override this behavior, you can set the COAX_JUMBO environment
    variable as follows:

    - COAX_JUMBO=ignore - try a jumbo write, anyway, use this option if you
                          believe you are seeing this behavior in error

    **** **** **** **** **** **** **** **** **** **** **** **** **** **** **** ****
    '''

    print(dedent(notice))
