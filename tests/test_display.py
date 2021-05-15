import unittest
from unittest.mock import Mock, patch

import context

from oec.display import Dimensions, Display, encode_ascii_character, encode_ebcdic_character, encode_string

class DisplayMoveCursorTestCase(unittest.TestCase):
    def setUp(self):
        self.interface = Mock()

        dimensions = Dimensions(24, 80)

        self.display = Display(self.interface, dimensions, None)

        self.display._load_address_counter = Mock(wraps=self.display._load_address_counter)

        patcher = patch('oec.display.load_address_counter_hi')

        self.load_address_counter_hi_mock = patcher.start()

        patcher = patch('oec.display.load_address_counter_lo')

        self.load_address_counter_lo_mock = patcher.start()

        self.addCleanup(patch.stopall)

    def test(self):
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

class DisplayBufferedWriteTestCase(unittest.TestCase):
    def setUp(self):
        self.interface = Mock()

        dimensions = Dimensions(24, 80)

        self.display = Display(self.interface, Dimensions(24, 80), None)

    def test_with_no_eab(self):
        # Act
        self.display.buffered_write(0x01, 0x00, index=15)
        self.display.buffered_write(0x02, 0x00, index=97)
        self.display.buffered_write(0x00, 0x01, index=98)

        # Assert
        self.assertEqual(self.display.regen_buffer[15], 0x01)
        self.assertEqual(self.display.regen_buffer[97], 0x02)
        self.assertEqual(self.display.eab_buffer[98], 0x00)
        self.assertSequenceEqual(self.display.dirty, [15, 97])

    def test_with_eab(self):
        # Arrange
        self.display.eab_address = 7

        # Act
        self.display.buffered_write(0x01, 0x00, index=15)
        self.display.buffered_write(0x02, 0x00, index=97)
        self.display.buffered_write(0x00, 0x01, index=98)

        # Assert
        self.assertEqual(self.display.regen_buffer[15], 0x01)
        self.assertEqual(self.display.regen_buffer[97], 0x02)
        self.assertEqual(self.display.eab_buffer[98], 0x01)
        self.assertSequenceEqual(self.display.dirty, [15, 97, 98])

    def test_with_row_and_column(self):
        # Act
        self.display.buffered_write(0x01, 0x00, row=0, column=15)
        self.display.buffered_write(0x02, 0x00, row=1, column=17)

        # Assert
        self.assertEqual(self.display.regen_buffer[15], 0x01)
        self.assertEqual(self.display.regen_buffer[97], 0x02)
        self.assertSequenceEqual(self.display.dirty, [15, 97])

    def test_change(self):
        self.assertTrue(self.display.buffered_write(0x01, 0x00, index=0))
        self.assertTrue(self.display.buffered_write(0x02, 0x00, index=0))

        self.assertEqual(self.display.regen_buffer[0], 0x02)
        self.assertSequenceEqual(self.display.dirty, [0])

    def test_no_change(self):
        self.assertTrue(self.display.buffered_write(0x01, 0x00, index=0))
        self.assertFalse(self.display.buffered_write(0x01, 0x00, index=0))

        self.assertEqual(self.display.regen_buffer[0], 0x01)
        self.assertSequenceEqual(self.display.dirty, [0])

class DisplayFlushTestCase(unittest.TestCase):
    def setUp(self):
        self.interface = Mock()

        dimensions = Dimensions(24, 80)

        self.display = Display(self.interface, dimensions, None)

        self.display._flush_range = Mock()

    def test_no_changes(self):
        # Act
        self.display.flush()

        # Assert
        self.display._flush_range.assert_not_called()

    def test_single_range_with_no_eab(self):
        # Arrange
        self.display.buffered_write(0x01, 0x00, index=0)
        self.display.buffered_write(0x02, 0x00, index=1)
        self.display.buffered_write(0x03, 0x00, index=2)
        self.display.buffered_write(0x00, 0x01, index=3)

        # Act
        self.display.flush()

        # Assert
        self.display._flush_range.assert_called_with(0, 2)

    def test_single_range_with_eab(self):
        # Arrange
        self.display.eab_address = 7

        self.display.buffered_write(0x01, 0x00, index=0)
        self.display.buffered_write(0x02, 0x00, index=1)
        self.display.buffered_write(0x03, 0x00, index=2)
        self.display.buffered_write(0x00, 0x01, index=3)

        # Act
        self.display.flush()

        # Assert
        self.display._flush_range.assert_called_with(0, 3)

    def test_multiple_ranges_with_no_eab(self):
        # Arrange
        self.display.buffered_write(0x01, 0x00, index=0)
        self.display.buffered_write(0x02, 0x00, index=1)
        self.display.buffered_write(0x03, 0x01, index=2)
        self.display.buffered_write(0x00, 0x02, index=3)
        self.display.buffered_write(0x05, 0x00, index=30)
        self.display.buffered_write(0x06, 0x00, index=31)
        self.display.buffered_write(0x00, 0x05, index=32)
        self.display.buffered_write(0x04, 0x03, index=20)
        self.display.buffered_write(0x00, 0x04, index=21)

        # Act
        self.display.flush()

        # Assert
        self.display._flush_range.assert_called_with(0, 31)

    def test_multiple_ranges_with_no_eab(self):
        # Arrange
        self.display.eab_address = 7

        self.display.buffered_write(0x01, 0x00, index=0)
        self.display.buffered_write(0x02, 0x00, index=1)
        self.display.buffered_write(0x03, 0x01, index=2)
        self.display.buffered_write(0x00, 0x02, index=3)
        self.display.buffered_write(0x05, 0x00, index=30)
        self.display.buffered_write(0x06, 0x00, index=31)
        self.display.buffered_write(0x00, 0x05, index=32)
        self.display.buffered_write(0x04, 0x03, index=20)
        self.display.buffered_write(0x00, 0x04, index=21)

        # Act
        self.display.flush()

        # Assert
        self.display._flush_range.assert_called_with(0, 32)

class DisplayClearTestCase(unittest.TestCase):
    def setUp(self):
        self.interface = Mock()

        dimensions = Dimensions(24, 80)

        self.display = Display(self.interface, dimensions, None)

        self.display._load_address_counter = Mock(wraps=self.display._load_address_counter)
        self.display._write = Mock(wraps=self.display._write)

        patcher = patch('oec.display.load_address_counter_hi')

        self.load_address_counter_hi_mock = patcher.start()

        patcher = patch('oec.display.load_address_counter_lo')

        self.load_address_counter_lo_mock = patcher.start()

        patcher = patch('oec.display.write_data')

        self.write_data_mock = patcher.start()

        patcher = patch('oec.display.eab_write_alternate')

        self.eab_write_alternate_mock = patcher.start()

        self.addCleanup(patch.stopall)

    def test_excluding_status_line_with_no_eab(self):
        # Arrange
        self.display.buffered_write(0x01, 0x01, index=0)

        self.assertEqual(self.display.regen_buffer[0], 0x01)
        self.assertEqual(self.display.eab_buffer[0], 0x00)
        self.assertTrue(self.display.dirty)

        # Act
        self.display.clear(clear_status_line=False)

        # Assert
        self.display._write.assert_called_with((b'\x00', 1920), None, address=80)
        self.display._load_address_counter.assert_called_with(80, True)

        self.assertEqual(self.display.regen_buffer[0], 0x00)
        self.assertEqual(self.display.eab_buffer[0], 0x00)
        self.assertFalse(self.display.dirty)

    def test_excluding_status_line_with_eab(self):
        # Arrange
        self.display.eab_address = 7

        self.display.buffered_write(0x01, 0x01, index=0)

        self.assertEqual(self.display.regen_buffer[0], 0x01)
        self.assertEqual(self.display.eab_buffer[0], 0x01)
        self.assertTrue(self.display.dirty)

        # Act
        self.display.clear(clear_status_line=False)

        # Assert
        self.display._write.assert_called_with((b'\x00', 1920), (b'\x00', 1920), address=80)
        self.display._load_address_counter.assert_called_with(80, True)

        self.assertEqual(self.display.regen_buffer[0], 0x00)
        self.assertEqual(self.display.eab_buffer[0], 0x00)
        self.assertFalse(self.display.dirty)

    def test_including_status_line_with_no_eab(self):
        # Arrange
        self.display.buffered_write(0x01, 0x01, index=0)

        self.assertEqual(self.display.regen_buffer[0], 0x01)
        self.assertEqual(self.display.eab_buffer[0], 0x00)
        self.assertTrue(self.display.dirty)

        # Act
        self.display.clear(clear_status_line=True)

        # Assert
        self.display._write.assert_called_with((b'\x00', 2000), None, address=0)
        self.display._load_address_counter.assert_called_with(80, True)

        self.assertEqual(self.display.regen_buffer[0], 0x00)
        self.assertEqual(self.display.eab_buffer[0], 0x00)
        self.assertFalse(self.display.dirty)

    def test_including_status_line_with_eab(self):
        # Arrange
        self.display.eab_address = 7

        self.display.buffered_write(0x01, 0x01, index=0)

        self.assertEqual(self.display.regen_buffer[0], 0x01)
        self.assertEqual(self.display.eab_buffer[0], 0x01)
        self.assertTrue(self.display.dirty)

        # Act
        self.display.clear(clear_status_line=True)

        # Assert
        self.display._write.assert_called_with((b'\x00', 2000), (b'\x00', 2000), address=0)
        self.display._load_address_counter.assert_called_with(80, True)

        self.assertEqual(self.display.regen_buffer[0], 0x00)
        self.assertEqual(self.display.eab_buffer[0], 0x00)
        self.assertFalse(self.display.dirty)

class DisplayFlushRangeTestCase(unittest.TestCase):
    def setUp(self):
        self.interface = Mock()

        dimensions = Dimensions(24, 80)

        self.display = Display(self.interface, dimensions, None)

        self.display._write = Mock(wraps=self.display._write)

        patcher = patch('oec.display.load_address_counter_hi')

        self.load_address_counter_hi_mock = patcher.start()

        patcher = patch('oec.display.load_address_counter_lo')

        self.load_address_counter_lo_mock = patcher.start()

        patcher = patch('oec.display.write_data')

        self.write_data_mock = patcher.start()

        self.addCleanup(patch.stopall)

    def test_when_start_address_is_current_address_counter(self):
        # Arrange
        self.display.move_cursor(index=0)

        self.display.buffered_write(0x01, 0x00, index=0)
        self.display.buffered_write(0x02, 0x00, index=1)
        self.display.buffered_write(0x03, 0x00, index=2)

        # Act
        self.display.flush()

        # Assert
        self.display._write.assert_called_with(bytes.fromhex('01 02 03'), None, address=80)

        self.assertEqual(self.display.address_counter, 83)
        self.assertFalse(self.display.dirty)

    def test_when_start_address_is_not_current_address_counter(self):
        # Arrange
        self.display.move_cursor(index=70)

        self.display.buffered_write(0x01, 0x00, index=0)
        self.display.buffered_write(0x02, 0x00, index=1)
        self.display.buffered_write(0x03, 0x00, index=2)

        # Act
        self.display.flush()

        # Assert
        self.display._write.assert_called_with(bytes.fromhex('01 02 03'), None, address=80)

        self.assertEqual(self.display.address_counter, 83)
        self.assertFalse(self.display.dirty)

class DisplayLoadAddressCounterTestCase(unittest.TestCase):
    def setUp(self):
        self.interface = Mock()

        dimensions = Dimensions(24, 80)

        self.display = Display(self.interface, dimensions, None)

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

        self.load_address_counter_hi_mock.assert_called_with(self.interface, 3)
        self.load_address_counter_lo_mock.assert_called_with(self.interface, 127)

    def test_hi_change(self):
        # Arrange
        self.display._load_address_counter(895, force_load=False)

        self.load_address_counter_hi_mock.reset_mock()
        self.load_address_counter_lo_mock.reset_mock()

        # Act
        self.display._load_address_counter(1151, force_load=False)

        # Assert
        self.assertEqual(self.display.address_counter, 1151)

        self.load_address_counter_hi_mock.assert_called_with(self.interface, 4)
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
        self.load_address_counter_lo_mock.assert_called_with(self.interface, 128)

    def test_hi_lo_change(self):
        # Arrange
        self.display._load_address_counter(895, force_load=False)

        self.load_address_counter_hi_mock.reset_mock()
        self.load_address_counter_lo_mock.reset_mock()

        # Act
        self.display._load_address_counter(1152, force_load=False)

        # Assert
        self.assertEqual(self.display.address_counter, 1152)

        self.load_address_counter_hi_mock.assert_called_with(self.interface, 4)
        self.load_address_counter_lo_mock.assert_called_with(self.interface, 128)

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

        self.load_address_counter_hi_mock.assert_called_with(self.interface, 0)
        self.load_address_counter_lo_mock.assert_called_with(self.interface, 80)

class DisplayWriteTestCase(unittest.TestCase):
    def setUp(self):
        self.interface = Mock()

        dimensions = Dimensions(24, 80)

        self.display = Display(self.interface, dimensions, None)

        self.display._load_address_counter = Mock(wraps=self.display._load_address_counter)

        patcher = patch('oec.display.load_address_counter_hi')

        self.load_address_counter_hi_mock = patcher.start()

        patcher = patch('oec.display.load_address_counter_lo')

        self.load_address_counter_lo_mock = patcher.start()

        patcher = patch('oec.display.write_data')

        self.write_data_mock = patcher.start()

        patcher = patch('oec.display.eab_write_alternate')

        self.eab_write_alternate_mock = patcher.start()

        self.addCleanup(patch.stopall)

    def test_with_no_eab_data(self):
        # Act
        self.display._write(bytes.fromhex('01 02 03'), None)

        # Assert
        self.assertIsNone(self.display.address_counter)

        self.write_data_mock.assert_called_with(self.interface, bytes.fromhex('01 02 03'), jumbo_write_strategy=None)

    def test_with_eab_data(self):
        # Arrange
        self.display.eab_address = 7

        # Act
        self.display._write(bytes.fromhex('01 02 03'), bytes.fromhex('04 05 06'))

        # Assert
        self.assertIsNone(self.display.address_counter)

        self.eab_write_alternate_mock.assert_called_with(self.interface, 7, bytes.fromhex('01 04 02 05 03 06'), jumbo_write_strategy=None)

    def test_repeat_with_no_eab_data(self):
        # Act
        self.display._write((bytes.fromhex('01 02 03'), 3), None)

        # Assert
        self.assertIsNone(self.display.address_counter)

        self.write_data_mock.assert_called_with(self.interface, (bytes.fromhex('01 02 03'), 3), jumbo_write_strategy=None)

    def test_repeat_with_eab_data(self):
        # Arrange
        self.display.eab_address = 7

        # Act
        self.display._write((bytes.fromhex('01 02 03'), 3), (bytes.fromhex('04 05 06'), 3))

        # Assert
        self.assertIsNone(self.display.address_counter)

        self.eab_write_alternate_mock.assert_called_with(self.interface, 7, (bytes.fromhex('01 04 02 05 03 06'), 3), jumbo_write_strategy=None)

    def test_regen_eab_data_mismatch_format(self):
        # Arrange
        self.display.eab_address = 7

        # Act and assert
        with self.assertRaisesRegex(ValueError, 'must be provided in same form'):
            self.display._write(bytes.fromhex('01 02 03'), (b'\x00', 3))

    def test_regen_eab_data_mismatch_length(self):
        # Arrange
        self.display.eab_address = 7

        # Act and assert
        with self.assertRaisesRegex(ValueError, 'data length must be equal'):
            self.display._write(bytes.fromhex('01 02 03'), bytes.fromhex('01 02'))

    def test_regen_eab_data_mismatch_length_repeat(self):
        # Arrange
        self.display.eab_address = 7

        # Act and assert
        with self.assertRaisesRegex(ValueError, 'pattern length must be equal'):
            self.display._write((bytes.fromhex('01 02 03'), 3), (b'\x00', 2))

    def test_address_if_current_address_unknown(self):
        # Arrange
        self.assertIsNone(self.display.address_counter)

        # Act
        self.display._write(bytes.fromhex('01 02 03'), None, address=80)

        # Assert
        self.assertEqual(self.display.address_counter, 83)

    def test_address_if_change(self):
        # Arrange
        self.display.address_counter = 160

        # Act
        self.display._write(bytes.fromhex('01 02 03'), None, address=80)

        # Assert
        self.assertEqual(self.display.address_counter, 83)

        self.display._load_address_counter.assert_called_with(80, force_load=False)

    def test_address_if_no_change(self):
        # Arrange
        self.display.address_counter = 80

        # Act
        self.display._write(bytes.fromhex('01 02 03'), None, address=80)

        # Assert
        self.assertEqual(self.display.address_counter, 83)

        self.display._load_address_counter.assert_called_with(80, force_load=False)

    def test_restore_original_address_if_current_address_unknown(self):
        # Arrange
        self.display._read_address_counter = Mock(return_value=160)

        self.assertIsNone(self.display.address_counter)

        # Act
        self.display._write(bytes.fromhex('01 02 03'), None, restore_original_address=True)

        # Assert
        self.assertEqual(self.display.address_counter, 160)

    def test_restore_original_address_if_current_address_known(self):
        # Arrange
        self.display._read_address_counter = Mock(return_value=160)

        self.display.address_counter = 160

        # Act
        self.display._write(bytes.fromhex('01 02 03'), None, restore_original_address=True)

        # Assert
        self.assertEqual(self.display.address_counter, 160)

        self.display._read_address_counter.assert_not_called()

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
