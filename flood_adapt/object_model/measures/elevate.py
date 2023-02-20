from flood_adapt.object_model.measures.measure import Measure

class Elevate(Measure):
    def __init__(self, config_path) -> None:
        super().__init__(config_path)