"""
oec.controller
~~~~~~~~~~~~~~
"""

from enum import Enum
import time
import logging
import selectors
from concurrent import futures
from itertools import groupby
from coax import InterfaceFeature, Poll, PollAck, KeystrokePollResponse, \
                 ReceiveTimeout, ReceiveError, ProtocolError
from coax.multiplexer import PORT_MAP_3299

from .device import address_commands, format_address, UnsupportedDeviceError
from .keyboard import Key
from .session import SessionDisconnectedError

class Timer:
    def __init__(self, measurements):
        self.measurements = measurements

    def __enter__(self):
        self.start_time = time.perf_counter()

    def __exit__(self, type, value, traceback):
        duration = time.perf_counter() - self.start_time

        self.measurements.append(duration)

PERF_LOGS = open('timing.csv', 'w')
PERF_LOGS.write('update_sessions,delay,poll_attached,poll_detatched\n')

def dump_stats(a, b, c, d):
    if len(a) < 100:
        return

    for (l, m, n, o) in zip(a, b, c, d):
        PERF_LOGS.write(f'{l},{m},{n},{o}\n')

    PERF_LOGS.flush()

    a.clear()
    b.clear()
    c.clear()
    d.clear()

class SessionState(Enum):
    """Session state."""

    STARTING = 1
    ACTIVE = 2
    TERMINATING = 3

class Controller:
    """The controller."""

    def __init__(self, interface, create_device, create_session):
        self.logger = logging.getLogger(__name__)

        self.interface = interface
        self.running = False

        self.create_device = create_device
        self.create_session = create_session

        self.devices = { }
        self.detatched_device_poll_queue = []

        self.sessions = { }
        self.session_selector = None
        self.session_executor = None

        # Target time between POLL commands in seconds when a device is attached or
        # no device is attached.
        self.attached_poll_period = 1 / 15
        self.detatched_poll_period = 1 / 2

        # Maximum number of POLL commands to execute, per attached device, per run
        # loop iteration. If all attached devices respond with TT/AR the run loop
        # iteration will exit without reaching this maximum depth.
        #
        # This is an effort to improve the keystroke responsiveness.
        self.poll_depth = 3

        self.last_attached_poll_time = None
        self.last_detatched_poll_time = None

        self.a = []
        self.b = []
        self.c = []
        self.d = []

    def run(self):
        """Run the controller."""
        self.running = True

        self.session_selector = selectors.DefaultSelector()
        self.session_executor = futures.ThreadPoolExecutor()

        self.logger.info('Controller started')

        while self.running:
            self._run_loop()

        self.session_executor.shutdown(wait=True)

        self.session_executor = None

        for session in [session for (state, session) in self.sessions.values() if state == SessionState.ACTIVE]:
            self._terminate_session(session, blocking=True)

        self.session_selector.close()

        self.session_selector = None

        self.sessions.clear()

        self.devices.clear()
        self.detatched_device_poll_queue.clear()

        self.logger.info('Controller stopped')

    def stop(self):
        """Stop the controller."""
        self.running = False

    def _run_loop(self):
        poll_delay = self._calculate_poll_delay()

        # If POLLing is delayed, handle the host output, otherwise just sleep.
        start_time = time.perf_counter()

        with Timer(self.a):
            if poll_delay > 0:
                self._update_sessions(poll_delay)

        poll_delay -= (time.perf_counter() - start_time)

        if poll_delay > 0:
            self.b.append(poll_delay)
            time.sleep(poll_delay)
        else:
            self.b.append(0)

        # POLL devices.
        with Timer(self.c):
            self._poll_attached_devices()

        with Timer(self.d):
            self._poll_next_detatched_device()

        dump_stats(self.a, self.b, self.c, self.d)

    def _update_sessions(self, duration):
        start_time = time.perf_counter()

        # Start any missing sessions.
        for device_address in self.devices.keys() - self.sessions.keys():
            self._start_session(self.devices[device_address])

        sessions = { state: [(device_address, session) for (device_address, (_, session)) in group] for (state, group) in groupby(self.sessions.items(), lambda item: item[1][0]) }

        # Handle started sessions.
        started_sessions = []

        for (device_address, future) in sessions.get(SessionState.STARTING, []):
            if future.done():
                session = future.result()

                self.sessions[device_address] = (SessionState.ACTIVE, session)

                self.session_selector.register(session, selectors.EVENT_READ)

                started_sessions.append(session)

                self.logger.info(f'Session started for device @ {format_address(self.interface, device_address)}')

        # Handle terminated sessions.
        for (device_address, future) in sessions.get(SessionState.TERMINATING, []):
            if future.done():
                del self.sessions[device_address]

                self.logger.info(f'Session terminated for device @ {format_address(self.interface, device_address)}')

        # Update the duration based on the time taken handling futures.
        duration -= (time.perf_counter() - start_time)

        # Update active sessions.
        updated_sessions = set()

        is_first_iteration = True

        while duration > 0:
            start_time = time.perf_counter()

            sessions = set(self._select_sessions(duration))

            # Handle host output from started sessions immediately as the telnet client
            # buffer may contain commands that were buffered during negotiation. If we do
            # not handle them here, we will have to wait for further commands to trigger
            # the read select event.
            #
            # This ensures that messages such as "connection rejected, no available device"
            # are shown on the terminal.
            if is_first_iteration:
                sessions.update(started_sessions)

            if not sessions:
                break

            for session in sessions:
                try:
                    if session.handle_host():
                        updated_sessions.add(session)
                except SessionDisconnectedError:
                    updated_sessions.discard(session)

                    self._handle_session_disconnected(session)

            duration -= (time.perf_counter() - start_time)
            is_first_iteration = False

        for session in updated_sessions:
            session.render()

    def _select_sessions(self, duration):
        # The Windows selector will raise an error if there are no handles registered while
        # other selectors may block for the provided duration.
        if not self.session_selector.get_map():
            return []

        selected = self.session_selector.select(duration)

        return [key.fileobj for (key, _) in selected]

    def _start_session(self, device):
        device_address = device.device_address

        self.logger.info(f'Starting session for device @ {format_address(self.interface, device_address)}')

        def start_session():
            session = self.create_session(device)

            session.start()

            return session

        future = self.session_executor.submit(start_session)

        self.sessions[device_address] = (SessionState.STARTING, future)

    def _terminate_session(self, session, blocking=False):
        device_address = session.terminal.device_address

        self.logger.info(f'Terminating session for device @ {format_address(self.interface, device_address)}')

        self.session_selector.unregister(session)

        def terminate_session():
            session.terminate()

        if blocking:
            terminate_session()

            del self.sessions[device_address]
        else:
            future = self.session_executor.submit(terminate_session)

            self.sessions[device_address] = (SessionState.TERMINATING, future)

    def _handle_session_disconnected(self, session):
        self.logger.info('Session disconnected')

        self._terminate_session(session)

    def _poll_attached_devices(self):
        self.last_attached_poll_time = time.perf_counter()

        for _ in range(self.poll_depth):
            devices = self.devices.values()

            if not devices:
                break

            poll_commands = [address_commands(device.device_address, Poll(device.get_poll_action())) for device in devices]

            poll_responses = list(zip(devices, self.interface.execute(poll_commands, receive_timeout_is_error=False)))

            # Handle POLL responses.
            handleable_poll_responses = [pair for pair in poll_responses if pair[1] is not None and not isinstance(pair[1], ReceiveTimeout)]

            if handleable_poll_responses:
                poll_ack_commands = [address_commands(device.device_address, PollAck()) for (device, _) in handleable_poll_responses]

                self.interface.execute(poll_ack_commands)

                for (device, poll_response) in handleable_poll_responses:
                    self._handle_poll_response(device, poll_response)

            # Handle lost devices.
            for (device, poll_response) in poll_responses:
                if isinstance(poll_response, ReceiveTimeout):
                    self._handle_device_lost(device)

            if not handleable_poll_responses:
                break

    def _poll_next_detatched_device(self):
        if self.last_detatched_poll_time is not None and (time.perf_counter() - self.last_detatched_poll_time) < self.detatched_poll_period:
            return

        self.last_detatched_poll_time = time.perf_counter()

        if not self.detatched_device_poll_queue:
            self.detatched_device_poll_queue = list(self._get_detatched_device_addresses())

        try:
            device_address = self.detatched_device_poll_queue.pop(0)
        except IndexError:
            return

        try:
            poll_response = self.interface.execute(address_commands(device_address, Poll()))
        except ReceiveTimeout:
            return
        except ReceiveError as error:
            self.logger.warning(f'POLL detatched device @ {format_address(self.interface, device_address)} receive error: {error}')
            return
        except ProtocolError as error:
            self.logger.warning(f'POLL detatched device @ {format_address(self.interface, device_address)} protocol error: {error}')
            return

        if poll_response:
            self.interface.execute(address_commands(device_address, PollAck()))

        self._handle_device_found(device_address, poll_response)

    def _handle_device_found(self, device_address, poll_response):
        self.logger.info(f'Found device @ {format_address(self.interface, device_address)}')

        try:
            device = self.create_device(self.interface, device_address, poll_response)
        except UnsupportedDeviceError as error:
            self.logger.error(f'Unsupported device @ {format_address(self.interface, device_address)}: {error}')
            return

        device.setup()

        self.devices[device_address] = device

        self.logger.info(f'Attached device @ {format_address(self.interface, device_address)}')

    def _handle_device_lost(self, device):
        device_address = device.device_address

        self.logger.info(f'Lost device @ {format_address(self.interface, device_address)}')

        if device_address in self.sessions:
            (session_state, session) = self.sessions[device_address]

            if session_state == SessionState.ACTIVE:
                self._terminate_session(session)

        del self.devices[device_address]

        self.logger.info(f'Detached device @ {format_address(self.interface, device_address)}')

    def _handle_poll_response(self, device, poll_response):
        if isinstance(poll_response, KeystrokePollResponse):
            self._handle_keystroke_poll_response(device, poll_response)

    def _handle_keystroke_poll_response(self, terminal, poll_response):
        device_address = terminal.device_address
        scan_code = poll_response.scan_code

        (key, modifiers, modifiers_changed) = terminal.keyboard.get_key(scan_code)

        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug((f'Keystroke detected: Scan Code = {scan_code}, '
                               f'Key = {key}, Modifiers = {modifiers}'))

        # Update the status line if modifiers have changed.
        if modifiers_changed:
            terminal.display.status_line.write_keyboard_modifiers(modifiers)

        if not key:
            return

        if key == Key.CURSOR_BLINK:
            terminal.display.toggle_cursor_blink()
        elif key == Key.ALT_CURSOR:
            terminal.display.toggle_cursor_reverse()
        elif key == Key.CLICKER:
            terminal.keyboard.toggle_clicker()
        elif device_address in self.sessions:
            (session_state, session) = self.sessions[device_address]

            if session_state == SessionState.ACTIVE:
                session.handle_key(key, modifiers, scan_code)

                session.render()

    def _calculate_poll_delay(self):
        if self.last_attached_poll_time is None:
            return 0

        return max((self.last_attached_poll_time + self.attached_poll_period) - time.perf_counter(), 0)

    def _get_detatched_device_addresses(self):
        attached_addresses = set(self.devices.keys())

        # The 3299 is transparent, but if there is at least one device attached to a 3299
        # port then we can assume there is a 3299 attached and if there is one device
        # direct attached then we can assume there is not a 3299 attached.
        is_3299_attached = any(attached_addresses.difference([None]))
        is_3299_not_attached = (None in attached_addresses)

        if is_3299_not_attached or InterfaceFeature.PROTOCOL_3299 not in self.interface.features:
            addresses = [None]
        elif is_3299_attached:
            addresses = PORT_MAP_3299
        else:
            addresses = [None, *PORT_MAP_3299]

        return filter(lambda address: address not in attached_addresses, addresses)
