import logging
import shutil
from enum import Enum
from pathlib import Path
from shutil import rmtree
from typing import Optional
from urllib.request import urlretrieve

import click
import geopandas as gpd
import pandas as pd
import tomli
import tomli_w
from hydromt_fiat.fiat import FiatModel
from hydromt_sfincs import SfincsModel
from pydantic import BaseModel, Field
from shapely.geometry import Polygon

from flood_adapt.api.projections import create_projection, save_projection
from flood_adapt.api.startup import read_database
from flood_adapt.api.strategies import create_strategy, save_strategy
from flood_adapt.object_model.interface.site import (
    EquityModel,
    Obs_pointModel,
    RiverModel,
    UnitfulDischarge,
)
from flood_adapt.object_model.site import Site


def logger(log_path):
    # Create a root logger and set the minimum logging level.
    logger = logging.getLogger("FloodAdapt")
    logger.setLevel(logging.INFO)
    # Create a file handler and set the required logging level.
    fh = logging.FileHandler(filename=log_path, mode="w")
    fh.setLevel(logging.DEBUG)

    # Create a console handler and set the required logging level.
    ch = logging.StreamHandler()
    ch.setLevel(logging.WARNING)  # Can be also set to WARNING

    # Create a formatter and add to the file and console handlers.
    formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %I:%M:%S %p",
    )
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)

    # Add the file and console handlers to the root logger.
    logger.addHandler(fh)
    logger.addHandler(ch)

    return logger


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


class Basins(str, Enum):
    """class describing the accepted input for metric_system field."""

    NA = "NA"  # North Atlantic
    SA = "SA"  # South Atlantic
    EP = "EP"  # Eastern North Pacific (which includes the Central Pacific region)
    WP = "WP"  # Western North Pacific
    SP = "SP"  # South Pacific
    SI = "SI"  # South Indian
    NI = "NI"  # North Indian


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
    # Impact
    building_footprints: Optional[SpatialJoinModel] = None
    bfe: Optional[SpatialJoinModel] = None
    aggregation: list[AggregationModel]
    svi: Optional[SpatialJoinModel] = None
    road_width: Optional[float] = 2.5  # in meters
    # Hazard
    cyclone_basin: Optional[Basins] = None
    river: Optional[list[RiverModel]] = []
    obs_point: Optional[list[Obs_pointModel]] = []


def read_toml(fn: str) -> dict:
    with open(fn, mode="rb") as fp:
        toml = tomli.load(fp)
    return toml


def read_config(config: str) -> ConfigModel:
    toml = read_toml(config)
    attrs = ConfigModel.model_validate(toml)
    return attrs


class Database:
    def __init__(self, config: ConfigModel, overwrite=True):
        self.config = config
        root = Path(config.database_path).joinpath(config.name)

        if root.exists() and not overwrite:
            raise ValueError(f"There is already a Database folder in '{root}'")
        if root.exists() and overwrite:
            rmtree(root)
        root.mkdir(parents=True)

        self.logger = logger(root.joinpath("floodadapt_builder.log"))

        self.logger.info(f"Initializing a FloodAdapt database in '{root}'")
        self.root = root
        self.site_attrs = {"name": config.name, "description": config.description}
        self.site_path = root.joinpath("static", "site")

    def make_folder_structure(self):
        self.logger.info("Preparing the database folder structure.")
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
        # Load database
        dbs = read_database(self.root.parent, self.config.name)

        strategy = create_strategy({"name": "no_measures", "measures": []}, dbs)
        save_strategy(strategy, dbs)

        projection = create_projection(
            {
                "name": "current",
                "physical_projection": {},
                "socio_economic_change": {},
            }
        )
        save_projection(projection, dbs)

    def read_fiat(self):
        path = self.config.fiat
        self.logger.info(f"Reading in FIAT model from {path}")
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
        self.site_attrs["fiat"]["exposure_crs"] = self.fiat_model.exposure.crs
        self.site_attrs["fiat"]["floodmap_type"] = "water_level"  # for now fixed
        self.site_attrs["fiat"]["non_building_names"] = ["roads"]  #  for now fixed
        self.site_attrs["fiat"][
            "damage_unit"
        ] = "$"  # TODO This should be in the (hydromt-)FIAT model

        # TODO make footprints an optional argument and use points as the minimum default spatial description
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
                self.logger.info(
                    f"Exposure csv is missing the 'BF_FID' column to connect to the footprints located at {self.site_path.joinpath(rel_path).resolve()}"
                )
                raise NotImplementedError
            if check_file and check_col:
                self.site_attrs["fiat"][
                    "building_footprints"
                ] = "../templates/fiat/footprints/footprints.gpkg"
                self.logger.info(
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
            self.logger.info("No base flood elevation provided.")

        # Read aggregation areas
        self.site_attrs["fiat"]["aggregation"] = []
        for aggr in self.config.aggregation:
            # Make sure paths are correct
            aggr.file = str(Path("../templates/fiat/").joinpath(aggr.file))
            aggr.equity.census_data = str(
                Path("../templates/fiat/").joinpath(aggr.equity.census_data)
            )
            self.site_attrs["fiat"]["aggregation"].append(aggr.model_dump())

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
            self.logger.info(
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
        self.site_attrs["sfincs"][
            "ambient_air_pressure"
        ] = 102000  # TODO this is not used anywhere
        fiat_units = self.fiat_model.config["vulnerability"]["unit"]
        if fiat_units == "ft":
            fiat_units = "feet"
        self.site_attrs["sfincs"]["floodmap_units"] = fiat_units
        self.site_attrs["sfincs"]["save_simulation"] = "False"

    def read_offshore_sfincs(self):
        path = self.config.sfincs_offshore
        # TODO check if extents of offshore cover overland
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
        # TODO if files not found in SFINCS model, user can provide them!
        tiles_sfincs = Path(self.sfincs.root).joinpath("tiles")
        if tiles_sfincs.exists():
            fa_path1 = self.root.joinpath("static", "dem", "tiles")
            shutil.move(tiles_sfincs, fa_path1)
        fn = "dep_subgrid.tif"
        subgrid_sfincs = Path(self.sfincs.root).joinpath("subgrid", fn)
        if subgrid_sfincs.exists():
            fa_path2 = self.root.joinpath("static", "dem", fn)
            shutil.move(subgrid_sfincs, fa_path2)
        self.site_attrs["dem"] = {}
        self.site_attrs["dem"]["filename"] = fn
        self.site_attrs["dem"][
            "units"
        ] = "meters"  # This is always in meters from SFINCS

    def add_cyclone_dbs(self):
        if self.config.cyclone_basin:
            basin = self.config.cyclone_basin
        else:
            basin = "ALL"
        name = f"IBTrACS.{basin}.v04r00.nc"
        url = f"https://www.ncei.noaa.gov/data/international-best-track-archive-for-climate-stewardship-ibtracs/v04r00/access/netcdf/{name}"
        self.logger.info(f"Downloading cyclone track database from {url}")
        fn = self.root.joinpath("static", "cyclone_track_database", name)
        fn.parent.mkdir()
        urlretrieve(url, fn)
        self.site_attrs["cyclone_track_database"] = {}
        self.site_attrs["cyclone_track_database"]["file"] = name

    def add_water_level(self):
        # TODO define better default values
        # TODO for use location get closest station and read values from there (add observation station as well!)
        self.site_attrs["water_level"] = {}

        self.site_attrs["water_level"]["reference"] = {}
        self.site_attrs["water_level"]["reference"]["name"] = "MSL"
        self.site_attrs["water_level"]["reference"]["height"] = {}
        self.site_attrs["water_level"]["reference"]["height"]["value"] = 0
        self.site_attrs["water_level"]["reference"]["height"]["units"] = (
            self.site_attrs["sfincs"]["floodmap_units"]
        )

        self.site_attrs["water_level"]["msl"] = {}
        self.site_attrs["water_level"]["msl"]["name"] = "MSL"
        self.site_attrs["water_level"]["msl"]["height"] = {}
        self.site_attrs["water_level"]["msl"]["height"]["value"] = 0
        self.site_attrs["water_level"]["msl"]["height"]["units"] = self.site_attrs[
            "sfincs"
        ]["floodmap_units"]

        self.site_attrs["water_level"]["localdatum"] = {}
        self.site_attrs["water_level"]["localdatum"]["name"] = "Datum"
        self.site_attrs["water_level"]["localdatum"]["height"] = {}
        self.site_attrs["water_level"]["localdatum"]["height"]["value"] = 0
        self.site_attrs["water_level"]["localdatum"]["height"]["units"] = (
            self.site_attrs["sfincs"]["floodmap_units"]
        )

    def add_slr(self):
        # TODO better default values
        # TODO add slr projections csv
        self.site_attrs["slr"] = {}
        self.site_attrs["slr"]["relative_to_year"] = 2020
        self.site_attrs["slr"]["vertical_offset"] = {}
        self.site_attrs["slr"]["vertical_offset"]["value"] = 0
        self.site_attrs["slr"]["vertical_offset"]["units"] = self.site_attrs["sfincs"][
            "floodmap_units"
        ]

    def add_obs_points(self):
        self.site_attrs["obs_point"] = []

        for op in self.config.obs_point:
            self.site_attrs["obs_point"].append(op.model_dump())

    def add_gui_params(self):
        # Read default units from template
        self.site_attrs["gui"] = self.get_default_units()
        # Get default value for tide?
        self.site_attrs["gui"]["tide_harmonic_amplitude"] = {
            "value": 0.0,  # TODO where should this come from?
            "units": self.site_attrs["gui"]["default_length_units"],
        }
        # Read default colors from template
        self.site_attrs["gui"]["mapbox_layers"] = self.get_bin_colors()
        # Derive bins from config max attributes
        fd_max = self.config.gui.max_flood_depth
        self.site_attrs["gui"]["mapbox_layers"][
            "flood_map_depth_min"
        ] = 0  # mask areas with flood depth lower than this (zero = all depths shown)
        self.site_attrs["gui"]["mapbox_layers"][
            "flood_map_zbmax"
        ] = (
            -9999
        )  # mask areas with elevation lower than this (very negative = show all calculated flood depths)
        self.site_attrs["gui"]["mapbox_layers"]["flood_map_bins"] = [
            0.2 * fd_max,
            0.6 * fd_max,
            fd_max,
        ]
        self.site_attrs["gui"]["damage_decimals"] = 0
        self.site_attrs["gui"]["footprints_dmg_type"] = "absolute"
        ad_max = self.config.gui.max_aggr_dmg
        self.site_attrs["gui"]["mapbox_layers"]["aggregation_dmg_bins"] = [
            0.00001,
            0.1 * ad_max,
            0.25 * ad_max,
            0.5 * ad_max,
            ad_max,
        ]
        fd_max = self.config.gui.max_footprint_dmg
        self.site_attrs["gui"]["mapbox_layers"]["footprints_dmg_bins"] = [
            0.00001,
            0.06 * fd_max,
            0.2 * fd_max,
            0.4 * fd_max,
            fd_max,
        ]
        b_max = self.config.gui.max_benefits
        self.site_attrs["gui"]["mapbox_layers"]["benefits_bins"] = [
            0,
            0.01,
            0.02 * b_max,
            0.2 * b_max,
            b_max,
        ]

        # Add visualization layers
        # TODO add option to input layer
        self.site_attrs["gui"]["visualization_layers"] = {}
        self.site_attrs["gui"]["visualization_layers"]["default_bin_number"] = 4
        self.site_attrs["gui"]["visualization_layers"]["default_colors"] = [
            "#FFFFFF",
            "#FEE9CE",
            "#E03720",
            "#860000",
        ]
        self.site_attrs["gui"]["visualization_layers"]["layer_names"] = []
        self.site_attrs["gui"]["visualization_layers"]["layer_long_names"] = []
        self.site_attrs["gui"]["visualization_layers"]["layer_paths"] = []
        self.site_attrs["gui"]["visualization_layers"]["field_names"] = []
        self.site_attrs["gui"]["visualization_layers"]["bins"] = []
        self.site_attrs["gui"]["visualization_layers"]["colors"] = []

    def add_general_attrs(self):
        self.site_attrs["risk"] = {}
        self.site_attrs["risk"]["return_periods"] = [1, 2, 5, 10, 25, 50, 100]
        self.site_attrs["risk"]["flooding_threshold"] = {}
        self.site_attrs["risk"]["flooding_threshold"][
            "value"
        ] = 0  # TODO how to define this
        self.site_attrs["risk"]["flooding_threshold"]["units"] = self.site_attrs[
            "sfincs"
        ]["floodmap_units"]

        self.site_attrs["standard_objects"] = {}
        self.site_attrs["standard_objects"]["events"] = ["probabilistic_set"]
        self.site_attrs["standard_objects"]["projections"] = ["current"]
        self.site_attrs["standard_objects"]["strategies"] = ["no_measures"]

        # TODO how to define the benefit objects?
        self.site_attrs["benefits"] = {}
        self.site_attrs["benefits"]["current_year"] = 2023
        self.site_attrs["benefits"]["current_projection"] = "current"
        self.site_attrs["benefits"]["baseline_strategy"] = "no_measures"
        self.site_attrs["benefits"]["event_set"] = "probabilistic_set"

    def add_static_files(self):
        templates_path = Path(__file__).parent.resolve().joinpath("templates")
        folders = ["icons", "green_infra_table"]
        for folder in folders:
            path_0 = templates_path.joinpath(folder)
            path_1 = self.root.joinpath("static", folder)
            shutil.copytree(path_0, path_1)

    def add_infometrics(self):
        templates_path = Path(__file__).parent.resolve().joinpath("templates")
        folders = ["infometrics", "infographics"]
        for folder in folders:
            path_0 = templates_path.joinpath(folder)
            path_1 = self.root.joinpath("static", "templates", folder)
            shutil.copytree(path_0, path_1)

        files = ["metrics_config.toml", "metrics_config_risk.toml"]
        path = self.root.joinpath("static", "templates", "infometrics")
        for file in files:
            file = path.joinpath(file)
            attrs = read_toml(file)
            attrs["aggregateBy"] = [
                aggr["name"] for aggr in self.site_attrs["fiat"]["aggregation"]
            ]
            with open(file, "wb") as f:
                tomli_w.dump(attrs, f)

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

    def save_site_config(self):
        site_config_path = self.root.joinpath("static", "site", "site.toml")
        site_config_path.parent.mkdir()

        site = Site.load_dict(self.site_attrs)
        site.save(filepath=site_config_path)


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
    dbs.add_obs_points()
    dbs.add_gui_params()
    dbs.add_dem()
    dbs.add_cyclone_dbs()
    dbs.add_static_files()
    dbs.add_water_level()
    dbs.add_slr()
    dbs.add_general_attrs()
    dbs.save_site_config()
    dbs.add_infometrics()
    dbs.create_standard_objects()


if __name__ == "__main__":
    main(["--config_path", r"c:\Users\athanasi\Github\Database\FA_builder\config.toml"])
