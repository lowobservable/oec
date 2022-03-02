import unittest

import context

from oec.keyboard import KeyboardModifiers, Key, Keymap, Keyboard, get_character_for_key
from oec.keymap_3278_2 import KEYMAP as KEYMAP_3278_2
from oec.keymap_3483 import KEYMAP as KEYMAP_3483

class KeyboardModifiersTestCase(unittest.TestCase):
    def test_is_shift(self):
        for modifiers in [KeyboardModifiers.LEFT_SHIFT, KeyboardModifiers.RIGHT_SHIFT, KeyboardModifiers.LEFT_SHIFT | KeyboardModifiers.RIGHT_SHIFT, KeyboardModifiers.LEFT_SHIFT | KeyboardModifiers.LEFT_ALT, KeyboardModifiers.RIGHT_SHIFT | KeyboardModifiers.CAPS_LOCK]:
            with self.subTest(modifiers=input):
                self.assertTrue(modifiers.is_shift())

    def test_not_is_shift(self):
        for modifiers in [KeyboardModifiers.NONE, KeyboardModifiers.LEFT_ALT, KeyboardModifiers.RIGHT_ALT, KeyboardModifiers.CAPS_LOCK]:
            with self.subTest(modifiers=input):
                self.assertFalse(modifiers.is_shift())

    def test_is_alt(self):
        for modifiers in [KeyboardModifiers.LEFT_ALT, KeyboardModifiers.RIGHT_ALT, KeyboardModifiers.LEFT_ALT | KeyboardModifiers.RIGHT_ALT, KeyboardModifiers.LEFT_ALT | KeyboardModifiers.LEFT_SHIFT, KeyboardModifiers.RIGHT_ALT | KeyboardModifiers.CAPS_LOCK]:
            with self.subTest(modifiers=input):
                self.assertTrue(modifiers.is_alt())

    def test_not_is_alt(self):
        for modifiers in [KeyboardModifiers.NONE, KeyboardModifiers.LEFT_SHIFT, KeyboardModifiers.RIGHT_SHIFT, KeyboardModifiers.CAPS_LOCK]:
            with self.subTest(modifiers=input):
                self.assertFalse(modifiers.is_alt())

    def test_is_caps_lock(self):
        for modifiers in [KeyboardModifiers.CAPS_LOCK, KeyboardModifiers.CAPS_LOCK | KeyboardModifiers.LEFT_SHIFT, KeyboardModifiers.CAPS_LOCK | KeyboardModifiers.LEFT_ALT]:
            with self.subTest(modifiers=input):
                self.assertTrue(modifiers.is_caps_lock())

    def test_not_is_caps_lock(self):
        for modifiers in [KeyboardModifiers.NONE, KeyboardModifiers.LEFT_SHIFT, KeyboardModifiers.RIGHT_SHIFT, KeyboardModifiers.LEFT_ALT, KeyboardModifiers.RIGHT_ALT]:
            with self.subTest(modifiers=input):
                self.assertFalse(modifiers.is_caps_lock())

class KeyboardGetKeySingleModifierReleaseTestCase(unittest.TestCase):
    def setUp(self):
        self.keyboard = Keyboard(KEYMAP_3483)

    def test_single_modifier_release_is_true(self):
        self.assertTrue(self.keyboard.single_modifier_release)

    def test_default(self):
        self._assert_get_key(28, Key.LOWER_A, KeyboardModifiers.NONE, False)
        self._assert_get_key(50, Key.LOWER_B, KeyboardModifiers.NONE, False)
        self._assert_get_key(33, Key.LOWER_C, KeyboardModifiers.NONE, False)
        self._assert_get_key(35, Key.LOWER_D, KeyboardModifiers.NONE, False)

    def test_shift(self):
        self._assert_get_key(28, Key.LOWER_A, KeyboardModifiers.NONE, False)
        self._assert_get_key(18, Key.LEFT_SHIFT, KeyboardModifiers.LEFT_SHIFT, True)
        self._assert_get_key(50, Key.UPPER_B, KeyboardModifiers.LEFT_SHIFT, False)
        self._assert_get_key(89, Key.RIGHT_SHIFT, KeyboardModifiers.LEFT_SHIFT | KeyboardModifiers.RIGHT_SHIFT, True)
        self._assert_get_key(33, Key.UPPER_C, KeyboardModifiers.LEFT_SHIFT | KeyboardModifiers.RIGHT_SHIFT, False)
        self._assert_get_key(240, None, KeyboardModifiers.LEFT_SHIFT | KeyboardModifiers.RIGHT_SHIFT, False)
        self._assert_get_key(18, None, KeyboardModifiers.RIGHT_SHIFT, True)
        self._assert_get_key(35, Key.UPPER_D, KeyboardModifiers.RIGHT_SHIFT, False)
        self._assert_get_key(240, None, KeyboardModifiers.RIGHT_SHIFT, False)
        self._assert_get_key(89, None, KeyboardModifiers.NONE, True)
        self._assert_get_key(36, Key.LOWER_E, KeyboardModifiers.NONE, False)

    # TODO... include the additional ALT reset scan_code!

    def test_mapped_alt(self):
        self._assert_get_key(28, Key.LOWER_A, KeyboardModifiers.NONE, False)
        self._assert_get_key(57, Key.RIGHT_ALT, KeyboardModifiers.RIGHT_ALT, True)
        self._assert_get_key(50, Key.LOWER_B, KeyboardModifiers.RIGHT_ALT, False)
        self._assert_get_key(240, None, KeyboardModifiers.RIGHT_ALT, False)
        self._assert_get_key(57, None, KeyboardModifiers.NONE, True)
        self._assert_get_key(33, Key.LOWER_C, KeyboardModifiers.NONE, False)

    def test_unmapped_alt(self):
        self._assert_get_key(28, Key.LOWER_A, KeyboardModifiers.NONE, False)
        self._assert_get_key(57, Key.RIGHT_ALT, KeyboardModifiers.RIGHT_ALT, True)
        self._assert_get_key(50, Key.LOWER_B, KeyboardModifiers.RIGHT_ALT, False)
        self._assert_get_key(240, None, KeyboardModifiers.RIGHT_ALT, False)
        self._assert_get_key(57, None, KeyboardModifiers.NONE, True)
        self._assert_get_key(33, Key.LOWER_C, KeyboardModifiers.NONE, False)

    def test_alt_and_shift(self):
        self._assert_get_key(28, Key.LOWER_A, KeyboardModifiers.NONE, False)
        self._assert_get_key(57, Key.RIGHT_ALT, KeyboardModifiers.RIGHT_ALT, True)
        self._assert_get_key(50, Key.LOWER_B, KeyboardModifiers.RIGHT_ALT, False)
        self._assert_get_key(18, Key.LEFT_SHIFT, KeyboardModifiers.RIGHT_ALT | KeyboardModifiers.LEFT_SHIFT, True)
        self._assert_get_key(33, Key.UPPER_C, KeyboardModifiers.RIGHT_ALT | KeyboardModifiers.LEFT_SHIFT, False)
        self._assert_get_key(240, None, KeyboardModifiers.RIGHT_ALT | KeyboardModifiers.LEFT_SHIFT, False)
        self._assert_get_key(18, None, KeyboardModifiers.RIGHT_ALT, True)
        self._assert_get_key(35, Key.LOWER_D, KeyboardModifiers.RIGHT_ALT, False)
        self._assert_get_key(240, None, KeyboardModifiers.RIGHT_ALT, False)
        self._assert_get_key(57, None, KeyboardModifiers.NONE, True)
        self._assert_get_key(36, Key.LOWER_E, KeyboardModifiers.NONE, False)

    def test_caps_lock(self):
        self._assert_get_key(28, Key.LOWER_A, KeyboardModifiers.NONE, False)
        self._assert_get_key(20, Key.CAPS_LOCK, KeyboardModifiers.CAPS_LOCK, True)
        self._assert_get_key(240, None, KeyboardModifiers.CAPS_LOCK, False)
        self._assert_get_key(20, None, KeyboardModifiers.CAPS_LOCK, False)
        self._assert_get_key(50, Key.UPPER_B, KeyboardModifiers.CAPS_LOCK, False)
        self._assert_get_key(20, Key.CAPS_LOCK, KeyboardModifiers.NONE, True)
        self._assert_get_key(240, None, KeyboardModifiers.NONE, False)
        self._assert_get_key(20, None, KeyboardModifiers.NONE, False)
        self._assert_get_key(33, Key.LOWER_C, KeyboardModifiers.NONE, False)

    def test_caps_lock_and_shift(self):
        self._assert_get_key(28, Key.LOWER_A, KeyboardModifiers.NONE, False)
        self._assert_get_key(20, Key.CAPS_LOCK, KeyboardModifiers.CAPS_LOCK, True)
        self._assert_get_key(240, None, KeyboardModifiers.CAPS_LOCK, False)
        self._assert_get_key(20, None, KeyboardModifiers.CAPS_LOCK, False)
        self._assert_get_key(50, Key.UPPER_B, KeyboardModifiers.CAPS_LOCK, False)
        self._assert_get_key(18, Key.LEFT_SHIFT, KeyboardModifiers.CAPS_LOCK | KeyboardModifiers.LEFT_SHIFT, True)
        self._assert_get_key(33, Key.LOWER_C, KeyboardModifiers.CAPS_LOCK | KeyboardModifiers.LEFT_SHIFT, False)
        self._assert_get_key(240, None, KeyboardModifiers.CAPS_LOCK | KeyboardModifiers.LEFT_SHIFT, False)
        self._assert_get_key(18, None, KeyboardModifiers.CAPS_LOCK, True)
        self._assert_get_key(35, Key.UPPER_D, KeyboardModifiers.CAPS_LOCK, False)
        self._assert_get_key(20, Key.CAPS_LOCK, KeyboardModifiers.NONE, True)
        self._assert_get_key(240, None, KeyboardModifiers.NONE, False)
        self._assert_get_key(20, None, KeyboardModifiers.NONE, False)
        self._assert_get_key(36, Key.LOWER_E, KeyboardModifiers.NONE, False)
    
    def _assert_get_key(self, scan_code, key, modifiers, modifiers_changed):
        self.assertEqual(self.keyboard.get_key(scan_code), (key, modifiers, modifiers_changed))

class KeyboardGetKeyMultipleModifierReleaseTestCase(unittest.TestCase):
    def setUp(self):
        self.keyboard = Keyboard(KEYMAP_3278_2)

    def test_single_modifier_release_is_false(self):
        self.assertFalse(self.keyboard.single_modifier_release)

    def test_default(self):
        self._assert_get_key(96, Key.LOWER_A, KeyboardModifiers.NONE, False)
        self._assert_get_key(97, Key.LOWER_B, KeyboardModifiers.NONE, False)
        self._assert_get_key(98, Key.LOWER_C, KeyboardModifiers.NONE, False)
        self._assert_get_key(99, Key.LOWER_D, KeyboardModifiers.NONE, False)

    def test_shift(self):
        self._assert_get_key(96, Key.LOWER_A, KeyboardModifiers.NONE, False)
        self._assert_get_key(77, Key.LEFT_SHIFT, KeyboardModifiers.LEFT_SHIFT, True)
        self._assert_get_key(97, Key.UPPER_B, KeyboardModifiers.LEFT_SHIFT, False)
        self._assert_get_key(78, Key.RIGHT_SHIFT, KeyboardModifiers.LEFT_SHIFT | KeyboardModifiers.RIGHT_SHIFT, True)
        self._assert_get_key(98, Key.UPPER_C, KeyboardModifiers.LEFT_SHIFT | KeyboardModifiers.RIGHT_SHIFT, False)
        self._assert_get_key(205, None, KeyboardModifiers.RIGHT_SHIFT, True)
        self._assert_get_key(99, Key.UPPER_D, KeyboardModifiers.RIGHT_SHIFT, False)
        self._assert_get_key(206, None, KeyboardModifiers.NONE, True)
        self._assert_get_key(100, Key.LOWER_E, KeyboardModifiers.NONE, False)

    # TODO... include the additional ALT reset scan_code!

    def test_mapped_alt(self):
        self._assert_get_key(96, Key.LOWER_A, KeyboardModifiers.NONE, False)
        self._assert_get_key(79, Key.RIGHT_ALT, KeyboardModifiers.RIGHT_ALT, True)
        self._assert_get_key(33, Key.PF1, KeyboardModifiers.RIGHT_ALT, False)
        self._assert_get_key(207, None, KeyboardModifiers.NONE, True)
        self._assert_get_key(98, Key.LOWER_C, KeyboardModifiers.NONE, False)

    def test_unmapped_alt(self):
        self._assert_get_key(96, Key.LOWER_A, KeyboardModifiers.NONE, False)
        self._assert_get_key(79, Key.RIGHT_ALT, KeyboardModifiers.RIGHT_ALT, True)
        self._assert_get_key(97, Key.LOWER_B, KeyboardModifiers.RIGHT_ALT, False)
        self._assert_get_key(207, None, KeyboardModifiers.NONE, True)
        self._assert_get_key(98, Key.LOWER_C, KeyboardModifiers.NONE, False)

    def test_alt_and_shift(self):
        self._assert_get_key(96, Key.LOWER_A, KeyboardModifiers.NONE, False)
        self._assert_get_key(79, Key.RIGHT_ALT, KeyboardModifiers.RIGHT_ALT, True)
        self._assert_get_key(97, Key.LOWER_B, KeyboardModifiers.RIGHT_ALT, False)
        self._assert_get_key(77, Key.LEFT_SHIFT, KeyboardModifiers.RIGHT_ALT | KeyboardModifiers.LEFT_SHIFT, True)
        self._assert_get_key(98, Key.UPPER_C, KeyboardModifiers.RIGHT_ALT | KeyboardModifiers.LEFT_SHIFT, False)
        self._assert_get_key(205, None, KeyboardModifiers.RIGHT_ALT, True)
        self._assert_get_key(99, Key.LOWER_D, KeyboardModifiers.RIGHT_ALT, False)
        self._assert_get_key(207, None, KeyboardModifiers.NONE, True)
        self._assert_get_key(100, Key.LOWER_E, KeyboardModifiers.NONE, False)

    def test_caps_lock(self):
        self._assert_get_key(96, Key.LOWER_A, KeyboardModifiers.NONE, False)
        self._assert_get_key(76, Key.CAPS_LOCK, KeyboardModifiers.CAPS_LOCK, True)
        self._assert_get_key(204, None, KeyboardModifiers.CAPS_LOCK, False)
        self._assert_get_key(97, Key.UPPER_B, KeyboardModifiers.CAPS_LOCK, False)
        self._assert_get_key(76, Key.CAPS_LOCK, KeyboardModifiers.NONE, True)
        self._assert_get_key(204, None, KeyboardModifiers.NONE, False)
        self._assert_get_key(98, Key.LOWER_C, KeyboardModifiers.NONE, False)

    def test_caps_lock_and_shift(self):
        self._assert_get_key(96, Key.LOWER_A, KeyboardModifiers.NONE, False)
        self._assert_get_key(76, Key.CAPS_LOCK, KeyboardModifiers.CAPS_LOCK, True)
        self._assert_get_key(204, None, KeyboardModifiers.CAPS_LOCK, False)
        self._assert_get_key(97, Key.UPPER_B, KeyboardModifiers.CAPS_LOCK, False)
        self._assert_get_key(77, Key.LEFT_SHIFT, KeyboardModifiers.CAPS_LOCK | KeyboardModifiers.LEFT_SHIFT, True)
        self._assert_get_key(98, Key.LOWER_C, KeyboardModifiers.CAPS_LOCK | KeyboardModifiers.LEFT_SHIFT, False)
        self._assert_get_key(205, None, KeyboardModifiers.CAPS_LOCK, True)
        self._assert_get_key(99, Key.UPPER_D, KeyboardModifiers.CAPS_LOCK, False)
        self._assert_get_key(76, Key.CAPS_LOCK, KeyboardModifiers.NONE, True)
        self._assert_get_key(204, None, KeyboardModifiers.NONE, False)
        self._assert_get_key(100, Key.LOWER_E, KeyboardModifiers.NONE, False)
    
    def _assert_get_key(self, scan_code, key, modifiers, modifiers_changed):
        self.assertEqual(self.keyboard.get_key(scan_code), (key, modifiers, modifiers_changed))

class GetCharacterForKeyTestCase(unittest.TestCase):
    def test_none(self):
        self.assertIsNone(get_character_for_key(None))

    def test_no_mapping(self):
        self.assertIsNone(get_character_for_key(Key.ATTN))

    def test_mapping(self):
        self.assertEqual(get_character_for_key(Key.UPPER_A), 'A')
