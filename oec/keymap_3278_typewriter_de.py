"""
oec.keymap_3278_typewriter_de
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
"""

from .keyboard import Key, Keymap
from .keymap_3278_typewriter import KEYMAP_DEFAULT as _US_DEFAULT, KEYMAP_SHIFT as _US_SHIFT, \
                                    KEYMAP_ALT, MODIFIER_RELEASE_MAP

KEYMAP_DEFAULT = {
    **_US_DEFAULT,

    # First Row
    48: Key.ESZETT,         # was MINUS
    17: Key.SINGLE_QUOTE,   # was EQUAL

    # Second Row
    120: Key.LOWER_Z,        # was LOWER_Y
    27: Key.LOWER_U_UMLAUT, # was CENT
    21: Key.PLUS,            # was BACKSLASH

    # Third Row
    126: Key.LOWER_O_UMLAUT, # was SEMICOLON
    18: Key.LOWER_A_UMLAUT,  # was SINGLE_QUOTE
    15: Key.HASH,            # was LEFT_BRACE

    # Fourth Row
    121: Key.LOWER_Y,  # was LOWER_Z
    51: Key.COMMA,  # unchanged
    50: Key.PERIOD, # unchanged
    20: Key.MINUS,  # was SLASH
}

KEYMAP_SHIFT = {
    **_US_SHIFT,

    # First Row - number row
    33: Key.EXCLAMATION,  # was BAR
    34: Key.DOUBLE_QUOTE, # was AT
    35: Key.SECTION,      # was HASH
    38: Key.AMPERSAND,    # was NOT
    39: Key.SLASH,        # was AMPERSAND
    40: Key.LEFT_PAREN,   # was ASTERISK
    41: Key.RIGHT_PAREN,  # was LEFT_PAREN
    32: Key.EQUAL,        # was RIGHT_PAREN
    48: Key.QUESTION,     # was UNDERSCORE
    17: Key.BACKTICK,     # was PLUS

    # Second Row
    120: Key.UPPER_Z,        # was UPPER_Y
    27: Key.UPPER_U_UMLAUT, # was EXCLAMATION
    21: Key.ASTERISK,       # was BROKEN_BAR

    # Third Row
    126: Key.UPPER_O_UMLAUT, # was COLON
    18: Key.UPPER_A_UMLAUT,  # was DOUBLE_QUOTE
    15: Key.CARET,           # was RIGHT_BRACE

    # Fourth Row
    121: Key.UPPER_Y,    # was UPPER_Z
    51: Key.SEMICOLON,  # was COMMA
    50: Key.COLON,      # was CENTER_PERIOD
    20: Key.UNDERSCORE, # was QUESTION
}

KEYMAP = Keymap('3278 Typewriter (DE)', KEYMAP_DEFAULT, KEYMAP_SHIFT, KEYMAP_ALT, MODIFIER_RELEASE_MAP)
