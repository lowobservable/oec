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

        self.running = False

        self.interface = interface
        self.create_session = create_session

        self.terminal = None
        self.session = None

        # Target time between POLL commands in seconds when a terminal is connected or
        # no terminal is connected.
        #
        # The connected poll period only applies in cases where the terminal responded
        # with TR/TA to the last poll - this is an effort to improve the keystroke
        # responsiveness.
        self.connected_poll_period = 1 / 10
        self.disconnected_poll_period = 5

        self.last_poll_time = None
        self.last_poll_response = None

    def run(self):
        """Run the controller."""
        self.running = True

        while self.running:
            if self.session:
                try:
                    self.session.handle_host()
                except SessionDisconnectedError:
                    self._handle_session_disconnected()

            try:
                poll_response = self._poll()
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

            if not self.terminal:
                self._handle_terminal_attached(poll_response)

            if poll_response:
                self._handle_poll_response(poll_response)

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

        self.terminal.display.clear(clear_status_line=True)

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
            self.terminal.display.status_line.write_keyboard_modifiers(modifiers)

        if not key:
            return

        if self.session:
            self.session.handle_key(key, modifiers, scan_code)

    def _poll(self):
        delay = self._calculate_poll_delay()

        if delay > 0:
            time.sleep(delay)

        self.last_poll_time = time.perf_counter()

        poll_response = poll(self.interface, timeout=1)

        if poll_response:
            try:
                poll_ack(self.interface)
            except ReceiveError as error:
                self.logger.warning(f'POLL_ACK receive error: {error}', exc_info=error)
            except ProtocolError as error:
                self.logger.warning(f'POLL_ACK protocol error: {error}', exc_info=error)

        self.last_poll_response = poll_response

        return poll_response

    def _calculate_poll_delay(self):
        if self.last_poll_response is not None:
            return 0

        if self.last_poll_time is None:
            return 0

        if self.terminal:
            period = self.connected_poll_period
        else:
            period = self.disconnected_poll_period

        return (self.last_poll_time + period) - time.perf_counter()
