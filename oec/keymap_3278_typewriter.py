"""
oec.keymap_3278_typewriter
~~~~~~~~~~~~~~~~~~~~~~~~~~
"""

from .keyboard import Key, Keymap

KEYMAP_DEFAULT = {
    # Control Keys
    80: Key.ATTN,
    81: Key.CURSOR_SELECT,
    82: None, # Blank
    83: None, # Blank
    84: Key.CURSOR_BLINK,
    85: Key.ERASE_EOF,
    86: Key.PRINT,
    87: Key.CLICKER,

    # First Row
    61: Key.BACKTICK,
    33: Key.ONE,
    34: Key.TWO,
    35: Key.THREE,
    36: Key.FOUR,
    37: Key.FIVE,
    38: Key.SIX,
    39: Key.SEVEN,
    40: Key.EIGHT,
    41: Key.NINE,
    32: Key.ZERO,
    48: Key.MINUS,
    17: Key.EQUAL,
    49: Key.BACKSPACE,

    # Second Row
    54: Key.TAB,
    112: Key.LOWER_Q,
    118: Key.LOWER_W,
    100: Key.LOWER_E,
    113: Key.LOWER_R,
    115: Key.LOWER_T,
    120: Key.LOWER_Y,
    116: Key.LOWER_U,
    104: Key.LOWER_I,
    110: Key.LOWER_O,
    111: Key.LOWER_P,
    27: Key.CENT,
    21: Key.BACKSLASH,
    53: Key.BACKTAB,

    # Third Row
    76: Key.CAPS_LOCK,
    96: Key.LOWER_A,
    114: Key.LOWER_S,
    99: Key.LOWER_D,
    101: Key.LOWER_F,
    102: Key.LOWER_G,
    103: Key.LOWER_H,
    105: Key.LOWER_J,
    106: Key.LOWER_K,
    107: Key.LOWER_L,
    126: Key.SEMICOLON,
    18: Key.SINGLE_QUOTE,
    15: Key.LEFT_BRACE,
    8: Key.NEWLINE,

    # Fourth Row
    77: Key.LEFT_SHIFT,
    9: Key.LESS,
    121: Key.LOWER_Z,
    119: Key.LOWER_X,
    98: Key.LOWER_C,
    117: Key.LOWER_V,
    97: Key.LOWER_B,
    109: Key.LOWER_N,
    108: Key.LOWER_M,
    51: Key.COMMA,
    50: Key.PERIOD,
    20: Key.SLASH,
    78: Key.RIGHT_SHIFT,

    # Bottom Row
    52: Key.RESET,
    16: Key.SPACE,
    79: Key.RIGHT_ALT,
    24: Key.ENTER,

    # Right
    95: Key.DUP,
    94: Key.FIELD_MARK,
    12: Key.INSERT,
    13: Key.DELETE,
    14: Key.UP,
    19: Key.DOWN,
    22: Key.LEFT,
    26: Key.RIGHT
}

KEYMAP_SHIFT = {
    **KEYMAP_DEFAULT,

    # First Row
    61: Key.TILDE,
    33: Key.BAR,
    34: Key.AT,
    35: Key.HASH,
    36: Key.DOLLAR,
    37: Key.PERCENT,
    38: Key.NOT,
    39: Key.AMPERSAND,
    40: Key.ASTERISK,
    41: Key.LEFT_PAREN,
    32: Key.RIGHT_PAREN,
    48: Key.UNDERSCORE,
    17: Key.PLUS,

    # Second Row
    112: Key.UPPER_Q,
    118: Key.UPPER_W,
    100: Key.UPPER_E,
    113: Key.UPPER_R,
    115: Key.UPPER_T,
    120: Key.UPPER_Y,
    116: Key.UPPER_U,
    104: Key.UPPER_I,
    110: Key.UPPER_O,
    111: Key.UPPER_P,
    27: Key.EXCLAMATION,
    21: Key.BROKEN_BAR,

    # Third Row
    96: Key.UPPER_A,
    114: Key.UPPER_S,
    99: Key.UPPER_D,
    101: Key.UPPER_F,
    102: Key.UPPER_G,
    103: Key.UPPER_H,
    105: Key.UPPER_J,
    106: Key.UPPER_K,
    107: Key.UPPER_L,
    126: Key.COLON,
    18: Key.DOUBLE_QUOTE,
    15: Key.RIGHT_BRACE,

    # Fourth Row
    9: Key.GREATER,
    121: Key.UPPER_Z,
    119: Key.UPPER_X,
    98: Key.UPPER_C,
    117: Key.UPPER_V,
    97: Key.UPPER_B,
    109: Key.UPPER_N,
    108: Key.UPPER_M,
    51: Key.COMMA, # TODO: Confirm this mapping
    50: Key.CENTER_PERIOD,
    20: Key.QUESTION
}

KEYMAP_ALT = {
    **KEYMAP_DEFAULT,

    # Control Keys
    80: Key.SYS_RQ,
    81: Key.CLEAR,
    83: Key.ERASE_INPUT,
    84: Key.ALT_CURSOR,
    86: Key.IDENT,
    87: Key.TEST,

    # First Row
    33: Key.PF1,
    34: Key.PF2,
    35: Key.PF3,
    36: Key.PF4,
    37: Key.PF5,
    38: Key.PF6,
    39: Key.PF7,
    40: Key.PF8,
    41: Key.PF9,
    32: Key.PF10,
    48: Key.PF11,
    17: Key.PF12,

    # Second Row
    53: Key.HOME,

    # Right
    95: Key.PA1,
    94: Key.PA2,
    22: Key.LEFT_2,
    26: Key.RIGHT_2
}

MODIFIER_RELEASE_MAP = {
    204: Key.CAPS_LOCK,
    205: Key.LEFT_SHIFT,
    206: Key.RIGHT_SHIFT,
    207: Key.RIGHT_ALT
}

KEYMAP = Keymap('3278 Typewriter', KEYMAP_DEFAULT, KEYMAP_SHIFT, KEYMAP_ALT, MODIFIER_RELEASE_MAP)
