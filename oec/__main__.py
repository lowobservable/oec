import sys
import os
import signal
import logging
import time
import select
from coax import open_serial_interface, TerminalType, Feature
from coax.exceptions import InterfaceTimeout

from .args import parse_args
from .interface import InterfaceWrapper
from .controller import Controller
from .device import get_ids, get_features, UnsupportedDeviceError
from .terminal import Terminal, get_model, get_keyboard_description
from .tn3270 import TN3270Session

# VT100 emulation is not supported on Windows.
IS_VT100_AVAILABLE = False

if os.name == 'posix':
    from .vt100 import VT100Session

    IS_VT100_AVAILABLE = True

from .keymap_3278_typewriter import KEYMAP as KEYMAP_3278_TYPEWRITER
from .keymap_3278_typewriter_de import KEYMAP as KEYMAP_3278_TYPEWRITER_DE
from .keymap_ibm_typewriter import KEYMAP as KEYMAP_IBM_TYPEWRITER
from .keymap_ibm_enhanced import KEYMAP as KEYMAP_IBM_ENHANCED

_LOG_LEVELS = {
    'debug': logging.DEBUG,
    'info': logging.INFO,
    'warning': logging.WARNING,
    'error': logging.ERROR,
}

logger = logging.getLogger('oec.main')

# How long to wait for an answer from the interface. A transaction carries its
# own timeout and the interface answers it either way, so a read that takes
# longer than this is the interface having stopped talking altogether.
SERIAL_READ_TIMEOUT = 5

KEYMAP_3278_LANGUAGE = {
    'us': KEYMAP_3278_TYPEWRITER,
    'de': KEYMAP_3278_TYPEWRITER_DE
}

def _get_keymap(args, keyboard_description):
    if keyboard_description.startswith('3278'):
        return KEYMAP_3278_LANGUAGE.get(args.keyboard_language, KEYMAP_3278_TYPEWRITER)

    if keyboard_description.startswith('IBM-TYPEWRITER'):
        return KEYMAP_IBM_TYPEWRITER

    if keyboard_description.startswith('IBM-ENHANCED'):
        return KEYMAP_IBM_ENHANCED

    return KEYMAP_3278_TYPEWRITER

def _create_device(args, interface, device_address, _poll_response):
    (terminal_id, extended_id) = get_ids(interface, device_address)

    logger.info(f'Terminal ID = {terminal_id}, Extended ID = {extended_id}')

    if terminal_id.type != TerminalType.CUT:
        raise UnsupportedDeviceError('Only CUT type terminals are supported')

    model = get_model(terminal_id, extended_id)

    if model is not None:
        logger.info(f'Model = IBM {model} or equivalent')

    features = get_features(interface, device_address)

    # The 3179 includes an EAB but does not respond to the READ_FEATURE_ID
    # command.
    if model == '3179':
        features[Feature.EAB] = 7

    logger.info(f'Features = {features}')

    keyboard_description = get_keyboard_description(terminal_id, extended_id)

    logger.info(f'Keyboard = {keyboard_description}')

    keymap = _get_keymap(args, keyboard_description)

    logger.info(f'Keymap = {keymap.name}')

    terminal = Terminal(interface, device_address, terminal_id, extended_id, features, keymap)

    if args.clicker:
        terminal.keyboard.clicker = True

    return terminal

def _create_session(args, device):
    if args.emulator == 'tn3270':
        return TN3270Session(device, args.host, args.port, args.device_names, args.character_encoding, args.tn3270e_profile, args.ssl, args.no_starttls, args.ssl_no_verify, args.no_hostname_status)

    if args.emulator == 'vt100' and IS_VT100_AVAILABLE:
        host_command = [args.command, *args.command_args]

        # pylint: disable-next=possibly-used-before-assignment
        return VT100Session(device, host_command)

    raise ValueError('Unsupported emulator')

def _read_through_the_descriptor(serial_port):
    """Read the port without an empty read costing bytes or ending the run.

    A USB serial device ends a transfer that fills its last packet with a zero
    length one, so a port that has just reported data hands over none. pySerial
    takes that for a disconnected device and raises -- and the bytes it had
    already gathered for that read go with the exception, so what arrives
    afterwards is read as the middle of a message.

    Reading the port's own descriptor keeps every byte that arrives. Nothing
    to hand over yet, whether that shows as an empty read or as EAGAIN on the
    non-blocking descriptor pySerial opens, means only that: the read waits
    for more until the port's timeout, and a port that stays quiet returns
    what it has, which the interface library reports as the timeout it is.
    """
    fd = serial_port.fileno()

    def read(size=1):
        deadline = time.monotonic() + (serial_port.timeout or 0)
        data = bytearray()

        while len(data) < size:
            remaining = deadline - time.monotonic()

            if remaining <= 0:
                break

            (ready, _, _) = select.select([fd], [], [], remaining)

            if not ready:
                break

            try:
                chunk = os.read(fd, size - len(data))
            except (BlockingIOError, InterruptedError):
                chunk = b''

            if chunk:
                data.extend(chunk)
            else:
                # Readable with nothing behind it: let the port get on with
                # it rather than asking again as fast as the loop can run.
                time.sleep(0.001)

        if not data:
            # Handing back nothing is read as the end of the stream: the SLIP
            # decoder flushes what it holds and gives it up as a message, so
            # an answer still arriving comes out truncated and one that has
            # not started comes out empty. A port with nothing to give has
            # timed out, which is what the caller is told.
            raise InterfaceTimeout()

        return bytes(data)

    serial_port.read = read

def main():
    args = parse_args(sys.argv[1:], IS_VT100_AVAILABLE)

    logging.basicConfig(level=_LOG_LEVELS[args.log_level])

    def create_device(interface, device_address, poll_response):
        return _create_device(args, interface, device_address, poll_response)

    def create_session(device):
        return _create_session(args, device)

    logger.info('Starting controller...')

    with open_serial_interface(args.serial_port) as interface:
        # An interface that stops answering must not take the controller with
        # it. pySerial waits for ever on a port opened without a timeout, so
        # the read of a response that never comes never returns, and the
        # interface's own InterfaceTimeout -- which ends the run and lets
        # whatever supervises it start a fresh one -- is never raised.
        interface.serial.timeout = SERIAL_READ_TIMEOUT
        _read_through_the_descriptor(interface.serial)

        controller = Controller(InterfaceWrapper(interface), create_device, create_session)

        def signal_handler(_number, _frame):
            logger.info('Stopping controller...')

            controller.stop()

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        controller.run()

if __name__ == '__main__':
    main()
