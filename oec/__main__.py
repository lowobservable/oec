import os
import time
import signal
import logging
import argparse
from contextlib import contextmanager
from serial import Serial
from coax import SerialInterface

from .controller import Controller
from .tn3270 import TN3270Session

# VT100 emulation is not supported on Windows.
is_vt100_available = False

if os.name == 'posix':
    from .vt100 import VT100Session

    is_vt100_available = True

from .keymap_3278_2 import KEYMAP as KEYMAP_3278_2
from .keymap_3483 import KEYMAP as KEYMAP_3483

logging.basicConfig(level=logging.INFO)

controller = None

def _get_keymap(terminal_id, extended_id):
    keymap = KEYMAP_3278_2

    if extended_id == 'c1348300':
        keymap = KEYMAP_3483

    if extended_id == 'c1347200':
        keymap = KEYMAP_3483

    return keymap

@contextmanager
def _create_interface(args):
    with Serial(args.serial_port, 115200) as serial:
        serial.reset_input_buffer()
        serial.reset_output_buffer()

        # Allow the interface firmware time to start, this is only required for the
        # original Arduino Mega based interface.
        if 'COAX_FAST_START' not in os.environ:
            time.sleep(3)

        interface = SerialInterface(serial)

        interface.reset()

        yield interface

def _create_session(args, terminal):
    if args.emulator == 'tn3270':
        return TN3270Session(terminal, args.host, args.port)

    if args.emulator == 'vt100' and is_vt100_available:
        host_command = [args.command, *args.command_args]

        return VT100Session(terminal, host_command)

    raise ValueError('Unsupported emulator')

def _signal_handler(number, frame):
    global controller

    print('Stopping controller...')

    if controller:
        controller.stop()

        controller = None

signal.signal(signal.SIGINT, _signal_handler)
signal.signal(signal.SIGTERM, _signal_handler)

def main():
    global controller

    parser = argparse.ArgumentParser(description=('An open replacement for the IBM 3174 '
                                                  'Establishment Controller'))

    parser.add_argument('serial_port', help='Serial port')

    subparsers = parser.add_subparsers(dest='emulator', required=True,
                                       description='Emulator')

    tn3270_parser = subparsers.add_parser('tn3270', description='TN3270 emulator',
                                          help='TN3270 emulator')

    tn3270_parser.add_argument('host', help='Hostname')
    tn3270_parser.add_argument('port', nargs='?', default=23, type=int)

    if is_vt100_available:
        vt100_parser = subparsers.add_parser('vt100', description='VT100 emulator',
                                             help='VT100 emulator')

        vt100_parser.add_argument('command', help='Host process')
        vt100_parser.add_argument('command_args', nargs=argparse.REMAINDER,
                                  help='Host process arguments')

    args = parser.parse_args()

    with _create_interface(args) as interface:
        create_session = lambda terminal: _create_session(args, terminal)

        controller = Controller(interface, _get_keymap, create_session)

        print('Starting controller...')

        controller.run()

if __name__ == '__main__':
    main()
