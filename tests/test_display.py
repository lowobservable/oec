import unittest
from unittest.mock import Mock, patch

import context

from oec.display import Dimensions, Display, StatusLine, BufferedDisplay, encode_ascii_character, encode_ebcdic_character, encode_string

class DisplayClearTestCase(unittest.TestCase):
    def setUp(self):
        self.terminal = Mock()

        dimensions = Dimensions(24, 80)

        self.display = Display(self.terminal, dimensions, None)

        self.display.write = Mock(wraps=self.display.write)
        self.display._load_address_counter = Mock(wraps=self.display._load_address_counter)

        patcher = patch('oec.display.read_address_counter_hi')

        self.read_address_counter_hi_mock = patcher.start()

        patcher = patch('oec.display.read_address_counter_lo')

        self.read_address_counter_lo_mock = patcher.start()

        patcher = patch('oec.display.load_address_counter_hi')

        self.load_address_counter_hi_mock = patcher.start()

        patcher = patch('oec.display.load_address_counter_lo')

        self.load_address_counter_lo_mock = patcher.start()

        patcher = patch('oec.display.write_data')

        self.write_data_mock = patcher.start()

        patcher = patch('oec.display.eab_write_alternate')

        self.eab_write_alternate_mock = patcher.start()

        self.addCleanup(patch.stopall)

    def test_excluding_status_line_with_no_eab_feature(self):
        # Act
        self.display.clear(clear_status_line=False)

        # Assert
        self.display.write.assert_called_with((b'\x00', 1920), None, address=80)
        self.display._load_address_counter.assert_called_with(80, True)

    def test_excluding_status_line_with_eab(self):
        # Arrange
        self.display.eab_address = 7

        # Act
        self.display.clear(clear_status_line=False)

        # Assert
        self.display.write.assert_called_with((b'\x00', 1920), (b'\x00', 1920), address=80)
        self.display._load_address_counter.assert_called_with(80, True)

    def test_including_status_line_with_no_eab_feature(self):
        # Act
        self.display.clear(clear_status_line=True)

        # Assert
        self.display.write.assert_called_with((b'\x00', 2000), None, address=0)
        self.display._load_address_counter.assert_called_with(80, True)

    def test_including_status_line_with_eab(self):
        # Arrange
        self.display.eab_address = 7

        # Act
        self.display.clear(clear_status_line=True)

        # Assert
        self.display.write.assert_called_with((b'\x00', 2000), (b'\x00', 2000), address=0)
        self.display._load_address_counter.assert_called_with(80, True)

class DisplayMoveCursorTestCase(unittest.TestCase):
    def setUp(self):
        self.terminal = Mock()

        dimensions = Dimensions(24, 80)

        self.display = Display(self.terminal, dimensions, None)

        self.display._load_address_counter = Mock(wraps=self.display._load_address_counter)

        patcher = patch('oec.display.load_address_counter_hi')

        self.load_address_counter_hi_mock = patcher.start()

        patcher = patch('oec.display.load_address_counter_lo')

        self.load_address_counter_lo_mock = patcher.start()

        self.addCleanup(patch.stopall)

    def test_with_address(self):
        # Act
        self.display.move_cursor(address=895)

        # Assert
        self.assertEqual(self.display.address_counter, 895)

        self.display._load_address_counter.assert_called_with(895, False)

    def test_with_index(self):
        # Act
        self.display.move_cursor(index=815)

        # Assert
        self.assertEqual(self.display.address_counter, 895)

        self.display._load_address_counter.assert_called_with(895, False)

    def test_with_row_and_column(self):
        # Act
        self.display.move_cursor(row=10, column=15)

        # Assert
        self.assertEqual(self.display.address_counter, 895)

        self.display._load_address_counter.assert_called_with(895, False)

    def test_force(self):
        # Act
        self.display.move_cursor(index=815, force_load=True)

        # Assert
        self.assertEqual(self.display.address_counter, 895)

        self.display._load_address_counter.assert_called_with(895, True)

class DisplayWriteTestCase(unittest.TestCase):
    def setUp(self):
        self.terminal = Mock()

        dimensions = Dimensions(24, 80)

        self.display = Display(self.terminal, dimensions, None)

        self.display._read_address_counter = Mock(wraps=self.display._read_address_counter)
        self.display._load_address_counter = Mock(wraps=self.display._load_address_counter)

        patcher = patch('oec.display.read_address_counter_hi')

        self.read_address_counter_hi_mock = patcher.start()

        patcher = patch('oec.display.read_address_counter_lo')

        self.read_address_counter_lo_mock = patcher.start()

        patcher = patch('oec.display.load_address_counter_hi')

        self.load_address_counter_hi_mock = patcher.start()

        patcher = patch('oec.display.load_address_counter_lo')

        self.load_address_counter_lo_mock = patcher.start()

        patcher = patch('oec.display.write_data')

        self.write_data_mock = patcher.start()

        patcher = patch('oec.display.eab_write_alternate')

        self.eab_write_alternate_mock = patcher.start()

        self.addCleanup(patch.stopall)

    def test_no_eab_feature(self):
        # Act and assert
        with self.assertRaisesRegex(RuntimeError, 'No EAB feature'):
            self.display.write(bytes.fromhex('01 02 03'), (b'\x00', 3))

    def test_regen_eab_data_mismatch_format(self):
        # Arrange
        self.display.eab_address = 7

        # Act and assert
        with self.assertRaisesRegex(ValueError, 'must be provided in same form'):
            self.display.write(bytes.fromhex('01 02 03'), (b'\x00', 3))

    def test_regen_eab_data_mismatch_length(self):
        # Arrange
        self.display.eab_address = 7

        # Act and assert
        with self.assertRaisesRegex(ValueError, 'data length must be equal'):
            self.display.write(bytes.fromhex('01 02 03'), bytes.fromhex('01 02'))

    def test_regen_eab_data_mismatch_length_repeat(self):
        # Arrange
        self.display.eab_address = 7

        # Act and assert
        with self.assertRaisesRegex(ValueError, 'pattern length must be equal'):
            self.display.write((bytes.fromhex('01 02 03'), 3), (b'\x00', 3))

    def test_regen_eab_data_mismatch_count_repeat(self):
        # Arrange
        self.display.eab_address = 7

        # Act and assert
        with self.assertRaisesRegex(ValueError, 'pattern count must be equal'):
            self.display.write((bytes.fromhex('01 02 03'), 3), (bytes.fromhex('01 02 03'), 2))

    def test_if_current_address_unknown(self):
        # Arrange
        self.assertIsNone(self.display.address_counter)

        # Act
        self.display.write(bytes.fromhex('01 02 03'), None)

        # Assert
        self.assertIsNone(self.display.address_counter)

        self.display._read_address_counter.assert_not_called()
        self.display._load_address_counter.assert_not_called()

    def test_address_if_current_address_unknown(self):
        # Arrange
        self.assertIsNone(self.display.address_counter)

        # Act
        self.display.write(bytes.fromhex('01 02 03'), None, address=80)

        # Assert
        self.assertEqual(self.display.address_counter, 83)

        self.display._read_address_counter.assert_not_called()
        self.display._load_address_counter.assert_called_with(80, force_load=False)

    def test_address_if_change(self):
        # Arrange
        self.display.address_counter = 160

        # Act
        self.display.write(bytes.fromhex('01 02 03'), None, address=80)

        # Assert
        self.assertEqual(self.display.address_counter, 83)

        self.display._read_address_counter.assert_not_called()
        self.display._load_address_counter.assert_called_with(80, force_load=False)

    def test_address_if_no_change(self):
        # Arrange
        self.display.address_counter = 80

        # Act
        self.display.write(bytes.fromhex('01 02 03'), None, address=80)

        # Assert
        self.assertEqual(self.display.address_counter, 83)

        self.display._read_address_counter.assert_not_called()
        self.display._load_address_counter.assert_called_with(80, force_load=False)

    def test_restore_original_address_if_current_address_unknown(self):
        # Arrange
        self.assertIsNone(self.display.address_counter)

        self.read_address_counter_hi_mock.return_value = 0
        self.read_address_counter_lo_mock.return_value = 160

        # Act
        self.display.write(bytes.fromhex('01 02 03'), None, restore_original_address=True)

        # Assert
        self.assertEqual(self.display.address_counter, 160)

        self.display._read_address_counter.assert_called_once()
        self.display._load_address_counter.assert_called_with(160, force_load=True)

    def test_restore_original_address_if_current_address_known(self):
        # Arrange
        self.display.address_counter = 160

        # Act
        self.display.write(bytes.fromhex('01 02 03'), None, restore_original_address=True)

        # Assert
        self.assertEqual(self.display.address_counter, 160)

        self.display._read_address_counter.assert_not_called()
        self.display._load_address_counter.assert_called_with(160, force_load=True)

    def test_regen_only(self):
        # Arrange
        self.display.address_counter = 80

        # Act
        self.display.write(bytes.fromhex('01 02 03'), None)

        # Assert
        self.write_data_mock.assert_called_with(self.terminal.interface, bytes.fromhex('01 02 03'), jumbo_write_strategy=None)

    def test_regen_only_repeat(self):
        # Arrange
        self.display.address_counter = 80

        # Act
        self.display.write((bytes.fromhex('01 02 03'), 2), None)

        # Assert
        self.write_data_mock.assert_called_with(self.terminal.interface, (bytes.fromhex('01 02 03'), 2), jumbo_write_strategy=None)

    def test_regen_eab(self):
        # Arrange
        self.display.eab_address = 7
        self.display.address_counter = 80

        # Act
        self.display.write(bytes.fromhex('01 02 03'), bytes.fromhex('04 05 06'))

        # Assert
        self.eab_write_alternate_mock.assert_called_with(self.terminal.interface, 7, bytes.fromhex('01 04 02 05 03 06'), jumbo_write_strategy=None)

    def test_regen_eab_repeat(self):
        # Arrange
        self.display.eab_address = 7
        self.display.address_counter = 80

        # Act
        self.display.write((bytes.fromhex('01 02 03'), 2), (bytes.fromhex('04 05 06'), 2))

        # Assert
        self.eab_write_alternate_mock.assert_called_with(self.terminal.interface, 7, (bytes.fromhex('01 04 02 05 03 06'), 2), jumbo_write_strategy=None)

class DisplayLoadAddressCounterTestCase(unittest.TestCase):
    def setUp(self):
        self.terminal = Mock()

        dimensions = Dimensions(24, 80)

        self.display = Display(self.terminal, dimensions, None)

        patcher = patch('oec.display.load_address_counter_hi')

        self.load_address_counter_hi_mock = patcher.start()

        patcher = patch('oec.display.load_address_counter_lo')

        self.load_address_counter_lo_mock = patcher.start()

        self.addCleanup(patch.stopall)

    def test(self):
        # Act
        self.display._load_address_counter(895, force_load=False)

        # Assert
        self.assertEqual(self.display.address_counter, 895)

        self.load_address_counter_hi_mock.assert_called_with(self.terminal.interface, 3)
        self.load_address_counter_lo_mock.assert_called_with(self.terminal.interface, 127)

    def test_hi_change(self):
        # Arrange
        self.display._load_address_counter(895, force_load=False)

        self.load_address_counter_hi_mock.reset_mock()
        self.load_address_counter_lo_mock.reset_mock()

        # Act
        self.display._load_address_counter(1151, force_load=False)

        # Assert
        self.assertEqual(self.display.address_counter, 1151)

        self.load_address_counter_hi_mock.assert_called_with(self.terminal.interface, 4)
        self.load_address_counter_lo_mock.assert_not_called()

    def test_lo_change(self):
        # Arrange
        self.display._load_address_counter(895, force_load=False)

        self.load_address_counter_hi_mock.reset_mock()
        self.load_address_counter_lo_mock.reset_mock()

        # Act
        self.display._load_address_counter(896, force_load=False)

        # Assert
        self.assertEqual(self.display.address_counter, 896)

        self.load_address_counter_hi_mock.assert_not_called()
        self.load_address_counter_lo_mock.assert_called_with(self.terminal.interface, 128)

    def test_hi_lo_change(self):
        # Arrange
        self.display._load_address_counter(895, force_load=False)

        self.load_address_counter_hi_mock.reset_mock()
        self.load_address_counter_lo_mock.reset_mock()

        # Act
        self.display._load_address_counter(1152, force_load=False)

        # Assert
        self.assertEqual(self.display.address_counter, 1152)

        self.load_address_counter_hi_mock.assert_called_with(self.terminal.interface, 4)
        self.load_address_counter_lo_mock.assert_called_with(self.terminal.interface, 128)

    def test_no_change(self):
        # Arrange
        self.display._load_address_counter(80, force_load=False)

        self.load_address_counter_hi_mock.reset_mock()
        self.load_address_counter_lo_mock.reset_mock()

        # Act
        self.display._load_address_counter(80, force_load=False)

        # Assert
        self.assertEqual(self.display.address_counter, 80)

        self.load_address_counter_hi_mock.assert_not_called()
        self.load_address_counter_lo_mock.assert_not_called()

    def test_no_change_force(self):
        # Arrange
        self.display._load_address_counter(80, force_load=False)

        self.load_address_counter_hi_mock.reset_mock()
        self.load_address_counter_lo_mock.reset_mock()

        # Act
        self.display._load_address_counter(80, force_load=True)

        # Assert
        self.assertEqual(self.display.address_counter, 80)

        self.load_address_counter_hi_mock.assert_called_with(self.terminal.interface, 0)
        self.load_address_counter_lo_mock.assert_called_with(self.terminal.interface, 80)

class StatusLineWriteTestCase(unittest.TestCase):
    def setUp(self):
        self.display = Mock()

        self.display.dimensions = Dimensions(24, 80)

        self.status_line = StatusLine(self.display)

    def test(self):
        self.status_line.write(77, bytes.fromhex('01 02 03'))

    def test_column_out_of_range(self):
        with self.assertRaisesRegex(ValueError, 'Column is out of range'):
            self.status_line.write(80, bytes.fromhex('01 02 03'))

    def test_length_out_of_range(self):
        with self.assertRaisesRegex(ValueError, 'Length is out of range'):
            self.status_line.write(78, bytes.fromhex('01 02 03'))

class BufferedDisplayBufferedWriteByteTestCase(unittest.TestCase):
    def setUp(self):
        self.terminal = Mock()

        dimensions = Dimensions(24, 80)

        self.buffered_display = BufferedDisplay(self.terminal, dimensions, None)

    def test_no_eab_feature(self):
        # Act and assert
        with self.assertRaisesRegex(RuntimeError, 'No EAB feature'):
            self.buffered_display.buffered_write_byte(0x01, 0x02, address=80)

    def test_no_address(self):
        # Act and assert
        with self.assertRaisesRegex(ValueError, 'Either address, index or row and column is required'):
            self.buffered_display.buffered_write_byte(0x01, None)

    def test_regen_no_change_with_no_eab_feature(self):
        # Arrange
        self.assertFalse(self.buffered_display.dirty)

        # Act and assert
        self.assertFalse(self.buffered_display.buffered_write_byte(0x00, None, address=80))

        self.assertFalse(self.buffered_display.dirty)

    def test_regen_change_with_no_eab_feature(self):
        # Arrange
        self.assertFalse(self.buffered_display.dirty)

        # Act and assert
        self.assertTrue(self.buffered_display.buffered_write_byte(0x01, None, address=80))

        self.assertSequenceEqual(self.buffered_display.dirty, [80])

        self.assertEqual(self.buffered_display.regen_buffer[80], 0x01)

    def test_regen_no_change_eab_no_change(self):
        # Arrange
        dimensions = Dimensions(24, 80)

        self.buffered_display = BufferedDisplay(self.terminal, dimensions, 7)

        self.assertFalse(self.buffered_display.dirty)

        # Act and assert
        self.assertFalse(self.buffered_display.buffered_write_byte(0x00, 0x00, address=80))

        self.assertFalse(self.buffered_display.dirty)

    def test_regen_change_eab_no_change(self):
        # Arrange
        dimensions = Dimensions(24, 80)

        self.buffered_display = BufferedDisplay(self.terminal, dimensions, 7)

        self.assertFalse(self.buffered_display.dirty)

        # Act and assert
        self.assertTrue(self.buffered_display.buffered_write_byte(0x01, 0x00, address=80))

        self.assertSequenceEqual(self.buffered_display.dirty, [80])

        self.assertEqual(self.buffered_display.regen_buffer[80], 0x01)
        self.assertEqual(self.buffered_display.eab_buffer[80], 0x00)

    def test_regen_no_change_eab_change(self):
        # Arrange
        dimensions = Dimensions(24, 80)

        self.buffered_display = BufferedDisplay(self.terminal, dimensions, 7)

        self.assertFalse(self.buffered_display.dirty)

        # Act and assert
        self.assertTrue(self.buffered_display.buffered_write_byte(0x00, 0x02, address=80))

        self.assertSequenceEqual(self.buffered_display.dirty, [80])

        self.assertEqual(self.buffered_display.regen_buffer[80], 0x00)
        self.assertEqual(self.buffered_display.eab_buffer[80], 0x02)

    def test_regen_change_eab_change(self):
        # Arrange
        dimensions = Dimensions(24, 80)

        self.buffered_display = BufferedDisplay(self.terminal, dimensions, 7)

        self.assertFalse(self.buffered_display.dirty)

        # Act and assert
        self.assertTrue(self.buffered_display.buffered_write_byte(0x01, 0x02, address=80))

        self.assertSequenceEqual(self.buffered_display.dirty, [80])

        self.assertEqual(self.buffered_display.regen_buffer[80], 0x01)
        self.assertEqual(self.buffered_display.eab_buffer[80], 0x02)

class BufferedDisplayFlushTestCase(unittest.TestCase):
    def setUp(self):
        self.terminal = Mock()

        dimensions = Dimensions(24, 80)

        self.buffered_display = BufferedDisplay(self.terminal, dimensions, None)

        self.buffered_display.write = Mock(wraps=self.buffered_display.write)

        patcher = patch('oec.display.read_address_counter_hi')

        self.read_address_counter_hi_mock = patcher.start()

        patcher = patch('oec.display.read_address_counter_lo')

        self.read_address_counter_lo_mock = patcher.start()

        patcher = patch('oec.display.load_address_counter_hi')

        self.load_address_counter_hi_mock = patcher.start()

        patcher = patch('oec.display.load_address_counter_lo')

        self.load_address_counter_lo_mock = patcher.start()

        patcher = patch('oec.display.write_data')

        self.write_data_mock = patcher.start()

        patcher = patch('oec.display.eab_write_alternate')

        self.eab_write_alternate_mock = patcher.start()

        self.addCleanup(patch.stopall)

    def test_no_changes(self):
        # Arrange
        self.assertFalse(self.buffered_display.dirty)

        # Act and assert
        self.assertFalse(self.buffered_display.flush())

        self.assertFalse(self.buffered_display.dirty)

        self.buffered_display.write.assert_not_called()

    def test_single_range_with_no_eab_feature(self):
        # Arrange
        self.assertFalse(self.buffered_display.dirty)

        self.buffered_display.buffered_write_byte(0x01, None, address=80)
        self.buffered_display.buffered_write_byte(0x02, None, address=81)
        self.buffered_display.buffered_write_byte(0x03, None, address=82)

        # Act and assert
        self.assertTrue(self.buffered_display.flush())

        self.assertFalse(self.buffered_display.dirty)
        self.assertEqual(self.buffered_display.regen_buffer[80:83], bytes.fromhex('01 02 03'))

        self.buffered_display.write.assert_called_with(bytes.fromhex('01 02 03'), None, address=80)

    def test_single_range_with_eab_feature(self):
        # Arrange
        dimensions = Dimensions(24, 80)

        self.buffered_display = BufferedDisplay(self.terminal, dimensions, 7)

        self.buffered_display.write = Mock(wraps=self.buffered_display.write)

        self.assertFalse(self.buffered_display.dirty)

        self.buffered_display.buffered_write_byte(0x01, 0x11, address=80)
        self.buffered_display.buffered_write_byte(0x02, 0x12, address=81)
        self.buffered_display.buffered_write_byte(0x03, 0x13, address=82)

        # Act and assert
        self.assertTrue(self.buffered_display.flush())

        self.assertFalse(self.buffered_display.dirty)
        self.assertEqual(self.buffered_display.regen_buffer[80:83], bytes.fromhex('01 02 03'))
        self.assertEqual(self.buffered_display.eab_buffer[80:83], bytes.fromhex('11 12 13'))

        self.buffered_display.write.assert_called_with(bytes.fromhex('01 02 03'), bytes.fromhex('11 12 13'), address=80)

    def test_multiple_ranges_with_no_eab_feature(self):
        # Arrange
        self.assertFalse(self.buffered_display.dirty)

        self.buffered_display.buffered_write_byte(0x01, None, address=80)
        self.buffered_display.buffered_write_byte(0x02, None, address=81)
        self.buffered_display.buffered_write_byte(0x03, None, address=82)
        self.buffered_display.buffered_write_byte(0x05, None, address=110)
        self.buffered_display.buffered_write_byte(0x06, None, address=111)
        self.buffered_display.buffered_write_byte(0x07, None, address=112)
        self.buffered_display.buffered_write_byte(0x04, None, address=100)

        # Act and assert
        self.assertTrue(self.buffered_display.flush())

        self.assertFalse(self.buffered_display.dirty)
        self.assertEqual(self.buffered_display.regen_buffer[80:83], bytes.fromhex('01 02 03'))
        self.assertEqual(self.buffered_display.regen_buffer[100:101], bytes.fromhex('04'))
        self.assertEqual(self.buffered_display.regen_buffer[110:113], bytes.fromhex('05 06 07'))

        self.buffered_display.write.assert_called_with(bytes.fromhex('01 02 03 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 04 00 00 00 00 00 00 00 00 00 05 06 07'), None, address=80)

    def test_multiple_ranges_with_eab_feature(self):
        # Arrange
        dimensions = Dimensions(24, 80)

        self.buffered_display = BufferedDisplay(self.terminal, dimensions, 7)

        self.buffered_display.write = Mock(wraps=self.buffered_display.write)

        self.assertFalse(self.buffered_display.dirty)

        self.buffered_display.buffered_write_byte(0x01, 0x11, address=80)
        self.buffered_display.buffered_write_byte(0x02, 0x12, address=81)
        self.buffered_display.buffered_write_byte(0x03, 0x13, address=82)
        self.buffered_display.buffered_write_byte(0x05, 0x15, address=110)
        self.buffered_display.buffered_write_byte(0x06, 0x16, address=111)
        self.buffered_display.buffered_write_byte(0x07, 0x17, address=112)
        self.buffered_display.buffered_write_byte(0x04, 0x14, address=100)

        # Act and assert
        self.assertTrue(self.buffered_display.flush())

        self.assertFalse(self.buffered_display.dirty)
        self.assertEqual(self.buffered_display.regen_buffer[80:83], bytes.fromhex('01 02 03'))
        self.assertEqual(self.buffered_display.regen_buffer[100:101], bytes.fromhex('04'))
        self.assertEqual(self.buffered_display.regen_buffer[110:113], bytes.fromhex('05 06 07'))
        self.assertEqual(self.buffered_display.eab_buffer[80:83], bytes.fromhex('11 12 13'))
        self.assertEqual(self.buffered_display.eab_buffer[100:101], bytes.fromhex('14'))
        self.assertEqual(self.buffered_display.eab_buffer[110:113], bytes.fromhex('15 16 17'))

        self.buffered_display.write.assert_called_with(bytes.fromhex('01 02 03 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 04 00 00 00 00 00 00 00 00 00 05 06 07'), bytes.fromhex('11 12 13 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 14 00 00 00 00 00 00 00 00 00 15 16 17'), address=80)

class BufferedDisplayClearTestCase(unittest.TestCase):
    def setUp(self):
        self.terminal = Mock()

        dimensions = Dimensions(24, 80)

        self.buffered_display = BufferedDisplay(self.terminal, dimensions, None)

        self.buffered_display.write = Mock(wraps=self.buffered_display.write)
        self.buffered_display._load_address_counter = Mock(wraps=self.buffered_display._load_address_counter)

        patcher = patch('oec.display.read_address_counter_hi')

        self.read_address_counter_hi_mock = patcher.start()

        patcher = patch('oec.display.read_address_counter_lo')

        self.read_address_counter_lo_mock = patcher.start()

        patcher = patch('oec.display.load_address_counter_hi')

        self.load_address_counter_hi_mock = patcher.start()

        patcher = patch('oec.display.load_address_counter_lo')

        self.load_address_counter_lo_mock = patcher.start()

        patcher = patch('oec.display.write_data')

        self.write_data_mock = patcher.start()

        patcher = patch('oec.display.eab_write_alternate')

        self.eab_write_alternate_mock = patcher.start()

        self.addCleanup(patch.stopall)

    def test_excluding_status_line_with_no_eab_feature(self):
        # Arrange
        self.buffered_display.buffered_write_byte(0x01, None, address=80)

        self.assertTrue(self.buffered_display.dirty)

        # Act
        self.buffered_display.clear(clear_status_line=False)

        # Assert
        self.buffered_display.write.assert_called_with((b'\x00', 1920), None, address=80)
        self.buffered_display._load_address_counter.assert_called_with(80, True)

        self.assertTrue(all(byte == 0x00 for byte in self.buffered_display.regen_buffer))
        self.assertFalse(self.buffered_display.dirty)

    def test_excluding_status_line_with_eab_feature(self):
        # Arrange
        dimensions = Dimensions(24, 80)

        self.buffered_display = BufferedDisplay(self.terminal, dimensions, 7)

        self.buffered_display.write = Mock(wraps=self.buffered_display.write)
        self.buffered_display._load_address_counter = Mock(wraps=self.buffered_display._load_address_counter)

        self.buffered_display.buffered_write_byte(0x01, 0x02, address=80)

        self.assertTrue(self.buffered_display.dirty)

        # Act
        self.buffered_display.clear(clear_status_line=False)

        # Assert
        self.buffered_display.write.assert_called_with((b'\x00', 1920), (b'\x00', 1920), address=80)
        self.buffered_display._load_address_counter.assert_called_with(80, True)

        self.assertTrue(all(byte == 0x00 for byte in self.buffered_display.regen_buffer))
        self.assertTrue(all(byte == 0x00 for byte in self.buffered_display.eab_buffer))
        self.assertFalse(self.buffered_display.dirty)

    def test_including_status_line_with_no_eab_feature(self):
        # Arrange
        self.buffered_display.buffered_write_byte(0x01, None, address=80)

        self.assertTrue(self.buffered_display.dirty)

        # Act
        self.buffered_display.clear(clear_status_line=True)

        # Assert
        self.buffered_display.write.assert_called_with((b'\x00', 2000), None, address=0)
        self.buffered_display._load_address_counter.assert_called_with(80, True)

        self.assertTrue(all(byte == 0x00 for byte in self.buffered_display.regen_buffer))
        self.assertFalse(self.buffered_display.dirty)

    def test_including_status_line_with_eab_feature(self):
        # Arrange
        dimensions = Dimensions(24, 80)

        self.buffered_display = BufferedDisplay(self.terminal, dimensions, 7)

        self.buffered_display.write = Mock(wraps=self.buffered_display.write)
        self.buffered_display._load_address_counter = Mock(wraps=self.buffered_display._load_address_counter)

        self.buffered_display.buffered_write_byte(0x01, 0x02, address=80)

        self.assertTrue(self.buffered_display.dirty)

        # Act
        self.buffered_display.clear(clear_status_line=True)

        # Assert
        self.buffered_display.write.assert_called_with((b'\x00', 2000), (b'\x00', 2000), address=0)
        self.buffered_display._load_address_counter.assert_called_with(80, True)

        self.assertTrue(all(byte == 0x00 for byte in self.buffered_display.regen_buffer))
        self.assertTrue(all(byte == 0x00 for byte in self.buffered_display.eab_buffer))
        self.assertFalse(self.buffered_display.dirty)

class BufferedDisplayWriteTestCase(unittest.TestCase):
    def setUp(self):
        self.terminal = Mock()

        dimensions = Dimensions(24, 80)

        self.buffered_display = BufferedDisplay(self.terminal, dimensions, None)

        self.buffered_display._read_address_counter = Mock(wraps=self.buffered_display._read_address_counter)
        self.buffered_display._load_address_counter = Mock(wraps=self.buffered_display._load_address_counter)

        patcher = patch('oec.display.read_address_counter_hi')

        self.read_address_counter_hi_mock = patcher.start()

        patcher = patch('oec.display.read_address_counter_lo')

        self.read_address_counter_lo_mock = patcher.start()

        patcher = patch('oec.display.load_address_counter_hi')

        self.load_address_counter_hi_mock = patcher.start()

        patcher = patch('oec.display.load_address_counter_lo')

        self.load_address_counter_lo_mock = patcher.start()

        patcher = patch('oec.display.write_data')

        self.write_data_mock = patcher.start()

        patcher = patch('oec.display.eab_write_alternate')

        self.eab_write_alternate_mock = patcher.start()

        self.addCleanup(patch.stopall)

    def test_if_current_address_unknown(self):
        # Arrange
        self.assertIsNone(self.buffered_display.address_counter)

        self.read_address_counter_hi_mock.return_value = 0
        self.read_address_counter_lo_mock.return_value = 160

        # Act
        self.buffered_display.write(bytes.fromhex('01 02 03'), None)

        # Assert
        self.assertEqual(self.buffered_display.address_counter, 163)

        self.assertEqual(self.buffered_display.regen_buffer[160:163], bytes.fromhex('01 02 03'))

        self.buffered_display._read_address_counter.assert_called()
        self.buffered_display._load_address_counter.assert_not_called()

    def test_address_if_current_address_unknown(self):
        # Arrange
        self.assertIsNone(self.buffered_display.address_counter)

        # Act
        self.buffered_display.write(bytes.fromhex('01 02 03'), None, address=80)

        # Assert
        self.assertEqual(self.buffered_display.address_counter, 83)

        self.assertEqual(self.buffered_display.regen_buffer[80:83], bytes.fromhex('01 02 03'))

        self.buffered_display._read_address_counter.assert_not_called()
        self.buffered_display._load_address_counter.assert_called_with(80, force_load=False)

    def test_regen_only(self):
        # Arrange
        self.buffered_display.address_counter = 80

        # Act
        self.buffered_display.write(bytes.fromhex('01 02 03'), None)

        # Assert
        self.assertEqual(self.buffered_display.regen_buffer[80:83], bytes.fromhex('01 02 03'))

        self.write_data_mock.assert_called_with(self.terminal.interface, bytes.fromhex('01 02 03'), jumbo_write_strategy=None)

    def test_regen_only_repeat(self):
        # Arrange
        self.buffered_display.address_counter = 80

        # Act
        self.buffered_display.write((bytes.fromhex('01 02 03'), 2), None)

        # Assert
        self.assertEqual(self.buffered_display.regen_buffer[80:86], bytes.fromhex('01 02 03 01 02 03'))

        self.write_data_mock.assert_called_with(self.terminal.interface, (bytes.fromhex('01 02 03'), 2), jumbo_write_strategy=None)

    def test_regen_eab(self):
        # Arrange
        dimensions = Dimensions(24, 80)

        self.buffered_display = BufferedDisplay(self.terminal, dimensions, 7)

        self.buffered_display._read_address_counter = Mock(wraps=self.buffered_display._read_address_counter)
        self.buffered_display._load_address_counter = Mock(wraps=self.buffered_display._load_address_counter)

        self.buffered_display.address_counter = 80

        # Act
        self.buffered_display.write(bytes.fromhex('01 02 03'), bytes.fromhex('04 05 06'))

        # Assert
        self.assertEqual(self.buffered_display.regen_buffer[80:83], bytes.fromhex('01 02 03'))
        self.assertEqual(self.buffered_display.eab_buffer[80:83], bytes.fromhex('04 05 06'))

        self.eab_write_alternate_mock.assert_called_with(self.terminal.interface, 7, bytes.fromhex('01 04 02 05 03 06'), jumbo_write_strategy=None)

    def test_regen_eab_repeat(self):
        # Arrange
        dimensions = Dimensions(24, 80)

        self.buffered_display = BufferedDisplay(self.terminal, dimensions, 7)

        self.buffered_display._read_address_counter = Mock(wraps=self.buffered_display._read_address_counter)
        self.buffered_display._load_address_counter = Mock(wraps=self.buffered_display._load_address_counter)

        self.buffered_display.address_counter = 80

        # Act
        self.buffered_display.write((bytes.fromhex('01 02 03'), 2), (bytes.fromhex('04 05 06'), 2))

        # Assert
        self.assertEqual(self.buffered_display.regen_buffer[80:86], bytes.fromhex('01 02 03 01 02 03'))
        self.assertEqual(self.buffered_display.eab_buffer[80:86], bytes.fromhex('04 05 06 04 05 06'))

        self.eab_write_alternate_mock.assert_called_with(self.terminal.interface, 7, (bytes.fromhex('01 04 02 05 03 06'), 2), jumbo_write_strategy=None)

    def test_dirty_cleared(self):
        # Arrange
        self.buffered_display.address_counter = 81

        self.buffered_display.buffered_write_byte(0x01, None, address=80)
        self.buffered_display.buffered_write_byte(0x02, None, address=81)
        self.buffered_display.buffered_write_byte(0x03, None, address=82)

        self.assertSequenceEqual(self.buffered_display.dirty, [80, 81, 82])

        # Act
        self.buffered_display.write(bytes.fromhex('02 03'), None)

        # Assert
        self.assertEqual(self.buffered_display.regen_buffer[80:83], bytes.fromhex('01 02 03'))

        self.assertSequenceEqual(self.buffered_display.dirty, [80])

class EncodeAsciiCharacterTestCase(unittest.TestCase):
    def test_mapped_character(self):
        self.assertEqual(encode_ascii_character(ord('a')), 0x80)

    def test_unmapped_character(self):
        self.assertEqual(encode_ascii_character(ord('`')), 0x00)

    def test_out_of_range(self):
        self.assertEqual(encode_ascii_character(ord('✓')), 0x00)

class EncodeEbcdicCharacterTestCase(unittest.TestCase):
    def test_mapped_character(self):
        self.assertEqual(encode_ebcdic_character(129), 0x80)

    def test_unmapped_character(self):
        self.assertEqual(encode_ebcdic_character(185), 0x00)

    def test_out_of_range(self):
        self.assertEqual(encode_ebcdic_character(256), 0x00)

class EncodeStringTestCase(unittest.TestCase):
    def test_mapped_characters(self):
        self.assertEqual(encode_string('Hello, world!'), bytes.fromhex('a7 84 8b 8b 8e 33 00 96 8e 91 8b 83 19'))

    def test_unmapped_characters(self):
        self.assertEqual(encode_string('Everything ✓'), bytes.fromhex('a4 95 84 91 98 93 87 88 8d 86 00 18'))
