from pathlib import Path
import pandas as pd
import geopandas as gpd

class FiatModel():
    def __init__(self, database_path: str = None):
        self.database_path = database_path
        self.exposure_file = str(Path(self.database_path, "static", "templates", "fiat", "Exposure", "exposure.csv"))
        self.exposure_file_crs = 4326  # better way to get this from excel config?
        
    def load_exposure(self):
        df = pd.read_csv(self.exposure_file, low_memory=False)
        self.exposure = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(x=df["X Coordinate"], y=df["Y Coordinate"]), crs=self.exposure_file_crs)
        return self.exposure
    
    def get_buildings(self, type=None):
        if not hasattr(self, "exposure"):
            self.load_exposure()
        buildings = self.exposure.loc[self.exposure["Primary Object Type"] != "road", :]
        if type:
            if str(type).upper() != 'ALL':
                buildings = buildings.loc[buildings["Primary Object Type"] == type, :]
            
        return buildings