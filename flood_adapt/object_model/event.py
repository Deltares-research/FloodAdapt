class Event:
    def __init__(self):
        self.name = None
        self.tomlfile = None

    def read(self, tomlfile: str):
        pass

    def write(self, tomlfile: str):
        pass

    def generate_timeseries(self, tomlfile: str):
        pass