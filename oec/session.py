class Session:
    def start(self):
        raise NotImplementedError

    def terminate(self):
        raise NotImplementedError

    def handle_host(self):
        raise NotImplementedError

    def handle_key(self, key, keyboard_modifiers, scan_code):
        raise NotImplementedError

class SessionDisconnectedError(Exception):
    pass
