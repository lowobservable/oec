import unittest
from unittest.mock import Mock, patch

from coax import ReadAddressCounterHi, ReadAddressCounterLo, ProtocolError

import context

from oec.interface import InterfaceWrapper, AggregateExecuteError, address_commands

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

    def test_split_jumbo_write_strategy(self):
        # Arrange
        self.get_jumbo_write_strategy.return_value = 'split'

        # Act
        interface_wrapper = InterfaceWrapper(self.interface)

        # Assert
        self.assertEqual(interface_wrapper.jumbo_write_strategy, 'split')
        self.assertEqual(interface_wrapper.jumbo_write_max_length, 1024)

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
        with self.assertRaises(AggregateExecuteError) as context:
            self.interface_wrapper.execute([(None, ReadAddressCounterHi()), (None, ReadAddressCounterLo())])

        error = context.exception

        self.assertEqual(len(error.errors), 1)
        self.assertIsInstance(error.errors[0], ProtocolError)

        self.assertEqual(len(error.responses), 2)

class InterfaceWrapperJumboWriteSplitDataTestCase(unittest.TestCase):
    def setUp(self):
        self.interface = MockInterface()

        self.interface_wrapper = InterfaceWrapper(self.interface)

    def test_no_split_strategy(self):
        # Arrange
        self.interface_wrapper.jumbo_write_strategy = None
        self.interface_wrapper.jumbo_write_max_length = 32

        # Act and assert
        for data in [bytes(range(0, 64)), (bytes.fromhex('00'), 64)]:
            with self.subTest(data=data):
                result = self.interface_wrapper.jumbo_write_split_data(data)

                self.assertEqual(len(result), 1)

                self.assertEqual(result[0], data)

    def test_split_strategy_one_chunk(self):
        # Arrange
        self.interface_wrapper.jumbo_write_strategy = 'split'
        self.interface_wrapper.jumbo_write_max_length = 32

        # Act and assert
        for data in [bytes(range(0, 16)), (bytes.fromhex('00'), 16), bytes(range(0, 31)), (bytes.fromhex('00'), 31)]:
            with self.subTest(data=data):
                result = self.interface_wrapper.jumbo_write_split_data(data)

                self.assertEqual(len(result), 1)

                self.assertEqual(result[0], data)

    def test_split_strategy_two_chunks(self):
        # Arrange
        self.interface_wrapper.jumbo_write_strategy = 'split'
        self.interface_wrapper.jumbo_write_max_length = 32

        # Act and assert
        for data in [bytes(range(0, 32)), (bytes.fromhex('00'), 32), bytes(range(0, 63)), (bytes.fromhex('00'), 63)]:
            with self.subTest(data=data):
                result = self.interface_wrapper.jumbo_write_split_data(data)

                self.assertEqual(len(result), 2)
                self.assertEqual(len(result[0]), 31)

    def test_split_strategy_three_chunks(self):
        # Arrange
        self.interface_wrapper.jumbo_write_strategy = 'split'
        self.interface_wrapper.jumbo_write_max_length = 32

        # Act and assert
        for data in [bytes(range(0, 64)), (bytes.fromhex('00'), 64), bytes(range(0, 95)), (bytes.fromhex('00'), 95)]:
            with self.subTest(data=data):
                result = self.interface_wrapper.jumbo_write_split_data(data)

                self.assertEqual(len(result), 3)
                self.assertEqual(len(result[0]), 31)
                self.assertEqual(len(result[1]), 32)

class AddressCommandsTestCase(unittest.TestCase):
    def test_single_command(self):
        # Arrange
        command = ReadAddressCounterHi()

        # Act
        result = address_commands(0b111000, command)

        # Assert
        self.assertEqual(result, (0b111000, command))

    def test_multiple_commands(self):
        # Arrange
        commands = [ReadAddressCounterHi(), ReadAddressCounterLo()]

        # Act
        result = address_commands(0b111000, commands)

        # Assert
        self.assertEqual(result, [(0b111000, commands[0]), (0b111000, commands[1])])
