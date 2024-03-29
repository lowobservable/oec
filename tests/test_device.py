import unittest
from unittest.mock import Mock, patch

from logging import Logger
from coax import TerminalType, Feature, ReadAddressCounterHi, ReadAddressCounterLo, ReadTerminalId, ReadExtendedId, ReadFeatureId, ProtocolError, LoadAddressCounterLo, LoadSecondaryControl
from coax.protocol import TerminalId

import context

from oec.interface import InterfaceWrapper
from oec.device import address_commands, format_address, get_ids, get_features, get_keyboard_description, _jumbo_write_split_data

from mock_interface import MockInterface

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

class FormatAddressTestCase(unittest.TestCase):
    def setUp(self):
        self.interface = MockInterface()

    def test_no_port(self):
        self.assertEqual(format_address(InterfaceWrapper(self.interface), None), '/dev/mock#0')

    def test_known_multiplexer_port(self):
        self.assertEqual(format_address(InterfaceWrapper(self.interface), 0b110000), '/dev/mock#3')

    def test_unknown_multiplexer_port(self):
        self.assertEqual(format_address(InterfaceWrapper(self.interface), 0b111111), '/dev/mock?111111')

class GetIdsTestCase(unittest.TestCase):
    def setUp(self):
        self.interface = MockInterface()

        patcher = patch('oec.device.logger', autospec=Logger)

        self.logger = patcher.start()

        patcher = patch('oec.device.time.sleep')

        self.sleep = patcher.start()

        self.addCleanup(patch.stopall)

    def test_dft(self):
        # Arrange
        self.interface.mock_responses = [(None, ReadTerminalId, None, TerminalId(0b00000001))]

        # Act
        (terminal_id, extended_id) = get_ids(InterfaceWrapper(self.interface), None)

        # Assert
        self.assertEqual(terminal_id.type, TerminalType.DFT)
        self.assertIsNone(extended_id)

        self.interface.assert_command_not_executed(None, ReadExtendedId)

    def test_no_extended_id(self):
        # Arrange
        self.interface.mock_responses = [(None, ReadTerminalId, None, TerminalId(0b11110100))]

        # Act
        (terminal_id, extended_id) = get_ids(InterfaceWrapper(self.interface), None)

        # Assert
        self.assertEqual(terminal_id.type, TerminalType.CUT)
        self.assertEqual(terminal_id.model, 2)
        self.assertEqual(terminal_id.keyboard, 15)
        self.assertIsNone(extended_id)

        self.interface.assert_command_executed(None, ReadExtendedId)

    def test_extended_id(self):
        # Arrange
        self.interface.mock_responses = [
            (None, ReadTerminalId, None, TerminalId(0b11110100)),
            (None, ReadExtendedId, None, bytes.fromhex('01 02 03 04'))
        ]

        # Act
        (terminal_id, extended_id) = get_ids(InterfaceWrapper(self.interface), None)

        # Assert
        self.assertEqual(terminal_id.type, TerminalType.CUT)
        self.assertEqual(terminal_id.model, 2)
        self.assertEqual(terminal_id.keyboard, 15)
        self.assertEqual(extended_id, '01020304')

        self.interface.assert_command_executed(None, LoadSecondaryControl, lambda command: command.control.big == False)
        self.interface.assert_command_executed(None, LoadAddressCounterLo, lambda command: command.address == 0)

    def test_terminal_id_error(self):
        # Arrange
        self.interface.mock_responses = [
            (None, ReadTerminalId, None, Mock(side_effect=ProtocolError))
        ]

        # Act
        (terminal_id, extended_id) = get_ids(InterfaceWrapper(self.interface), None)

        # Assert
        self.assertIsNone(terminal_id)
        self.assertIsNone(extended_id)

        self.logger.warning.assert_called()

    def test_extended_id_error(self):
        # Arrange
        self.interface.mock_responses = [
            (None, ReadTerminalId, None, TerminalId(0b11110100)),
            (None, ReadExtendedId, None, Mock(side_effect=ProtocolError))
        ]

        # Act
        (terminal_id, extended_id) = get_ids(InterfaceWrapper(self.interface), None)

        # Assert
        self.assertEqual(terminal_id.type, TerminalType.CUT)
        self.assertEqual(terminal_id.model, 2)
        self.assertEqual(terminal_id.keyboard, 15)
        self.assertIsNone(extended_id)

        self.logger.warning.assert_called()

class GetFeaturesTestCase(unittest.TestCase):
    def setUp(self):
        self.interface = MockInterface()

    def test_no_features(self):
        # Act
        features = get_features(InterfaceWrapper(self.interface), None)

        # Assert
        self.assertEqual(features, { })

    def test_eab_feature(self):
        # Arrange
        self.interface.mock_responses = [(None, ReadFeatureId, lambda command: command.feature_address == 7, Feature.EAB.value)]

        # Act
        features = get_features(InterfaceWrapper(self.interface), None)

        # Assert
        self.assertEqual(features, { Feature.EAB: 7 })

class GetKeyboardDescriptionTestCase(unittest.TestCase):
    def test(self):
        CASES = [
            (10, None, '3278-TYPEWRITER'),
            (0, 'c1347200', 'IBM-TYPEWRITER'),
            (10, '41347200', '3278-TYPEWRITER'),
            (0, 'c2347200', 'IBM-DATAENTRY'),
            (0, 'c3347200', 'IBM-APL'),
            (0, 'c1348301', 'IBM-ENHANCED'),
            (0, 'e1347200', 'USER-1'),
            (0, 'e4347200', 'USER-4')
        ]

        for (keyboard, extended_id, expected_description) in CASES:
            with self.subTest(keyboard=keyboard, extended_id=extended_id):
                terminal_id = TerminalId(0b0000_0100 | (keyboard << 4))

                description = get_keyboard_description(terminal_id, extended_id)

                self.assertEqual(description, expected_description)

class JumboWriteSplitDataTestCase(unittest.TestCase):
    def test_no_split_strategy(self):
        for data in [bytes(range(0, 64)), (bytes.fromhex('00'), 64)]:
            with self.subTest(data=data):
                result = _jumbo_write_split_data(data, None)

                self.assertEqual(len(result), 1)

                self.assertEqual(result[0], data)

    def test_split_strategy_one_chunk(self):
        for data in [bytes(range(0, 16)), (bytes.fromhex('00'), 16), bytes(range(0, 31)), (bytes.fromhex('00'), 31)]:
            with self.subTest(data=data):
                result = _jumbo_write_split_data(data, 32)

                self.assertEqual(len(result), 1)

                self.assertEqual(result[0], data)

    def test_split_strategy_two_chunks(self):
        for data in [bytes(range(0, 32)), (bytes.fromhex('00'), 32), bytes(range(0, 63)), (bytes.fromhex('00'), 63)]:
            with self.subTest(data=data):
                result = _jumbo_write_split_data(data, 32)

                self.assertEqual(len(result), 2)
                self.assertEqual(len(result[0]), 31)

    def test_split_strategy_three_chunks(self):
        for data in [bytes(range(0, 64)), (bytes.fromhex('00'), 64), bytes(range(0, 95)), (bytes.fromhex('00'), 95)]:
            with self.subTest(data=data):
                result = _jumbo_write_split_data(data, 32)

                self.assertEqual(len(result), 3)
                self.assertEqual(len(result[0]), 31)
                self.assertEqual(len(result[1]), 32)
