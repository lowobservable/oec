"""
oec.controller
~~~~~~~~~~~~~~
"""

import time
import logging
from coax import poll, poll_ack, KeystrokePollResponse, ReceiveTimeout, \
                 ReceiveError, ProtocolError

from .terminal import Terminal, read_terminal_ids
from .session import SessionDisconnectedError

class Controller:
    """The controller."""

    def __init__(self, interface, create_session):
        self.logger = logging.getLogger(__name__)

        self.running = True

        self.interface = interface
        self.create_session = create_session

        self.terminal = None
        self.session = None

    def run(self):
        """Run the controller."""
        while self.running:
            if self.session:
                try:
                    self.session.handle_host()
                except SessionDisconnectedError:
                    self._handle_session_disconnected()

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
        (terminal_id, extended_id) = read_terminal_ids(self.interface)

        self.logger.info(f'Terminal ID = {terminal_id}, Extended ID = {extended_id}')

        # Initialize the terminal.
        self.terminal = Terminal(self.interface, terminal_id, extended_id)

        (rows, columns) = self.terminal.display.dimensions
        keymap_name = self.terminal.keyboard.keymap.name

        self.logger.info(f'Rows = {rows}, Columns = {columns}, Keymap = {keymap_name}')

        self.terminal.display.clear_screen()

        # Show the attached indicator on the status line.
        self.terminal.display.status_line.write_string(0, 'S')

        # Start the session.
        self._start_session()

    def _handle_terminal_detached(self):
        self.logger.info('Terminal detached')

        if self.session:
            self.session.terminate()

            self.session = None

        self.terminal = None

    def _handle_session_disconnected(self):
        self.logger.info('Session disconnected')

        self.session = None

        # Restart the session.
        self._start_session()

    def _start_session(self):
        self.session = self.create_session(self.terminal)

        self.session.start()

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

            self.terminal.display.status_line.write(35, indicators)

        if not key:
            return

        if self.session:
            self.session.handle_key(key, modifiers, scan_code)
