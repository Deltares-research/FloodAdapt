from object_model.event import Event

class Synthetic(Event):
    def __init__(self):
        self.time_before_T0 = 0.
        self.time_after_T0 = 0.