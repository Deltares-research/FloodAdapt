import shutil
from enum import Enum
from pathlib import Path
from shutil import rmtree
from typing import Optional

import click
import geopandas as gpd
import pandas as pd
import tomli
from hydromt_fiat.fiat import FiatModel
from hydromt_sfincs import SfincsModel
from pydantic import BaseModel, Field
from shapely.geometry import Polygon

# from flood_adapt.api.projections import create_projection
# from flood_adapt.api.startup import read_database
# from flood_adapt.api.strategies import create_strategy
from flood_adapt.object_model.interface.site import (
    EquityModel,
    RiverModel,
    UnitfulDischarge,
)

# TODO replace printing with logging


class SpatialJoinModel(BaseModel):
    name: Optional[str] = None
    file: str
    field_name: str


class AggregationModel(SpatialJoinModel):
    equity: Optional[EquityModel] = None


class UnitSystems(str, Enum):
    """class describing the accepted input for metric_system field."""

    imperial = "imperial"
    metric = "metric"


class GuiModel(BaseModel):
    unit_system: Optional[UnitSystems] = "metric"
    max_flood_depth: float
    max_aggr_dmg: float
    max_aggr_dmg: float
    max_footprint_dmg: float
    max_benefits: float


class ConfigModel(BaseModel):
    """BaseModel describing the configuration parameters."""

    name: str = Field(..., min_length=1, pattern='^[^<>:"/\\\\|?* ]*$')
    description: Optional[str] = ""
    database_path: Optional[str] = None
    sfincs: str
    sfincs_offshore: Optional[str] = None
    fiat: str
    gui: GuiModel
    building_footprints: Optional[SpatialJoinModel] = None
    bfe: Optional[SpatialJoinModel] = None
    aggregation: list[AggregationModel]
    svi: Optional[SpatialJoinModel] = None
    road_width: Optional[float] = 2.5  # in meters
    river: Optional[list[RiverModel]] = []


def read_toml(fn: str) -> dict:
    with open(fn, mode="rb") as fp:
        toml = tomli.load(fp)
    return toml


def read_config(config: str) -> ConfigModel:
    """_summary_

    Parameters
    ----------
    config : str
        _description_

    Returns
    -------
    dict
        _description_
    """
    toml = read_toml(config)
    attrs = ConfigModel.model_validate(toml)
    return attrs


class Database:
    def __init__(self, config: ConfigModel, overwrite=True):
        self.config = config
        root = Path(config.database_path).joinpath("Database", config.name)
        if root.exists() and not overwrite:
            raise ValueError(f"There is already a Database folder in '{root}'")
        else:
            rmtree(root)
            root.mkdir(parents=True)
            print(f"Initializing a FloodAdapt database in '{root}'")
        self.root = root
        self.site_attrs = {"name": config.name, "description": config.description}
        self.site_path = root.joinpath("static", "site")

    def make_folder_structure(self):
        # Prepare input folder structure
        input_path = self.root.joinpath("input")
        input_path.mkdir()
        inputs = [
            "events",
            "projections",
            "measures",
            "strategies",
            "scenarios",
            "benefits",
        ]
        for name in inputs:
            input_path.joinpath(name).mkdir()

        # Prepare static folder structure
        static_path = self.root.joinpath("static")
        static_path.mkdir()
        folders = ["templates"]
        for name in folders:
            static_path.joinpath(name).mkdir()

    def create_standard_objects(self):
        pass
        # Load database
        # dbs = read_database(self.root.parent, self.config.name)

    def read_fiat(self):
        path = self.config.fiat
        # First copy FIAT model to database
        fiat_path = self.root.joinpath("static", "templates", "fiat")
        shutil.copytree(path, fiat_path)

        # Then read the model with hydromt-FIAT
        self.fiat_model = FiatModel(root=fiat_path, mode="r+")
        self.fiat_model.read()

        # Get center of area of interest
        center = (
            self.fiat_model.exposure.exposure_geoms[0]
            .dissolve()
            .centroid.to_crs(4326)[0]
        )
        self.site_attrs["lat"] = center.y
        self.site_attrs["lon"] = center.x

        # Read FIAT attributes for site config
        self.site_attrs["fiat"] = {}
        self.site_attrs["fiat"]["floodmap_type"] = "water_level"  # for now fixed
        self.site_attrs["fiat"]["non_building_names"] = ["roads"]  #  for now fixed
        self.site_attrs["fiat"][
            "damage_unit"
        ] = "$"  # TODO This should be in the (hydromt-)FIAT model

        #
        if not self.config.building_footprints:
            rel_path = Path(
                "../templates/fiat/footprints/footprints.gpkg"
            )  # default location for footprints
            check_file = self.site_path.joinpath(
                rel_path
            ).exists()  # check if file exists
            check_col = (
                "BF_FID" in self.fiat_model.exposure.exposure_db.columns
            )  # check if it is spatially joined already
            if not check_file:
                raise ValueError(
                    "Buildings footprints path has not been provided. Please specify that by using the field 'building_footprints' in the configuration toml."
                )
            if check_file and not check_col:
                print(
                    f"Exposure csv is missing the 'BF_FID' column to connect to the footprints located at {self.site_path.joinpath(rel_path).resolve()}"
                )
                raise NotImplementedError
            if check_file and check_col:
                self.site_attrs["fiat"][
                    "building_footprints"
                ] = "../templates/fiat/footprints/footprints.gpkg"
                print(
                    f"Using the footprints located at {self.site_path.joinpath(rel_path).resolve()}"
                )
        else:
            # TODO allow for user providing a vector of footprints and do spatial join here
            raise NotImplementedError

        # TODO check how this naming of output geoms should become more explicit!
        self.site_attrs["fiat"]["roads_file_name"] = "spatial2.gpkg"
        self.site_attrs["fiat"]["new_development_file_name"] = "spatial3.gpkg"
        self.site_attrs["fiat"][
            "save_simulation"
        ] = "False"  # default is not to save simulations

        # TODO allow for user providing a vector of a base flood elevation and do spatial join here
        if self.config.bfe:
            raise NotImplementedError
        else:
            print("No base flood elevation provided.")

        # Read aggregation areas
        self.site_attrs["fiat"]["aggregation"] = []
        for aggr in self.config.aggregation:
            # Make sure paths are correct
            aggr.file = Path("../templates/fiat/").joinpath(aggr.file)
            aggr.equity.census_data = Path("../templates/fiat/").joinpath(
                aggr.equity.census_data
            )
            self.site_attrs["fiat"]["aggregation"].append(aggr)

        # Read SVI
        # TODO check how to best include SVI
        if self.config.svi:
            raise NotImplementedError

        # Make sure that FIAT roads are polygons
        # TODO this should be performed through hydromt-FIAT
        roads_path = fiat_path.joinpath("exposure", "roads.gpkg")
        roads = gpd.read_file(roads_path)

        if not isinstance(roads.geometry[0], Polygon):
            roads = roads.to_crs(roads.estimate_utm_crs())
            roads.geometry = roads.geometry.buffer(self.config.road_width, cap_style=2)
            roads = roads.to_crs(4326)
            if roads_path.exists():
                roads_path.unlink()
            roads.to_file(roads_path)
            print(
                f"FIAT road objects transformed from lines to polygons assuming a road width of {self.config.road_width} meters."
            )

    def read_sfincs(self):
        path = self.config.sfincs

        # First copy sfincs model to database
        sfincs_path = self.root.joinpath("static", "templates", "overland")
        shutil.copytree(path, sfincs_path)

        # Then read the model with hydromt-SFINCS
        self.sfincs = SfincsModel(root=sfincs_path, mode="r+")
        self.sfincs.read()

        self.site_attrs["sfincs"] = {}
        self.site_attrs["sfincs"]["csname"] = self.sfincs.crs.name
        self.site_attrs["sfincs"]["cstype"] = self.sfincs.crs.type_name.split(" ")[
            0
        ].lower()
        self.site_attrs["sfincs"]["offshore_model"] = "offshore"
        self.site_attrs["sfincs"]["overland_model"] = "overland"
        self.site_attrs["sfincs"]["floodmap_units"] = self.fiat_model.config[
            "vulnerability"
        ]["unit"]
        self.site_attrs["sfincs"]["save_simulation"] = "False"

    def read_offshore_sfincs(self):
        path = self.config.sfincs_offshore

        # First copy sfincs model to database
        sfincs_offshore_path = self.root.joinpath("static", "templates", "offshore")
        shutil.copytree(path, sfincs_offshore_path)

        # Connect boundary points of overland to output points of offshore
        fn = Path(self.sfincs.root).joinpath("sfincs.bnd")
        bnd = pd.read_csv(fn, sep=" ", lineterminator="\n", header=None)
        bnd = bnd.rename(columns={0: "x", 1: "y"})
        bnd_geo = gpd.GeoDataFrame(
            bnd,
            geometry=gpd.points_from_xy(bnd.x, bnd.y),
            crs=self.sfincs.config["epsg"],
        )
        obs_geo = bnd_geo.to_crs(4326)
        obs_geo["x"] = obs_geo.geometry.x
        obs_geo["y"] = obs_geo.geometry.y
        del obs_geo["geometry"]
        obs_geo["name"] = [f"bnd_pt{num:02d}" for num in range(1, len(obs_geo) + 1)]
        obs_geo.to_csv(
            sfincs_offshore_path.joinpath("sfincs.obs"),
            sep="\t",
            index=False,
            header=False,
        )

    def add_rivers(self):
        # TODO it should not be mandatory to have at least one "dummy" river
        if not self.config.river:
            self.site_attrs["river"] = [
                RiverModel(
                    name="dummy",
                    description="dummy river",
                    x_coordinate=0,
                    y_coordinate=0,
                    mean_discharge=UnitfulDischarge(value=0.0, units="m3/s"),
                )
            ]
        else:
            self.site_attrs["river"] = self.config.river

    def add_dem(self):
        pass

    def add_gui_params(self):
        self.site_attrs["gui"] = self.get_default_units()
        self.site_attrs["gui"]["tide_harmonic_amplitude"] = {
            "value": 0.0,
            "units": self.site_attrs["gui"]["default_length_units"],
        }
        self.site_attrs["gui"]["mapbox_layers"] = self.get_bin_colors()

    def get_default_units(self):
        type = self.config.gui.unit_system
        templates_path = Path(__file__).parent.resolve().joinpath("templates")
        default_units = read_toml(
            templates_path.joinpath("default_units", f"{type}.toml")
        )
        return default_units

    def get_bin_colors(self):
        templates_path = Path(__file__).parent.resolve().joinpath("templates")
        bin_colors = read_toml(
            templates_path.joinpath("mapbox_layers", "bin_colors.toml")
        )
        return bin_colors


@click.command()
@click.option(
    "--config_path", default="config.toml", help="Full path to the config toml file."
)
def main(config_path):
    print(f"Read FloodAdapt building configuration from {config_path}")
    config = read_config(config_path)
    if not config.database_path:
        config.database_path = str(Path(config_path).parent)

    dbs = Database(config)
    dbs.make_folder_structure()
    dbs.read_fiat()
    dbs.read_sfincs()
    if config.sfincs_offshore:
        dbs.read_offshore_sfincs()
    dbs.add_rivers()
    dbs.add_gui_params()
    dbs.create_standard_objects()


if __name__ == "__main__":
    main(["--config_path", r"c:\Users\athanasi\Github\Database\FA_builder\config.toml"])
