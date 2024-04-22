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
    """
    Create and configure a logger.

    Args:
        log_path (str): The path to the log file.

    Returns:
        logging.Logger: The configured logger object.
    """
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
    """
    Represents a spatial join model.

    Attributes:
        name (Optional[str]): The name of the model (optional).
        file (str): The file associated with the model.
        field_name (str): The field name used for the spatial join.
    """

    name: Optional[str] = None
    file: str
    field_name: str


class AggregationModel(SpatialJoinModel):
    equity: Optional[EquityModel] = None


class UnitSystems(str, Enum):
    """The `UnitSystems` class is an enumeration that represents the accepted values for the `metric_system` field.
    It provides two options: `imperial` and `metric`.

    Attributes:
        imperial (str): Represents the imperial unit system.
        metric (str): Represents the metric unit system.
    """

    imperial = "imperial"
    metric = "metric"


class Basins(str, Enum):
    """
    Enumeration class representing different basins.

    Each basin is represented by a string value.

    Attributes:
        NA (str): North Atlantic
        SA (str): South Atlantic
        EP (str): Eastern North Pacific (which includes the Central Pacific region)
        WP (str): Western North Pacific
        SP (str): South Pacific
        SI (str): South Indian
        NI (str): North Indian
    """

    NA = "NA"
    SA = "SA"
    EP = "EP"
    WP = "WP"
    SP = "SP"
    SI = "SI"
    NI = "NI"


class GuiModel(BaseModel):
    """
    Represents a GUI model for for FloodAdapt.

    Attributes:
        unit_system (Optional[UnitSystems]): The unit system used (default: "metric").
        max_flood_depth (float): The last visualization bin will be ">value".
        max_aggr_dmg (float): The last visualization bin will be ">value".
        max_footprint_dmg (float): The last visualization bin will be ">value".
        max_benefits (float): The last visualization bin will be ">value".
    """

    unit_system: Optional[UnitSystems] = "metric"
    max_flood_depth: float
    max_aggr_dmg: float
    max_aggr_dmg: float
    max_footprint_dmg: float
    max_benefits: float


class ConfigModel(BaseModel):
    """
    Configuration model for FloodAdapt.

    Attributes:
        name (str): The name of the study area.
        description (Optional[str]): The description of the study area.
        database_path (Optional[str]): The path to the database.
        sfincs (str): The SFINCS model path.
        sfincs_offshore (Optional[str]): The offshore SFINCS model path.
        fiat (str): The FIAT model path.
        gui (GuiModel): The GUI configuration.
        building_footprints (Optional[SpatialJoinModel]): The building footprints model.
        bfe (Optional[SpatialJoinModel]): The BFE (Base Flood Elevation) model.
        aggregation (list[AggregationModel]): The aggregation models.
        svi (Optional[SpatialJoinModel]): The SVI (Social Vulnerability Index) model.
        road_width (Optional[float]): The road width in meters.
        cyclone_basin (Optional[Basins]): The cyclone basin to be used.
        river (Optional[list[RiverModel]]): The river models.
        obs_point (Optional[list[Obs_pointModel]]): The observation point models.
    """

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
    cyclone_basin: Optional[Basins] = None
    river: Optional[list[RiverModel]] = []
    obs_point: Optional[list[Obs_pointModel]] = []


def read_toml(fn: str) -> dict:
    """
    Reads a TOML file and returns its contents as a dictionary.

    Args:
        fn (str): The path to the TOML file.

    Returns:
        dict: The contents of the TOML file as a dictionary.
    """
    with open(fn, mode="rb") as fp:
        toml = tomli.load(fp)
    return toml


def read_config(config: str) -> ConfigModel:
    """
    Reads a configuration file and returns the validated attributes.

    Args:
        config (str): The path to the configuration file.

    Returns:
        ConfigModel: The validated attributes from the configuration file.
    """
    toml = read_toml(config)
    attrs = ConfigModel.model_validate(toml)
    return attrs


class Database:
    """
    Represents a FloodAdapt database.

    Args:
        config (ConfigModel): The configuration model for the database.
        overwrite (bool, optional): Whether to overwrite an existing database folder. Defaults to True.
    """

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
        """
        Creates the folder structure for the database.

        This method creates the necessary folder structure for the FloodAdapt database, including
        the input and static folders. It also creates subfolders within the input and
        static folders based on a predefined list of names.
        """
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
        """
        Creates standard objects for the FloodAdapt model.

        This method creates a strategy with no measures and a projection with current
        physical and socio-economic conditions, and saves them to the database.
        """
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
        """
        Reads the FIAT model and extracts relevant information for the site configuration.

        This method reads the FIAT model from the specified path and performs the following steps:
        1. Copies the FIAT model to the database.
        2. Reads the model using hydromt-FIAT.
        3. Retrieves the center of the area of interest.
        4. Reads FIAT attributes for site configuration.
        5. Checks if building footprints are provided and handles different scenarios.
        6. Sets default values for output geoms and simulation saving.
        7. Adds base flood elevation information if provided.
        8. Reads aggregation areas.
        9. Handles the inclusion of SVI (Social Vulnerability Index).
        10. Ensures that FIAT roads are represented as polygons.
        """
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
        self.site_attrs["fiat"]["damage_unit"] = self.fiat_model.config["exposure"][
            "csv"
        ][
            "damage_unit"
        ]  # TODO This should be accessed from object!

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

        # add base flood elevation information
        if self.config.bfe:
            self.logger.info(
                f"Using map from {self.config.bfe.file} as base flood elevation."
            )
            # Read in BFE map and keep only column of interest
            bfe = gpd.read_file(self.config.bfe.file)
            bfe = bfe[[self.config.bfe.field_name, "geometry"]]
            # Read in geometries of buildings
            ind = self.fiat_model.exposure.geom_names.index("buildings")
            buildings = self.fiat_model.exposure.exposure_geoms[ind].copy()
            # Create folder
            bfe_folder = self.root.joinpath("static", "bfe")
            bfe_folder.mkdir()
            # Save the spatial file for future use
            geo_path = bfe_folder.joinpath("bfe.gpkg")
            bfe.to_file(geo_path)
            # Save csv with building values
            buildings = buildings.sjoin(bfe)
            buildings = buildings[["Object ID", "STATIC_BFE"]]
            csv_path = bfe_folder.joinpath("bfe.csv")
            buildings.to_csv(csv_path, index=False)
            # Save site attributes
            self.site_attrs["fiat"]["bfe"] = {}
            self.site_attrs["fiat"]["bfe"]["geom"] = str(
                Path("../")
                .joinpath(geo_path.relative_to(self.site_path.parent))
                .as_posix()
            )
            self.site_attrs["fiat"]["bfe"]["table"] = str(
                Path("../")
                .joinpath(csv_path.relative_to(self.site_path.parent))
                .as_posix()
            )
            self.site_attrs["fiat"]["bfe"]["field_name"] = self.config.bfe.field_name
        else:
            self.logger.info("No base flood elevation provided.")

        # Read aggregation areas
        self.site_attrs["fiat"]["aggregation"] = []
        for aggr in self.config.aggregation:
            # Make sure paths are correct
            aggr.file = str(Path("../templates/fiat/").joinpath(aggr.file).as_posix())
            aggr.equity.census_data = str(
                Path("../templates/fiat/").joinpath(aggr.equity.census_data).as_posix()
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
        """
        Reads the SFINCS model and sets the necessary attributes for the site configuration.

        This method performs the following steps:
        1. Copies the sfincs model to the database.
        2. Reads the model using hydromt-SFINCS.
        3. Sets the necessary attributes for the site configuration.
        """
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
        """
        Reads the offshore SFINCS model and sets the necessary attributes for the site configuration.

        This method reads the offshore SFINCS model and performs the following steps:
        1. Copies the offshore sfincs model to the database.
        2. Connects the boundary points of the overland model to the output points of the offshore model.

        """
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
        """
        Adds rivers to the site attributes.

        If `self.config.river` is empty, a dummy river is added with default values.
        Otherwise, the rivers specified in `self.config.river` are added.
        """
        if not self.config.river:
            self.site_attrs["river"] = [
                {
                    "name": "dummy",
                    "description": "dummy river",
                    "x_coordinate": 0,
                    "y_coordinate": 0,
                    "mean_discharge": UnitfulDischarge(value=0.0, units="m3/s"),
                }
            ]
        else:
            self.site_attrs["river"] = self.config.river

    def add_dem(self):
        """
        Moves DEM files from the SFINCS model to the FloodAdapt model.

        If the DEM files are found in the SFINCS model, they are moved to the corresponding
        location in the FloodAdapt model. The filenames and units of the DEM files are
        stored in the `site_attrs` dictionary.
        """
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
        """
        Downloads and adds a cyclone track database to the site attributes.

        If the `cyclone_basin` configuration is provided, it downloads the cyclone track database for the specified basin.
        Otherwise, it downloads the cyclone track database for all basins.

        The downloaded database is stored in the 'static/cyclone_track_database' directory.
        """
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
        """
        Adds water level information to the site attributes.

        This method adds water level information to the `site_attrs` dictionary.
        It sets default values for the water level reference, MSL (Mean Sea Level),
        and local datum. The height values are set to 0 by default.
        """
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
        """
        Adds sea level rise (SLR) attributes to the site.

        This method adds SLR attributes to the `site_attrs` dictionary. It sets default values for SLR relative to the year 2020 and a vertical offset of 0.
        The units for the vertical offset are obtained from the `sfincs` attribute in the `site_attrs` dictionary.
        """
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
        """
        Adds observation points to the site attributes.

        This method iterates over the `obs_point` list in the `config` object and appends the model dump of each observation point
        to the `obs_point` attribute in the `site_attrs` dictionary.
        """
        self.site_attrs["obs_point"] = []

        for op in self.config.obs_point:
            self.site_attrs["obs_point"].append(op.model_dump())

    def add_gui_params(self):
        """
        Adds GUI parameters to the site attributes dictionary.

        This method reads default units from a template, sets default values for tide, reads default colors from the template,
        derives bins from the config max attributes, and adds visualization layers.
        """
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
        """
        Adds general attributes to the site_attrs dictionary.

        This method adds various attributes related to risk, standard objects, and benefits
        to the site_attrs dictionary.
        """
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
        """
        Copies static files from the 'templates' folder to the 'static' folder.

        This method iterates over a list of folders and copies the contents of each folder from the 'templates' directory
        to the corresponding folder in the 'static' directory.
        """
        templates_path = Path(__file__).parent.resolve().joinpath("templates")
        folders = ["icons", "green_infra_table"]
        for folder in folders:
            path_0 = templates_path.joinpath(folder)
            path_1 = self.root.joinpath("static", folder)
            shutil.copytree(path_0, path_1)

    def add_infometrics(self):
        """
        Copies the infometrics and infographics templates to the appropriate location and modifies the metrics_config.toml files.

        This method copies the templates from the 'infometrics' and 'infographics' folders to the 'static/templates' folder in the root directory.
        It then modifies the 'metrics_config.toml' and 'metrics_config_risk.toml' files by updating the 'aggregateBy' attribute with the names
        of the aggregations defined in the 'fiat' section of the 'site_attrs' attribute.
        """
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
        """
        Retrieves the default units based on the configured GUI unit system.

        Returns:
            dict: A dictionary containing the default units.
        """
        type = self.config.gui.unit_system
        templates_path = Path(__file__).parent.resolve().joinpath("templates")
        default_units = read_toml(
            templates_path.joinpath("default_units", f"{type}.toml")
        )
        return default_units

    def get_bin_colors(self):
        """
        Retrieves the bin colors from the bin_colors.toml file.

        Returns:
            dict: A dictionary containing the bin colors.
        """
        templates_path = Path(__file__).parent.resolve().joinpath("templates")
        bin_colors = read_toml(
            templates_path.joinpath("mapbox_layers", "bin_colors.toml")
        )
        return bin_colors

    def save_site_config(self):
        """
        Saves the site configuration to a TOML file.

        This method creates a TOML file at the specified location and saves the site configuration
        using the `Site` class. The site configuration is obtained from the `site_attrs` attribute.
        """
        site_config_path = self.root.joinpath("static", "site", "site.toml")
        site_config_path.parent.mkdir()

        site = Site.load_dict(self.site_attrs)
        site.save(filepath=site_config_path)


@click.command()
@click.option(
    "--config_path", default="config.toml", help="Full path to the config toml file."
)
def main(config_path):
    """
    Main function for building FloodAdapt model.

    Args:
        config_path (str): Path to the configuration file.

    Returns:
        None
    """
    print(f"Read FloodAdapt building configuration from {config_path}")
    config = read_config(config_path)
    if not config.database_path:
        config.database_path = str(Path(config_path).parent)
    # Create a Database object
    dbs = Database(config)
    # Workflow to create the database using the object methods
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
