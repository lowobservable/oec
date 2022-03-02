import os
import signal
import codecs
import logging
import argparse
from coax import open_serial_interface, TerminalType

from .interface import InterfaceWrapper
from .controller import Controller
from .device import get_ids, get_features, UnsupportedDeviceError
from .terminal import Terminal
from .tn3270 import TN3270Session

# VT100 emulation is not supported on Windows.
IS_VT100_AVAILABLE = False

if os.name == 'posix':
    from .vt100 import VT100Session

    IS_VT100_AVAILABLE = True

from .keymap_3278_2 import KEYMAP as KEYMAP_3278_2
from .keymap_3483 import KEYMAP as KEYMAP_3483

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger('oec.main')

CONTROLLER = None

def _get_keymap(terminal_id, extended_id):
    keymap = KEYMAP_3278_2

    if extended_id == 'c1348300':
        keymap = KEYMAP_3483

    if extended_id == 'c1347200':
        keymap = KEYMAP_3483

    return keymap

def _get_character_encoding(encoding):
    try:
        codecs.lookup(encoding)
    except LookupError:
        raise argparse.ArgumentTypeError(f'invalid encoding: {encoding}')

    return encoding

def _create_device(args, interface, device_address, poll_response):
    # Read the terminal identifiers.
    (terminal_id, extended_id) = get_ids(interface, device_address)

    logger.info(f'Terminal ID = {terminal_id}, Extended ID = {extended_id}')

    if terminal_id.type != TerminalType.CUT:
        raise UnsupportedDeviceError('Only CUT type terminals are supported')

    # Read the terminal features.
    features = get_features(interface, device_address)

    logger.info(f'Features = {features}')

    # Get the keymap.
    keymap = _get_keymap(terminal_id, extended_id)

    logger.info(f'Keymap = {keymap.name}')

    # Create the terminal.
    terminal = Terminal(interface, device_address, terminal_id, extended_id, features, keymap)

    return terminal

def _create_session(args, device):
    if args.emulator == 'tn3270':
        return TN3270Session(device, args.host, args.port, args.character_encoding)

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

    parser = argparse.ArgumentParser(description='IBM 3270 terminal controller')

    parser.add_argument('serial_port', help='Serial port')

    subparsers = parser.add_subparsers(dest='emulator', required=True,
                                       description='Emulator')

    tn3270_parser = subparsers.add_parser('tn3270', description='TN3270 emulator',
                                          help='TN3270 emulator')

    tn3270_parser.add_argument('host', help='Hostname')
    tn3270_parser.add_argument('port', nargs='?', default=23, type=int)

    tn3270_parser.add_argument('--codepage', metavar='encoding', default='ibm037',
                               dest='character_encoding', type=_get_character_encoding)

    if IS_VT100_AVAILABLE:
        vt100_parser = subparsers.add_parser('vt100', description='VT100 emulator',
                                             help='VT100 emulator')

        vt100_parser.add_argument('command', help='Host process')
        vt100_parser.add_argument('command_args', nargs=argparse.REMAINDER,
                                  help='Host process arguments')

    args = parser.parse_args()

    create_device = lambda interface, device_address, poll_response: _create_device(args, interface, device_address, poll_response)
    create_session = lambda device: _create_session(args, device)

    logger.info('Starting controller...')

    with open_serial_interface(args.serial_port) as interface:
        CONTROLLER = Controller(InterfaceWrapper(interface), create_device, create_session)

        CONTROLLER.run()

if __name__ == '__main__':
    main()
