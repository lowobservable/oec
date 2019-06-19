"""
oec.controller
~~~~~~~~~~~~~~
"""

import time
import os
from select import select
import logging
from ptyprocess import PtyProcess
from coax import poll, poll_ack, read_terminal_id, read_extended_id, \
                 KeystrokePollResponse, ReceiveTimeout, ReceiveError, \
                 ProtocolError

from .terminal import Terminal
from .emulator import VT100Emulator

class Controller:
    """The controller."""

    def __init__(self, interface, host_command):
        self.logger = logging.getLogger(__name__)

        self.running = True

        self.interface = interface
        self.host_command = host_command

        self.terminal = None
        self.host_process = None
        self.emulator = None

    def run(self):
        """Run the controller."""
        while self.running:
            if self.host_process:
                try:
                    if self.host_process in select([self.host_process], [], [], 0)[0]:
                        data = self.host_process.read()

                        self._handle_host_process_output(data)
                except EOFError:
                    self._handle_host_process_terminated()

            try:
                poll_response = poll(self.interface, timeout=1)
            except ReceiveTimeout:
                if self.terminal:
                    self._handle_terminal_detached()

                continue
            except ReceiveError as error:
                self.logger.warning(f'POLL receive error: {error}', exc_info=error)
                continue
            except ProtocolError as error:
                self.logger.warning(f'POLL protocol error: {error}', exc_info=error)
                continue

            if poll_response:
                try:
                    poll_ack(self.interface)
                except ReceiveError as error:
                    self.logger.warning(f'POLL_ACK receive error: {error}', exc_info=error)
                except ProtocolError as error:
                    self.logger.warning(f'POLL_ACK protocol error: {error}', exc_info=error)

            if not self.terminal:
                self._handle_terminal_attached(poll_response)

            if poll_response:
                self._handle_poll_response(poll_response)
            else:
                time.sleep(0.1)

    def _handle_terminal_attached(self, poll_response):
        self.logger.info('Terminal attached')

        # Read the terminal identifiers.
        (terminal_id, extended_id) = self._read_terminal_ids()

        self.logger.info(f'Terminal ID = {terminal_id}, Extended ID = {extended_id}')

        # Initialize the terminal.
        self.terminal = Terminal(self.interface, terminal_id, extended_id)

        (rows, columns) = self.terminal.dimensions
        keymap_name = self.terminal.keyboard.keymap.name

        self.logger.info(f'Rows = {rows}, Columns = {columns}, Keymap = {keymap_name}')

        self.terminal.clear_screen()

        # Show the attached indicator on the status line.
        self.terminal.status_line.write_string(0, 'S')

        # Start the process.
        self.host_process = self._start_host_process()

        # Initialize the emulator.
        self.emulator = VT100Emulator(self.terminal, self.host_process)

    def _read_terminal_ids(self):
        terminal_id = None
        extended_id = None

        try:
            terminal_id = read_terminal_id(self.interface)
        except ReceiveError as error:
            self.logger.warning(f'READ_TERMINAL_ID receive error: {error}', exc_info=error)
        except ProtocolError as error:
            self.logger.warning(f'READ_TERMINAL_ID protocol error: {error}', exc_info=error)

        try:
            extended_id = read_extended_id(self.interface)
        except ReceiveError as error:
            self.logger.warning(f'READ_EXTENDED_ID receive error: {error}', exc_info=error)
        except ProtocolError as error:
            self.logger.warning(f'READ_EXTENDED_ID protocol error: {error}', exc_info=error)

        return (terminal_id, extended_id.hex() if extended_id is not None else None)

    def _handle_terminal_detached(self):
        self.logger.info('Terminal detached')

        if self.host_process:
            self.logger.debug('Terminating host process')

            if not self.host_process.terminate(force=True):
                self.logger.error('Unable to terminate host process')
            else:
                self.logger.debug('Host process terminated')

        self.terminal = None
        self.host_process = None
        self.emulator = None

    def _handle_poll_response(self, poll_response):
        if isinstance(poll_response, KeystrokePollResponse):
            self._handle_keystroke_poll_response(poll_response)

    def _handle_keystroke_poll_response(self, poll_response):
        scan_code = poll_response.scan_code

        (key, modifiers, modifiers_changed) = self.terminal.keyboard.get_key(scan_code)

        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug((f'Keystroke detected: Scan Code = {scan_code}, '
                               f'Key = {key}, Modifiers = {modifiers}'))

        # Update the status line if modifiers have changed.
        if modifiers_changed:
            indicators = bytearray(1)

            if modifiers.is_shift():
                indicators[0] = 0xda
            else:
                indicators[0] = 0x00

            self.terminal.status_line.write(35, indicators)

        if not key:
            return

        if self.emulator:
            self.emulator.handle_key(key, modifiers, scan_code)

    def _start_host_process(self):
        environment = os.environ.copy()

        environment['TERM'] = 'vt100'
        environment['LC_ALL'] = 'C'

        process = PtyProcess.spawn(self.host_command, env=environment,
                                   dimensions=self.terminal.dimensions)

        return process

    def _handle_host_process_output(self, data):
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(f'Output from host process: {data}')

        if self.emulator:
            self.emulator.handle_host_output(data)

    def _handle_host_process_terminated(self):
        self.logger.info('Host process terminated')

        if self.host_process.isalive():
            self.logger.error('Host process is reporting as alive')

        self.host_process = None
        self.emulator = None
