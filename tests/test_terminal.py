import unittest

import context

from oec.keymap_3278_2 import KEYMAP as KEYMAP_3278_2

class TerminalGetPollActionTestCase(unittest.TestCase):
    def setUp(self):
        self.interface = Mock()

        self.terminal = Terminal(self.interface, TerminalId(0b11110100), 'c1348300', KEYMAP_3278_2)
