import unittest
from unittest.mock import Mock, create_autospec, patch, call, ANY

import selectors
from selectors import BaseSelector
from concurrent.futures import Future
from coax import Poll, PollAck, PowerOnResetCompletePollResponse, KeystrokePollResponse, ReceiveTimeout

import context

from oec.interface import InterfaceWrapper
from oec.controller import Controller, SessionState
from oec.terminal import Terminal
from oec.session import Session, SessionDisconnectedError

from mock_interface import MockInterface

class UpdateSessionsTestCase(unittest.TestCase):
    def setUp(self):
        self.interface = MockInterface()

        self.controller = Controller(InterfaceWrapper(self.interface), None, None)

        self.controller.session_selector = create_autospec(BaseSelector, instance=True)

        patcher = patch('oec.controller.time.perf_counter')

        self.perf_counter = patcher.start()

        self.addCleanup(patch.stopall)

    def test_no_sessions(self):
        # Arrange

        self.perf_counter.side_effect = [0, 0.1, 0.2]

        self.controller.session_selector.select.return_value = []

        # Act
        self.assertFalse(self.controller._update_sessions(1.0))

    def test_missing_sessions_are_started(self):
        # Arrange
        device = create_autospec(Terminal, instance=True)

        self.controller.devices[None] = device

        self.controller._start_session = Mock()

        self.perf_counter.side_effect = [0, 0.1, 0.2]

        self.controller.session_selector.select.return_value = []

        # Act
        self.controller._update_sessions(1.0)

        # Assert
        self.controller._start_session.assert_called_once_with(device)

    def test_started_sessions_are_activated(self):
        # Arrange
        device = create_autospec(Terminal, instance=True)

        session = create_autospec(Session, instance=True)

        future = create_autospec(Future, instance=True)

        future.done = Mock(return_value=True)
        future.result = Mock(return_value=session)

        self.controller.devices[None] = device
        self.controller.sessions[None] = (SessionState.STARTING, future)

        self.controller.session_selector.select.return_value = []

        self.perf_counter.side_effect = [0, 0.1, 0.2]

        # Act
        self.controller._update_sessions(1.0)

        # Assert
        self.assertEqual(self.controller.sessions, { None: (SessionState.ACTIVE, session) })

        self.controller.session_selector.register.assert_called_once_with(session, selectors.EVENT_READ)

    def test_terminated_sessions_are_removed(self):
        # Arrange
        device = create_autospec(Terminal, instance=True)

        future = create_autospec(Future, instance=True)

        future.done = Mock(return_value=True)
        future.result = Mock()

        self.controller.devices[None] = device
        self.controller.sessions[None] = (SessionState.TERMINATING, future)

        self.controller.session_selector.select.return_value = []

        self.perf_counter.side_effect = [0, 0.1, 0.2]

        # Act
        self.controller._update_sessions(1.0)

        # Assert
        self.assertEqual(self.controller.sessions, { })

    def test_active_sessions_select_timeout(self):
        # Arrange
        device = create_autospec(Terminal, instance=True)

        session = create_autospec(Session, instance=True)

        self.controller.devices[None] = device
        self.controller.sessions[None] = (SessionState.ACTIVE, session)

        self.controller.session_selector.select.return_value = []

        self.perf_counter.side_effect = [0, 0.1, 0.2]

        # Act
        self.controller._update_sessions(1.0)

        # Assert
        self.controller.session_selector.select.assert_called_once_with(0.9)

        session.handle_host.assert_not_called()
        session.render.assert_not_called()

    def test_active_sessions_select_available(self):
        # Arrange
        device = create_autospec(Terminal, instance=True)

        session = create_autospec(Session, instance=True)

        self.controller.devices[None] = device
        self.controller.sessions[None] = (SessionState.ACTIVE, session)

        selector_key = Mock(fileobj=session)

        self.controller.session_selector.select.side_effect = [[(selector_key, selectors.EVENT_READ)], []]

        self.perf_counter.side_effect = [0, 0.1, 0.2, 0.3, 0.4, 0.4]

        # Act
        self.controller._update_sessions(1.0)

        # Assert
        self.controller.session_selector.select.assert_has_calls([call(0.9), call(0.8)])

        session.handle_host.assert_called_once()
        session.render.assert_called_once()

    def test_active_sessions_disconnected(self):
        # Arrange
        device = create_autospec(Terminal, instance=True)

        session = create_autospec(Session, instance=True)

        session.handle_host.side_effect = SessionDisconnectedError

        self.controller.devices[None] = device
        self.controller.sessions[None] = (SessionState.ACTIVE, session)

        self.controller._terminate_session = Mock()

        selector_key = Mock(fileobj=session)

        self.controller.session_selector.select.side_effect = [[(selector_key, selectors.EVENT_READ)], []]

        self.perf_counter.side_effect = [0, 0.1, 0.2, 0.3, 0.4, 0.4]

        # Act
        self.controller._update_sessions(1.0)

        # Assert
        self.controller.session_selector.select.assert_has_calls([call(0.9), call(0.8)])

        self.controller._terminate_session.assert_called_once_with(session)

        session.render.assert_not_called()

class PollAttachedDevicesTestCase(unittest.TestCase):
    def setUp(self):
        self.interface = MockInterface()

        self.controller = Controller(InterfaceWrapper(self.interface), None, None)

        self.controller._handle_poll_response = Mock(wraps=self.controller._handle_poll_response)

    def test_no_attached_devices(self):
        self.controller._poll_attached_devices()

        # Assert
        self.interface.assert_command_not_executed(ANY, Poll)
        self.controller._handle_poll_response.assert_not_called()

    def test_tt_ar(self):
        # Arrange
        device = create_autospec(Terminal, instance=True, device_address=None)

        self.controller.devices[None] = device

        # Act
        self.controller._poll_attached_devices()

        # Assert
        self.interface.assert_command_executed(None, Poll)
        self.interface.assert_command_not_executed(None, PollAck)
        self.controller._handle_poll_response.assert_not_called()

    def test_receive_timeout(self):
        # Arrange
        self.interface.mock_responses = [(None, Poll, None, ReceiveTimeout)]

        device = create_autospec(Terminal, instance=True, device_address=None)

        self.controller.devices[None] = device

        self.controller._handle_device_lost = Mock()

        # Act
        self.controller._poll_attached_devices()

        # Assert
        self.controller._handle_device_lost.assert_called_once_with(device)

        self.interface.assert_command_executed(None, Poll)
        self.interface.assert_command_not_executed(None, PollAck)
        self.controller._handle_poll_response.assert_not_called()

    def test_keystroke(self):
        # Arrange
        poll_response = KeystrokePollResponse(0b0110000010)

        poll = Mock(side_effect=[poll_response, None, None])

        self.interface.mock_responses = [(None, Poll, None, poll)]

        device = create_autospec(Terminal, instance=True, device_address=None)

        self.controller.devices[None] = device

        self.controller._handle_keystroke_poll_response = Mock()

        # Act
        self.controller._poll_attached_devices()

        # Assert
        self.controller._handle_keystroke_poll_response.assert_called_once_with(device, poll_response)

        self.assertEqual(poll.call_count, 2)
        self.interface.assert_command_executed(None, PollAck)

class PollNextDetatchedDeviceTestCase(unittest.TestCase):
    def setUp(self):
        self.interface = MockInterface()

        self.interface.mock_responses = [(None, Poll, None, ReceiveTimeout)]

        self.controller = Controller(InterfaceWrapper(self.interface), None, None)

        patcher = patch('oec.controller.time.perf_counter')

        self.perf_counter = patcher.start()

        self.addCleanup(patch.stopall)

    def test_poll_period_not_expired(self):
        # Arrange
        self.controller.detatched_poll_period = 0.5
        self.controller.last_detatched_poll_time = 1.0

        self.perf_counter.return_value = 1.1

        # Act
        self.controller._poll_next_detatched_device()

        # Assert
        self.interface.assert_command_not_executed(None, Poll)

        self.assertEqual(self.controller.last_detatched_poll_time, 1.0)

    def test_empty_queue_that_remains_empty(self):
        # Arrange
        self.controller._get_detatched_device_addresses = Mock(return_value=[])

        # Act
        self.controller._poll_next_detatched_device()

        # Assert
        self.interface.assert_command_not_executed(None, Poll)

        self.controller._get_detatched_device_addresses.assert_called_once()

    def test_empty_queue_that_is_populated(self):
        # Arrange
        self.controller._get_detatched_device_addresses = Mock(return_value=[None])

        # Act
        self.controller._poll_next_detatched_device()

        # Assert
        self.interface.assert_command_executed(None, Poll)

        self.controller._get_detatched_device_addresses.assert_called_once()

    def test_non_empty_queue(self):
        # Arrange
        self.interface.mock_responses = [(0b000000, Poll, None, ReceiveTimeout)]

        self.controller.detatched_device_poll_queue = [0b000000, 0b100000]

        self.controller._get_detatched_device_addresses = Mock()

        # Act
        self.controller._poll_next_detatched_device()

        # Assert
        self.interface.assert_command_executed(0b000000, Poll)

        self.assertEqual(self.controller.detatched_device_poll_queue, [0b100000])

        self.controller._get_detatched_device_addresses.assert_not_called()

    def test_device_found(self):
        # Arrange
        self.controller.detatched_device_poll_queue = [None]

        poll_response = PowerOnResetCompletePollResponse(0xa)

        poll = Mock(side_effect=[poll_response, None, None])

        self.interface.mock_responses = [(None, Poll, None, poll)]

        self.controller._handle_device_found = Mock()

        # Act
        self.controller._poll_next_detatched_device()

        # Assert
        self.controller._handle_device_found.assert_called_once_with(None, poll_response)

        self.interface.assert_command_executed(None, PollAck)
