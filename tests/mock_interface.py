from unittest.mock import Mock

from coax import ProtocolError, ReceiveError, ReceiveTimeout
from coax.interface import Interface

class MockInterface(Interface):
    def __init__(self, responses=[]):
        self.mock_responses = responses

        self.serial = Mock(port='/dev/mock')

        self.legacy_firmware_detected = None
        self.legacy_firmware_version = None

        # Wrap the reset and execute methods so calls can be asserted.
        self.reset = Mock(wraps=self.reset)
        self._execute = Mock(wraps=self._execute)

    def _execute(self, commands, timeout):
        return [self._mock_get_response(device_address, command) for (device_address, command) in commands]

    def reset_mock(self):
        self.reset.reset_mock()
        self._execute.reset_mock()

    def assert_command_executed(self, device_address, command_type, predicate=None):
        if not self._mock_get_execute_commands(device_address, command_type, predicate):
            raise AssertionError('Expected command to be executed')

    def assert_command_not_executed(self, device_address, command_type, predicate=None):
        if self._mock_get_execute_commands(device_address, command_type, predicate):
            raise AssertionError('Expected command not to be executed')

    def _mock_get_execute_commands(self, device_address, command_type, predicate):
        calls = self._execute.call_args_list

        commands = []

        for call in calls:
            for command in call[0][0]:
                (call_device_address, call_command) = command

                if call_device_address == device_address and isinstance(call_command, command_type):
                    if predicate is None or predicate(call_command):
                        commands.append(command)

        return commands

    def _mock_get_response(self, device_address, command):
        for (mock_device_address, mock_command_type, mock_predicate, mock_response) in self.mock_responses:
            if mock_device_address == device_address and isinstance(command, mock_command_type):
                if mock_predicate is None or mock_predicate(command):
                    if callable(mock_response):
                        try:
                            return mock_response()
                        except (ProtocolError, ReceiveError, ReceiveTimeout) as error:
                            return error

                    return mock_response

        return None
