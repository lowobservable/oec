import time
import logging
import argparse
from serial import Serial
from coax import Interface1

from .controller import Controller

logging.basicConfig(level=logging.INFO)

def main():
    parser = argparse.ArgumentParser(description='VT100 emulator.')

    parser.add_argument('port', help='Serial port')
    parser.add_argument('command', help='Host process')
    parser.add_argument('command_args', nargs=argparse.REMAINDER, help='Host process arguments')

    args = parser.parse_args()

    with Serial(args.port, 115200) as serial:
        serial.reset_input_buffer()
        serial.reset_output_buffer()

        # Allow the interface firmware time to start.
        time.sleep(3)

        # Initialize the interface.
        interface = Interface1(serial)

        firmware_version = interface.reset()

        print(f'Interface firmware version {firmware_version}')

        # Initialize and start the controller.
        controller = Controller(interface, [args.command, *args.command_args])

        print('Starting controller...')

        controller.run()

if __name__ == '__main__':
    main()
