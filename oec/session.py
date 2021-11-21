class Session:
    def __init__(self, terminal):
        self.terminal = terminal

    def start(self):
        raise NotImplementedError

    def terminate(self):
        raise NotImplementedError

    def fileno(self):
        raise NotImplementedError

    def handle_host(self):
        raise NotImplementedError

    def handle_key(self, key, keyboard_modifiers, scan_code):
        raise NotImplementedError

    def render(self):
        raise NotImplementedError

class SessionDisconnectedError(Exception):
    pass
