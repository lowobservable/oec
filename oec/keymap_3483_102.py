"""
oec.keymap_3483_102
~~~~~~~~~~~~~~~
"""

from .keyboard import Key, Keymap

# I have a 5250 keyboard for my 3483-V, this mapping is based on photographs
# of the 3270 keyboard and may not be correct.

KEYMAP_DEFAULT = {
    # Function Keys
    7: Key.PF1,
    15: Key.PF2,
    23: Key.PF3,
    31: Key.PF4,
    39: Key.PF5,
    47: Key.PF6,
    55: Key.PF7,
    63: Key.PF8,
    71: Key.PF9,
    79: Key.PF10,
    86: Key.PF11,
    94: Key.PF12,

    # Control Keys
    5: Key.ATTN,
    6: Key.CLEAR,
    4: Key.CURSOR_SELECT,
    12: None, # Pause
    3: Key.EXTEND_SELECT,
    11: Key.ERASE_EOF,
    131: Key.PRINT,
    10: None, # Play
    1: Key.PRINT,
    9: Key.CTRL,

    # First Row
    14: Key.BACKTICK,
    22: Key.ONE,
    30: Key.TWO,
    38: Key.THREE,
    37: Key.FOUR,
    46: Key.FIVE,
    54: Key.SIX,
    61: Key.SEVEN,
    62: Key.EIGHT,
    70: Key.NINE,
    69: Key.ZERO,
    78: Key.MINUS,
    85: Key.EQUAL,
    102: Key.BACKSPACE,

    # Second Row
    13: Key.TAB,
    21: Key.LOWER_Q,
    29: Key.LOWER_W,
    36: Key.LOWER_E,
    45: Key.LOWER_R,
    44: Key.LOWER_T,
    53: Key.LOWER_Y,
    60: Key.LOWER_U,
    67: Key.LOWER_I,
    68: Key.LOWER_O,
    77: Key.LOWER_P,
    84: Key.CENT,
    91: Key.BACKSLASH,
    90: Key.NEWLINE,

    # Third Row
    20: Key.CAPS_LOCK,
    28: Key.LOWER_A,
    27: Key.LOWER_S,
    35: Key.LOWER_D,
    43: Key.LOWER_F,
    52: Key.LOWER_G,
    51: Key.LOWER_H,
    59: Key.LOWER_J,
    66: Key.LOWER_K,
    75: Key.LOWER_L,
    76: Key.SEMICOLON,
    82: Key.SINGLE_QUOTE,
    83: Key.LEFT_BRACE,

    # Fourth Row
    18: Key.LEFT_SHIFT,
    19: Key.LESS,
    26: Key.LOWER_Z,
    34: Key.LOWER_X,
    33: Key.LOWER_C,
    42: Key.LOWER_V,
    50: Key.LOWER_B,
    49: Key.LOWER_N,
    58: Key.LOWER_M,
    65: Key.COMMA,
    73: Key.PERIOD,
    74: Key.SLASH,
    89: Key.RIGHT_SHIFT,

    # Bottom Row
    17: Key.RESET,
    25: Key.LEFT_ALT,
    41: Key.SPACE,
    57: Key.RIGHT_ALT,
    88: Key.ENTER,

    # Center
    103: Key.INSERT,
    110: Key.HOME,
    111: Key.JUMP,
    100: Key.DELETE,
    101: Key.ERASE_EOF,
    109: Key.DELETE,

    99: Key.UP,
    97: Key.LEFT,
    98: None, # Rule
    106: Key.RIGHT,
    96: Key.DOWN,

    # Number Pad
    118: None, # Blank
    119: None, # Blank
    126: Key.COMMA,
    132: Key.SPACE,
    108: Key.NUMPAD_SEVEN,
    117: Key.NUMPAD_EIGHT,
    125: Key.NUMPAD_NINE,
    124: Key.TAB,
    107: Key.NUMPAD_FOUR,
    115: Key.NUMPAD_FIVE,
    116: Key.NUMPAD_SIX,
    123: Key.MINUS,
    105: Key.NUMPAD_ONE,
    114: Key.NUMPAD_TWO,
    122: Key.NUMPAD_THREE,
    121: Key.ENTER,
    112: Key.NUMPAD_ZERO,
    113: Key.NUMPAD_PERIOD
}

KEYMAP_SHIFT = {
    **KEYMAP_DEFAULT,

    # Function Keys
    7: Key.PF13,
    15: Key.PF14,
    23: Key.PF15,
    31: Key.PF16,
    39: Key.PF17,
    47: Key.PF18,
    55: Key.PF19,
    63: Key.PF20,
    71: Key.PF21,
    79: Key.PF22,
    86: Key.PF23,
    94: Key.PF24,

    # Control Keys
    10: None, # Copy

    # First Row
    14: Key.TILDE,
    22: Key.BAR,
    30: Key.AT,
    38: Key.HASH,
    37: Key.DOLLAR,
    46: Key.PERCENT,
    54: Key.NOT,
    61: Key.AMPERSAND,
    62: Key.ASTERISK,
    70: Key.LEFT_PAREN,
    69: Key.RIGHT_PAREN,
    78: Key.UNDERSCORE,
    85: Key.PLUS,

    # Second Row
    13: Key.BACKTAB,
    21: Key.UPPER_Q,
    29: Key.UPPER_W,
    36: Key.UPPER_E,
    45: Key.UPPER_R,
    44: Key.UPPER_T,
    53: Key.UPPER_Y,
    60: Key.UPPER_U,
    67: Key.UPPER_I,
    68: Key.UPPER_O,
    77: Key.UPPER_P,
    84: Key.EXCLAMATION,
    91: Key.BROKEN_BAR,

    # Third Row
    28: Key.UPPER_A,
    27: Key.UPPER_S,
    35: Key.UPPER_D,
    43: Key.UPPER_F,
    52: Key.UPPER_G,
    51: Key.UPPER_H,
    59: Key.UPPER_J,
    66: Key.UPPER_K,
    75: Key.UPPER_L,
    76: Key.COLON,
    82: Key.DOUBLE_QUOTE,
    83: Key.RIGHT_BRACE,

    # Fourth Row
    19: Key.GREATER,
    26: Key.UPPER_Z,
    34: Key.UPPER_X,
    33: Key.UPPER_C,
    42: Key.UPPER_V,
    50: Key.UPPER_B,
    49: Key.UPPER_N,
    58: Key.UPPER_M,
    65: Key.COMMA, # TODO: Confirm this mapping
    73: Key.CENTER_PERIOD, # TODO: Confirm this mapping
    74: Key.QUESTION,

    # Center
    103: Key.DUP,
    110: Key.FIELD_MARK,
    111: Key.PA3,
}

KEYMAP_ALT = {
    **KEYMAP_DEFAULT,

    # Control Keys
    5: Key.SYS_RQ,
    12: Key.ERASE_INPUT,
    131: Key.IDENT,
    10: Key.TEST,

    # Center
    103: Key.PA1,
    110: Key.PA2,

    97: Key.LEFT_2,
    98: Key.HOME,
    106: Key.RIGHT_2
}

KEYMAP = Keymap('3483_102', KEYMAP_DEFAULT, KEYMAP_SHIFT, KEYMAP_ALT, modifier_release=240)
