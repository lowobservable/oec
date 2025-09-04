import unittest
from unittest.mock import Mock, patch

from coax import ReadAddressCounterHi, ReadAddressCounterLo, ProtocolError, ReceiveTimeout, ReceiveError

import context

from oec.interface import InterfaceWrapper, ExecuteError

from mock_interface import MockInterface

class InterfaceWrapperInitTestCase(unittest.TestCase):
    def setUp(self):
        self.interface = MockInterface()

        patcher = patch('oec.interface._get_jumbo_write_strategy')

        self.get_jumbo_write_strategy = patcher.start()

        patcher = patch('oec.interface._print_i1_jumbo_write_notice')

        self.print_i1_jumbo_write_notice = patcher.start()

        self.addCleanup(patch.stopall)

    def test_no_jumbo_write_strategy(self):
        # Arrange
        self.get_jumbo_write_strategy.return_value = None

        # Act
        interface_wrapper = InterfaceWrapper(self.interface)

        # Assert
        self.assertIsNone(interface_wrapper.jumbo_write_strategy)
        self.assertIsNone(interface_wrapper.jumbo_write_max_length)

        self.print_i1_jumbo_write_notice.assert_not_called()

    def test_i1_no_jumbo_write_strategy(self):
        # Arrange
        self.interface.legacy_firmware_detected = True

        self.get_jumbo_write_strategy.return_value = None

        # Act
        interface_wrapper = InterfaceWrapper(self.interface)

        # Assert
        self.assertEqual(interface_wrapper.jumbo_write_strategy, 'split')
        self.assertEqual(interface_wrapper.jumbo_write_max_length, 1024)

        self.print_i1_jumbo_write_notice.assert_called()

class InterfaceWrapperExecuteTestCase(unittest.TestCase):
    def setUp(self):
        self.interface = MockInterface()

        self.interface_wrapper = InterfaceWrapper(self.interface)

    def test_single_command(self):
        # Arrange
        self.interface.mock_responses = [(None, ReadAddressCounterHi, None, 0x00)]

        # Act
        response = self.interface_wrapper.execute((None, ReadAddressCounterHi()))

        # Assert
        self.assertEqual(response, 0x00)

    def test_single_command_that_raises_error(self):
        # Arrange
        self.interface.mock_responses = [(None, ReadAddressCounterHi, None, Mock(side_effect=ProtocolError))]

        # Act and assert
        with self.assertRaises(ProtocolError):
            self.interface_wrapper.execute((None, ReadAddressCounterHi()))

    def test_multiple_commands(self):
        # Arrange
        self.interface.mock_responses = [
            (None, ReadAddressCounterHi, None, 0x00),
            (None, ReadAddressCounterLo, None, 0xff)
        ]

        # Act
        responses = self.interface_wrapper.execute([(None, ReadAddressCounterHi()), (None, ReadAddressCounterLo())])

        # Assert
        self.assertEqual(responses, [0x00, 0xff])

    def test_multiple_commands_that_returns_error(self):
        # Arrange
        self.interface.mock_responses = [
            (None, ReadAddressCounterHi, None, 0x00),
            (None, ReadAddressCounterLo, None, Mock(side_effect=ProtocolError))
        ]

        # Act and assert
        with self.assertRaises(ExecuteError) as context:
            self.interface_wrapper.execute([(None, ReadAddressCounterHi()), (None, ReadAddressCounterLo())])

        error = context.exception

        self.assertEqual(len(error.errors), 1)
        self.assertIsInstance(error.errors[0], ProtocolError)

        self.assertEqual(len(error.responses), 2)

class ExecuteErrorTestCase(unittest.TestCase):
    def test_single_str_error(self):
        error = ExecuteError([ReceiveError('ReceiveErrorMessage')], [])

        self.assertEqual(str(error), 'ReceiveErrorMessage')

    def test_single_repr_error(self):
        error = ExecuteError([ReceiveTimeout()], [])

        self.assertEqual(str(error), 'ReceiveTimeout()')

    def test_multiple_errors_first_str_error(self):
        error = ExecuteError([ReceiveError('ReceiveErrorMessage'), ReceiveTimeout()], [])

        self.assertEqual(str(error), 'ReceiveErrorMessage and 1 other error')

    def test_multiple_errors_first_repr_error(self):
        error = ExecuteError([ReceiveTimeout(), ReceiveError('ReceiveErrorMessage')], [])

        self.assertEqual(str(error), 'ReceiveTimeout() and 1 other error')
