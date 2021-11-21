import unittest
from unittest.mock import Mock, patch

from logging import Logger
from coax import TerminalType, Feature, ReadAddressCounterHi, ReadAddressCounterLo, ReadTerminalId, ReadExtendedId, ReadFeatureId, ProtocolError
from coax.protocol import TerminalId

import context

from oec.interface import InterfaceWrapper
from oec.device import address_commands, format_address, get_ids, get_features, _jumbo_write_split_data

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

    def test_extended_id_second_attempt(self):
        # Arrange
        self.interface.mock_responses = [
            (None, ReadTerminalId, None, TerminalId(0b11110100)),
            (None, ReadExtendedId, None, Mock(side_effect=[ProtocolError, bytes.fromhex('01 02 03 04')]))
        ]

        # Act
        (terminal_id, extended_id) = get_ids(InterfaceWrapper(self.interface), None)

        # Assert
        self.assertEqual(terminal_id.type, TerminalType.CUT)
        self.assertEqual(terminal_id.model, 2)
        self.assertEqual(terminal_id.keyboard, 15)
        self.assertEqual(extended_id, '01020304')

        self.logger.warning.assert_called()

    def test_extended_id_failed(self):
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

    def test_override(self):
        # Act
        with patch.dict('oec.device.os.environ', { 'COAX_FEATURES': 'EAB@7' }):
            features = get_features(InterfaceWrapper(self.interface), None)

        # Assert
        self.assertEqual(features, { Feature.EAB: 7 })

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
