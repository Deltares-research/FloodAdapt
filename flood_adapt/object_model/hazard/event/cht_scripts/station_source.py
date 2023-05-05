class StationSource:
    def __init__(self):
        pass

    def list_stations(self):
        pass

    def get_meta_data(self):
        pass

    def get_data(self):
        pass

    def source(name):
        if name == "ndbc":
            from flood_adapt.object_model.hazard.event.cht_scripts._ndbc import Source

            return Source()
        elif name == "noaa_coops":
            from flood_adapt.object_model.hazard.event.cht_scripts._noaa_coops import (
                Source,
            )

            return Source()
