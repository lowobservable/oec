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
