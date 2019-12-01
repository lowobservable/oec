import time
import logging
import argparse
from serial import Serial
from coax import Interface1

from .controller import Controller
from .tn3270 import TN3270Session
from .vt100 import VT100Session
from .keymap_3278_2 import KEYMAP as KEYMAP_3278_2
from .keymap_3483 import KEYMAP as KEYMAP_3483

logging.basicConfig(level=logging.INFO)

def _get_keymap(terminal_id, extended_id):
    keymap = KEYMAP_3278_2

    if extended_id == 'c1348300':
        keymap = KEYMAP_3483

    return keymap

def _create_session(args, terminal):
    if args.emulator == 'tn3270':
        return TN3270Session(terminal, args.host, args.port)

    if args.emulator == 'vt100':
        host_command = [args.command, *args.command_args]

        return VT100Session(terminal, host_command)

    raise ValueError('Unsupported emulator')

def main():
    parser = argparse.ArgumentParser(description=('An open replacement for the IBM 3174 '
                                                  'Establishment Controller'))

    parser.add_argument('serial_port', help='Serial port')

    subparsers = parser.add_subparsers(dest='emulator', required=True,
                                       description='Emulator')

    tn3270_parser = subparsers.add_parser('tn3270', description='TN3270 emulator',
                                          help='TN3270 emulator')

    tn3270_parser.add_argument('host', help='Hostname')
    tn3270_parser.add_argument('port', nargs='?', default=23, type=int)

    vt100_parser = subparsers.add_parser('vt100', description='VT100 emulator',
                                         help='VT100 emulator')

    vt100_parser.add_argument('command', help='Host process')
    vt100_parser.add_argument('command_args', nargs=argparse.REMAINDER,
                              help='Host process arguments')

    args = parser.parse_args()

    with Serial(args.serial_port, 115200) as serial:
        serial.reset_input_buffer()
        serial.reset_output_buffer()

        # Allow the interface firmware time to start.
        time.sleep(3)

        # Initialize the interface.
        interface = Interface1(serial)

        firmware_version = interface.reset()

        print(f'Interface firmware version {firmware_version}')

        # Initialize and start the controller.
        create_session = lambda terminal: _create_session(args, terminal)

        controller = Controller(interface, _get_keymap, create_session)

        print('Starting controller...')

        controller.run()

if __name__ == '__main__':
    main()
