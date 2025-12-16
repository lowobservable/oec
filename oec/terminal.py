"""
oec.terminal
~~~~~~~~~~~~
"""

from coax import LoadControlRegister, Feature, PollAction, Control

from .device import Device, UnsupportedDeviceError
from .display import Dimensions, BufferedDisplay
from .keyboard import Keyboard

MODEL_DIMENSIONS = {
    2: Dimensions(24, 80),
    3: Dimensions(32, 80),
    4: Dimensions(43, 80),
    5: Dimensions(27, 132)
}

class Terminal(Device):
    """The terminal."""

    def __init__(self, interface, device_address, terminal_id, extended_id, features, keymap):
        super().__init__(interface, device_address)

        self.terminal_id = terminal_id
        self.extended_id = extended_id
        self.features = features

        dimensions = MODEL_DIMENSIONS.get(terminal_id.model)

        if not dimensions:
            raise UnsupportedDeviceError(f'Terminal model {terminal_id.model} is not supported')

        self.control = Control(step_inhibit=False, display_inhibit=False,
                               cursor_inhibit=False, cursor_reverse=False,
                               cursor_blink=False)

        self.display = BufferedDisplay(self, dimensions, features.get(Feature.EAB))
        self.keyboard = Keyboard(keymap)

        self.alarm = False
        self.last_poll_keyboard_clicker = None

    def setup(self):
        """Load registers and clear the display."""
        self.load_control_register()

        if self.display.has_eab:
            self.display.load_eab_mask(0xff)

        self.display.clear(clear_status_line=True)

        # Show the attached indicator on the status line.
        self.display.status_line.write_string(0, 'OEC')

        self.display.move_cursor(row=0, column=0)

    def get_poll_action(self):
        """Get the POLL action."""
        poll_action = PollAction.NONE

        # Convert a queued alarm or keyboard clicker change to POLL action.
        if self.alarm:
            poll_action = PollAction.ALARM

            self.alarm = False
        elif self.keyboard.clicker != self.last_poll_keyboard_clicker:
            if self.keyboard.clicker:
                poll_action = PollAction.ENABLE_KEYBOARD_CLICKER
            else:
                poll_action = PollAction.DISABLE_KEYBOARD_CLICKER

            self.last_poll_keyboard_clicker = self.keyboard.clicker

        return poll_action

    def sound_alarm(self):
        """Queue an alarm on next POLL command."""
        self.alarm = True

    def load_control_register(self):
        """Execute a LOAD_CONTROL_REGISTER command."""
        self.execute(LoadControlRegister(self.control))

def get_model(terminal_id, extended_id):
    if extended_id is None:
        return None

    model = extended_id[2:6]

    # The 3179 does return an extended ID, but it does not include the model
    # like later terminals.
    if model == '0000':
        model = '3179'

    return model

def get_keyboard_description(terminal_id, extended_id):
    is_3278 = extended_id is None or not int(extended_id[0:2], 16) & 0x80

    if is_3278:
        description = '3278'

        id_map = {
            0b0001: 'APL',
            0b0010: 'TEXT',
            0b0100: 'TYPEWRITER-PSHICO',
            0b0101: 'APL',
            0b0110: 'TEXT',
            0b0111: 'APL-PSHICO',
            0b1000: 'DATAENTRY-2',
            0b1001: 'DATAENTRY-1',
            0b1010: 'TYPEWRITER',
            0b1100: 'DATAENTRY-2',
            0b1101: 'DATAENTRY-1',
            0b1110: 'TYPEWRITER'
        }

        if terminal_id.keyboard in id_map:
            description += '-' + id_map[terminal_id.keyboard]

        return description

    id_ = int(extended_id[0:2], 16) & 0x1f

    is_user = int(extended_id[0:2], 16) & 0x20

    if is_user:
        description = 'USER'

        if id_ in [1, 2, 3, 4]:
            description += f'-{id_}'

        return description

    is_ibm = not int(extended_id[6:8], 16) & 0x80

    description = 'IBM' if is_ibm else 'UNKNOWN'

    is_enhanced = int(extended_id[6:8], 16) & 0x01

    if is_enhanced:
        if id_ == 1:
            return description + '-ENHANCED'

        return None

    if id_ == 1:
        return description + '-TYPEWRITER'
    elif id_ == 2:
        return description + '-DATAENTRY'
    elif id_ == 3:
        return description + '-APL'

    return None
