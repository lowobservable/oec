import sys
import os
import signal
import logging
from coax import open_serial_interface, TerminalType

from .args import parse_args
from .interface import InterfaceWrapper
from .controller import Controller
from .device import get_ids, get_features, get_keyboard_description, UnsupportedDeviceError
from .terminal import Terminal
from .tn3270 import TN3270Session

# VT100 emulation is not supported on Windows.
IS_VT100_AVAILABLE = False

if os.name == 'posix':
    from .vt100 import VT100Session

    IS_VT100_AVAILABLE = True

from .keymap_3278_typewriter import KEYMAP as KEYMAP_3278_TYPEWRITER
from .keymap_ibm_typewriter import KEYMAP as KEYMAP_IBM_TYPEWRITER
from .keymap_ibm_enhanced import KEYMAP as KEYMAP_IBM_ENHANCED

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger('oec.main')

CONTROLLER = None

def _get_keymap(keyboard_description):
    if keyboard_description.startswith('3278'):
        return KEYMAP_3278_TYPEWRITER
    elif keyboard_description.startswith('IBM-TYPEWRITER'):
        return KEYMAP_IBM_TYPEWRITER
    elif keyboard_description.startswith('IBM-ENHANCED'):
        return KEYMAP_IBM_ENHANCED

    return KEYMAP_3278_TYPEWRITER

def _create_device(args, interface, device_address, poll_response):
    # Read the terminal identifiers.
    (terminal_id, extended_id) = get_ids(interface, device_address)

    logger.info(f'Terminal ID = {terminal_id}')

    if terminal_id.type != TerminalType.CUT:
        raise UnsupportedDeviceError('Only CUT type terminals are supported')

    logger.info(f'Extended ID = {extended_id}')

    if extended_id is not None:
        logger.info(f'Model = IBM {extended_id[2:6]} or equivalent')

    keyboard_description = get_keyboard_description(terminal_id, extended_id)

    logger.info(f'Keyboard = {keyboard_description}')

    # Read the terminal features.
    features = get_features(interface, device_address)

    logger.info(f'Features = {features}')

    # Get the keymap.
    keymap = _get_keymap(keyboard_description)

    logger.info(f'Keymap = {keymap.name}')

    # Create the terminal.
    terminal = Terminal(interface, device_address, terminal_id, extended_id, features, keymap)

    return terminal

def _create_session(args, device):
    if args.emulator == 'tn3270':
        return TN3270Session(device, args.host, args.port, args.device_names, args.character_encoding)

    if args.emulator == 'vt100' and IS_VT100_AVAILABLE:
        host_command = [args.command, *args.command_args]

        return VT100Session(device, host_command)

    raise ValueError('Unsupported emulator')

def _signal_handler(number, frame):
    global CONTROLLER

    logger.info('Stopping controller...')

    if CONTROLLER:
        CONTROLLER.stop()

        CONTROLLER = None

signal.signal(signal.SIGINT, _signal_handler)
signal.signal(signal.SIGTERM, _signal_handler)

def main():
    global CONTROLLER

    args = parse_args(sys.argv[1:], IS_VT100_AVAILABLE)

    create_device = lambda interface, device_address, poll_response: _create_device(args, interface, device_address, poll_response)
    create_session = lambda device: _create_session(args, device)

    logger.info('Starting controller...')

    with open_serial_interface(args.serial_port) as interface:
        CONTROLLER = Controller(InterfaceWrapper(interface), create_device, create_session)

        CONTROLLER.run()

if __name__ == '__main__':
    main()
