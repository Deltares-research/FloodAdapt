from object_model.event import Event


class Ensemble:
    def __init__(self):
        self.name = None
        self.tomlfile = None
        self.events = [Event()]
        self.frequencies = []

    def read(self, tomlfile: str):
        pass