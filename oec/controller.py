"""
oec.controller
~~~~~~~~~~~~~~
"""

import time
import logging
import selectors
from coax import Poll, PollAck, KeystrokePollResponse, ReceiveTimeout, \
                 ReceiveError, ProtocolError

from .interface import address_commands
from .terminal import create_terminal, UnsupportedTerminalError
from .keyboard import Key
from .session import SessionDisconnectedError

class Controller:
    """The controller."""

    def __init__(self, interface, get_keymap, create_session):
        self.logger = logging.getLogger(__name__)

        self.running = False

        self.interface = interface
        self.get_keymap = get_keymap
        self.create_session = create_session

        self.terminal = None
        self.session = None

        self.session_selector = None

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

        self.session_selector = selectors.DefaultSelector()

        while self.running:
            self._run_loop()

        self._terminate_session()

        self.session_selector.close()

        self.session_selector = None

        if self.terminal:
            self.terminal = None

    def stop(self):
        self.running = False

    def _run_loop(self):
        device_address = None

        poll_delay = self._calculate_poll_delay(time.perf_counter())

        # If POLLing is delayed, handle the host output, otherwise just sleep.
        if poll_delay > 0:
            if self.session:
                try:
                    self._update_session(poll_delay)
                except SessionDisconnectedError:
                    self._handle_session_disconnected()
            else:
                time.sleep(poll_delay)

        try:
            poll_response = self._poll(device_address)
        except ReceiveTimeout:
            if self.terminal:
                self._handle_terminal_detached()

            return
        except ReceiveError as error:
            self.logger.warning(f'POLL receive error: {error}', exc_info=error)
            return
        except ProtocolError as error:
            self.logger.warning(f'POLL protocol error: {error}', exc_info=error)
            return

        if not self.terminal:
            try:
                self._handle_terminal_attached(device_address, poll_response)
            except UnsupportedTerminalError as error:
                self.logger.error(f'Unsupported terminal: {error}')
                return

        if poll_response:
            self._handle_poll_response(poll_response)

    def _handle_terminal_attached(self, device_address, poll_response):
        self.logger.info('Terminal attached')

        self.terminal = create_terminal(self.interface, device_address, poll_response,
                                        self.get_keymap)

        self.terminal.setup()

        # Show the attached indicator on the status line.
        self.terminal.display.status_line.write_string(0, 'S')

        # Start the session.
        self._start_session()

    def _handle_terminal_detached(self):
        self.logger.info('Terminal detached')

        self._terminate_session()

        self.terminal = None

    def _handle_session_disconnected(self):
        self.logger.info('Session disconnected')

        self._terminate_session()

        # Restart the session.
        self._start_session()

    def _start_session(self):
        self.session = self.create_session(self.terminal)

        self.session.start()

        self.session_selector.register(self.session, selectors.EVENT_READ)

    def _terminate_session(self):
        if not self.session:
            return

        self.session_selector.unregister(self.session)

        self.session.terminate()

        self.session = None

    def _update_session(self, duration):
        update_count = 0

        while duration > 0:
            start_time = time.perf_counter()

            selected = self.session_selector.select(duration)

            if not selected:
                break

            for (key, events) in selected:
                session = key.fileobj

                if session.handle_host():
                    update_count += 1

            duration -= (time.perf_counter() - start_time)

        if update_count > 0:
            self.session.render()

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

        if key == Key.CURSOR_BLINK:
            self.terminal.display.toggle_cursor_blink()
        elif key == Key.ALT_CURSOR:
            self.terminal.display.toggle_cursor_reverse()
        elif key == Key.CLICKER:
            self.terminal.keyboard.toggle_clicker()
        elif self.session:
            self.session.handle_key(key, modifiers, scan_code)

            self.session.render()

    def _poll(self, device_address):
        self.last_poll_time = time.perf_counter()

        # If a terminal is connected, use the terminal method to ensure that
        # any queued POLL action is applied.
        if self.terminal:
            poll_response = self.terminal.poll()
        else:
            poll_response = self.interface.execute(address_commands(device_address, Poll()))

        if poll_response:
            try:
                self.interface.execute(address_commands(device_address, PollAck()))
            except ProtocolError as error:
                self.logger.warning(f'POLL_ACK protocol error: {error}', exc_info=error)

        self.last_poll_response = poll_response

        return poll_response

    def _calculate_poll_delay(self, current_time):
        if self.last_poll_response is not None:
            return 0

        if self.last_poll_time is None:
            return 0

        if self.terminal:
            period = self.connected_poll_period
        else:
            period = self.disconnected_poll_period

        return max((self.last_poll_time + period) - current_time, 0)
