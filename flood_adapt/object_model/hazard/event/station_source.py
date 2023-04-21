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
        from _ndbc import Source
        return Source()
    elif name == "noaa_coops":
        from _noaa_coops import Source
        return Source()