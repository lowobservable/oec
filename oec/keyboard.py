"""
oec.keyboard
~~~~~~~~~~~~
"""

from enum import Enum, Flag, auto
from collections import namedtuple
from collections.abc import Mapping

class KeyboardModifiers(Flag):
    """Keyboard modifiers."""
    LEFT_SHIFT = auto()
    RIGHT_SHIFT = auto()

    LEFT_ALT = auto()
    RIGHT_ALT = auto()

    CAPS_LOCK = auto()

    NONE = 0

    def is_shift(self):
        """Is either SHIFT key pressed?"""
        return bool(self & (KeyboardModifiers.LEFT_SHIFT | KeyboardModifiers.RIGHT_SHIFT))

    def is_alt(self):
        """Is either ALT key pressed?"""
        return bool(self & (KeyboardModifiers.LEFT_ALT | KeyboardModifiers.RIGHT_ALT))

    def is_caps_lock(self):
        """Is CAPS LOCK toggled on?"""
        return bool(self & KeyboardModifiers.CAPS_LOCK)

class Key(Enum):
    """Keyboad key."""

    # Modifiers
    LEFT_SHIFT = 256
    RIGHT_SHIFT = 257
    LEFT_ALT = 258
    RIGHT_ALT = 259
    CAPS_LOCK = 260

    # Cursor Movement
    SPACE = ord(' ')
    BACKSPACE = 261
    TAB = ord('\t')
    BACKTAB = 262
    NEWLINE = 263
    INSERT = 264
    DELETE = 265

    LEFT = 266
    LEFT_2 = 267
    UP = 268
    RIGHT = 269
    RIGHT_2 = 270
    DOWN = 271
    HOME = 272

    DUP = 273
    JUMP = 274

    # Function
    PF1 = 275
    PF2 = 276
    PF3 = 277
    PF4 = 278
    PF5 = 279
    PF6 = 280
    PF7 = 281
    PF8 = 282
    PF9 = 283
    PF10 = 284
    PF11 = 285
    PF12 = 286
    PF13 = 287
    PF14 = 288
    PF15 = 289
    PF16 = 290
    PF17 = 291
    PF18 = 292
    PF19 = 293
    PF20 = 294
    PF21 = 295
    PF22 = 296
    PF23 = 297
    PF24 = 298

    # Control
    ENTER = 299
    RESET = 300
    QUIT = 301
    DEVICE_CANCEL = 302

    SYS_RQ = 303
    ATTN = 304
    CLEAR = 305
    ERASE_INPUT = 306
    PRINT = 307
    TEST = 308

    FIELD_MARK = 309
    CURSOR_SELECT = 310
    CURSOR_BLINK = 311
    ERASE_EOF = 312
    CLICKER = 313
    ALT_CURSOR = 314
    IDENT = 315
    EXTEND_SELECT = 316
    CTRL = 317

    PA1 = 318
    PA2 = 319
    PA3 = 320

    # Number Pad
    NUMPAD_SEVEN = ord('7')
    NUMPAD_EIGHT = ord('8')
    NUMPAD_NINE = ord('9')
    NUMPAD_FOUR = ord('4')
    NUMPAD_FIVE = ord('5')
    NUMPAD_SIX = ord('6')
    NUMPAD_ONE = ord('1')
    NUMPAD_TWO = ord('2')
    NUMPAD_THREE = ord('3')
    NUMPAD_ZERO = ord('0')
    NUMPAD_PERIOD = ord('.')

    # Latin
    BACKTICK = ord('`')
    TILDE = ord('~')
    ONE = ord('1')
    BAR = ord('|')
    TWO = ord('2')
    AT = ord('@')
    THREE = ord('3')
    HASH = ord('#')
    FOUR = ord('4')
    DOLLAR = ord('$')
    FIVE = ord('5')
    PERCENT = ord('%')
    SIX = ord('6')
    NOT = ord('¬')
    SEVEN = ord('7')
    AMPERSAND = ord('&')
    EIGHT = ord('8')
    ASTERISK = ord('*')
    NINE = ord('9')
    LEFT_PAREN = ord('(')
    ZERO = ord('0')
    RIGHT_PAREN = ord(')')
    MINUS = ord('-')
    UNDERSCORE = ord('_')
    EQUAL = ord('=')
    PLUS = ord('+')

    LOWER_Q = ord('q')
    UPPER_Q = ord('Q')
    LOWER_W = ord('w')
    UPPER_W = ord('W')
    LOWER_E = ord('e')
    UPPER_E = ord('E')
    LOWER_R = ord('r')
    UPPER_R = ord('R')
    LOWER_T = ord('t')
    UPPER_T = ord('T')
    LOWER_Y = ord('y')
    UPPER_Y = ord('Y')
    LOWER_U = ord('u')
    UPPER_U = ord('U')
    LOWER_I = ord('i')
    UPPER_I = ord('I')
    LOWER_O = ord('o')
    UPPER_O = ord('O')
    LOWER_P = ord('p')
    UPPER_P = ord('P')
    CENT = ord('¢')
    EXCLAMATION = ord('!')
    BACKSLASH = ord('\\')
    BROKEN_BAR = ord('¦')

    LOWER_A = ord('a')
    UPPER_A = ord('A')
    LOWER_S = ord('s')
    UPPER_S = ord('S')
    LOWER_D = ord('d')
    UPPER_D = ord('D')
    LOWER_F = ord('f')
    UPPER_F = ord('F')
    LOWER_G = ord('g')
    UPPER_G = ord('G')
    LOWER_H = ord('h')
    UPPER_H = ord('H')
    LOWER_J = ord('j')
    UPPER_J = ord('J')
    LOWER_K = ord('k')
    UPPER_K = ord('K')
    LOWER_L = ord('l')
    UPPER_L = ord('L')
    SEMICOLON = ord(';')
    COLON = ord(':')
    SINGLE_QUOTE = ord('\'')
    DOUBLE_QUOTE = ord('"')
    LEFT_BRACE = ord('{')
    RIGHT_BRACE = ord('}')

    LESS = ord('<')
    GREATER = ord('>')
    LOWER_Z = ord('z')
    UPPER_Z = ord('Z')
    LOWER_X = ord('x')
    UPPER_X = ord('X')
    LOWER_C = ord('c')
    UPPER_C = ord('C')
    LOWER_V = ord('v')
    UPPER_V = ord('V')
    LOWER_B = ord('b')
    UPPER_B = ord('B')
    LOWER_N = ord('n')
    UPPER_N = ord('N')
    LOWER_M = ord('m')
    UPPER_M = ord('M')
    COMMA = ord(',')
    # APOSTOPHE?
    PERIOD = ord('.')
    CENTER_PERIOD = ord('·')
    SLASH = ord('/')
    QUESTION = ord('?')

KEY_UPPER_MAP = {
    Key.LOWER_A: Key.UPPER_A,
    Key.LOWER_B: Key.UPPER_B,
    Key.LOWER_C: Key.UPPER_C,
    Key.LOWER_D: Key.UPPER_D,
    Key.LOWER_E: Key.UPPER_E,
    Key.LOWER_F: Key.UPPER_F,
    Key.LOWER_G: Key.UPPER_G,
    Key.LOWER_H: Key.UPPER_H,
    Key.LOWER_I: Key.UPPER_I,
    Key.LOWER_J: Key.UPPER_J,
    Key.LOWER_K: Key.UPPER_K,
    Key.LOWER_L: Key.UPPER_L,
    Key.LOWER_M: Key.UPPER_M,
    Key.LOWER_N: Key.UPPER_N,
    Key.LOWER_O: Key.UPPER_O,
    Key.LOWER_P: Key.UPPER_P,
    Key.LOWER_Q: Key.UPPER_Q,
    Key.LOWER_R: Key.UPPER_R,
    Key.LOWER_S: Key.UPPER_S,
    Key.LOWER_T: Key.UPPER_T,
    Key.LOWER_U: Key.UPPER_U,
    Key.LOWER_V: Key.UPPER_V,
    Key.LOWER_W: Key.UPPER_W,
    Key.LOWER_X: Key.UPPER_X,
    Key.LOWER_Y: Key.UPPER_Y,
    Key.LOWER_Z: Key.UPPER_Z
}

KEY_LOWER_MAP = {upper_key: lower_key for lower_key, upper_key in KEY_UPPER_MAP.items()}

KEY_MODIFIER_MAP = {
    Key.LEFT_SHIFT: KeyboardModifiers.LEFT_SHIFT,
    Key.RIGHT_SHIFT: KeyboardModifiers.RIGHT_SHIFT,
    Key.LEFT_ALT: KeyboardModifiers.LEFT_ALT,
    Key.RIGHT_ALT: KeyboardModifiers.RIGHT_ALT,
    Key.CAPS_LOCK: KeyboardModifiers.CAPS_LOCK
}

MODIFIER_KEYS = set(KEY_MODIFIER_MAP.keys())

Keymap = namedtuple('Keymap', ['name', 'default', 'shift', 'alt', 'modifier_release'])

class Keyboard:
    """Keyboard state and key mapping."""

    def __init__(self, keymap):
        if keymap is None:
            raise ValueError('Keymap is required')

        self.keymap = keymap

        self.modifiers = KeyboardModifiers.NONE

        self.single_modifier_release = True

        if isinstance(self.keymap.modifier_release, Mapping):
            self.single_modifier_release = False

        self.modifier_release = False

        self.clicker = False

    def get_key(self, scan_code):
        """Map a scan code to key and update modifiers state."""
        key = self.keymap.default.get(scan_code)

        original_modifiers = self.modifiers

        (is_modifier, is_modifier_release) = self._apply_modifiers(scan_code, key)

        if is_modifier:
            return (key if not is_modifier_release else None, self.modifiers,
                    self.modifiers != original_modifiers)

        if self.modifiers.is_shift():
            key = self.keymap.shift.get(scan_code)
        elif self.modifiers.is_alt():
            key = self.keymap.alt.get(scan_code)

        if key is None:
            return (None, self.modifiers, False)

        if self.modifiers.is_caps_lock():
            if not self.modifiers.is_shift():
                key = KEY_UPPER_MAP.get(key, key)
            else:
                key = KEY_LOWER_MAP.get(key, key)

        return (key, self.modifiers, False)

    def toggle_clicker(self):
        self.clicker = not self.clicker

    def _apply_modifiers(self, scan_code, key):
        # TODO: Consider detection, in single modifier release mode, of entering
        # modififier release but the next keystroke not being a modifier... also
        # consider a warning in the case where a release of an unset modifier or
        # the setting of an already set modifier occurs.
        if self.single_modifier_release and scan_code == self.keymap.modifier_release:
            self.modifier_release = True

            return (True, None)

        if (self.single_modifier_release and self.modifier_release) or (not self.single_modifier_release and scan_code in self.keymap.modifier_release):
            self.modifier_release = False

            if self.single_modifier_release:
                released_key = key
            else:
                released_key = self.keymap.modifier_release[scan_code]

            modifier = KEY_MODIFIER_MAP.get(released_key)

            if modifier is None:
                return (False, None)

            # Ignore the release of the caps lock key as it acts as a toggle.
            if modifier.is_caps_lock():
                return (True, True)

            self.modifiers &= ~modifier

            return (True, True)

        if key in KEY_MODIFIER_MAP:
            modifier = KEY_MODIFIER_MAP[key]

            if modifier.is_caps_lock():
                self.modifiers ^= KeyboardModifiers.CAPS_LOCK
            else:
                self.modifiers |= modifier

            return (True, False)

        return (False, None)

def get_character_for_key(key):
    """Map a key to a character."""
    if not key:
        return None

    value = key.value

    if value > 255:
        return None

    return chr(value)
