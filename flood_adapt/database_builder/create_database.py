import os
import shutil
from enum import Enum
from pathlib import Path
from shutil import rmtree
from typing import Optional, Union
from urllib.request import urlretrieve

import cht_observations.observation_stations as obs
import geopandas as gpd
import numpy as np
import pandas as pd
import rioxarray as rxr
import tomli
import tomli_w
import xarray as xr
from hydromt_fiat.data_apis.open_street_maps import get_buildings_from_osm
from hydromt_fiat.fiat import FiatModel
from hydromt_sfincs import SfincsModel
from pydantic import BaseModel, Field
from shapely.geometry import Polygon

from flood_adapt.api.events import get_event_mode
from flood_adapt.api.projections import create_projection, save_projection
from flood_adapt.api.static import read_database
from flood_adapt.api.strategies import create_strategy, save_strategy
from flood_adapt.config import Settings
from flood_adapt.log import FloodAdaptLogging
from flood_adapt.object_model.interface.site import ObsPointModel, SlrModel
from flood_adapt.object_model.io.unitfulvalue import UnitfulDischarge, UnitfulLength
from flood_adapt.object_model.site import Site

config_path = None


class SpatialJoinModel(BaseModel):
    """
    Represents a spatial join model.

    Attributes
    ----------
    name (Optional[str]): The name of the model (optional).
    file (str): The file associated with the model.
    field_name (str): The field name used for the spatial join.
    """

    name: Optional[str] = None
    file: str
    field_name: str


class UnitSystems(str, Enum):
    """The `UnitSystems` class is an enumeration that represents the accepted values for the `metric_system` field.

    It provides two options: `imperial` and `metric`.

    Attributes
    ----------
        imperial (str): Represents the imperial unit system.
        metric (str): Represents the metric unit system.
    """

    imperial = "imperial"
    metric = "metric"


class FootprintsOptions(str, Enum):
    OSM = "OSM"


class Basins(str, Enum):
    """
    Enumeration class representing different basins.

    Each basin is represented by a string value.

    Attributes
    ----------
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

    Attributes
    ----------
        max_flood_depth (float): The last visualization bin will be ">value".
        max_aggr_dmg (float): The last visualization bin will be ">value".
        max_footprint_dmg (float): The last visualization bin will be ">value".
        max_benefits (float): The last visualization bin will be ">value".
    """

    max_flood_depth: float
    max_aggr_dmg: float
    max_footprint_dmg: float
    max_benefits: float


class TideGaugeModel(BaseModel):
    """
    Represents a tide gauge model.

    Attributes
    ----------
        source (str): The source of the tide gauge data.
        file (Optional[str]): The file associated with the tide gauge data (default: None).
        max_distance (Optional[float]): The maximum distance (default: None).
        msl (Optional[float]): The mean sea level (default: None).
        datum (Optional[float]): The datum (default: None).
        datum_name (Optional[str]): The name of the datum (default: None).
    """

    source: str
    file: Optional[str] = None
    max_distance: Optional[UnitfulLength] = None
    # TODO add option to add MSL and Datum?
    ref: Optional[str] = None


class SviModel(SpatialJoinModel):
    """
    Represents a model for the Social Vulnerability Index (SVI).

    Attributes
    ----------
        threshold (float): The threshold value for the SVI model to specify vulnerability.
    """

    threshold: float


class SlrModelDef(SlrModel):
    """
    Represents a sea level rise (SLR) model definition.

    Attributes
    ----------
        vertical_offset (Optional[UnitfulLength]): The vertical offset of the SLR model, measured in meters.
    """

    vertical_offset: Optional[UnitfulLength] = UnitfulLength(value=0, units="meters")


class ConfigModel(BaseModel):
    """
    Represents the configuration model for FloodAdapt.

    Attributes
    ----------
    name : str
        The name of the site.
    description : Optional[str], default ""
        The description of the site.
    database_path : Optional[str], default None
        The path to the database where all the sites are located.
    sfincs : str
        The SFINCS model path.
    sfincs_offshore : Optional[str], default None
        The offshore SFINCS model path.
    fiat : str
        The FIAT model path.
    unit_system : UnitSystems
        The unit system.
    gui : GuiModel
        The GUI model representing scaling values for the layers.
    building_footprints : Optional[SpatialJoinModel], default None
        The building footprints model.
    slr : Optional[SlrModelDef], default SlrModelDef()
        The sea level rise model.
    tide_gauge : Optional[TideGaugeModel], default None
        The tide gauge model.
    bfe : Optional[SpatialJoinModel], default None
        The BFE model.
    svi : Optional[SviModel], default None
        The SVI model.
    road_width : Optional[float], default 2
        The road width in meters.
    cyclones : Optional[bool], default True
        Indicates if cyclones are enabled.
    cyclone_basin : Optional[Basins], default None
        The cyclone basin.
    obs_point : Optional[list[Obs_pointModel]], default None
        The list of observation point models.
    probabilistic_set : Optional[str], default None
        The probabilistic set path.
    infographics : Optional[bool], default True
        Indicates if infographics are enabled.
    """

    name: str = Field(..., min_length=1, pattern='^[^<>:"/\\\\|?* ]*$')
    description: Optional[str] = ""
    database_path: Optional[str] = None
    sfincs: str
    sfincs_offshore: Optional[str] = None
    fiat: str
    unit_system: UnitSystems
    gui: GuiModel
    building_footprints: Optional[SpatialJoinModel | FootprintsOptions] = (
        FootprintsOptions.OSM
    )
    slr: Optional[SlrModelDef] = SlrModelDef()
    tide_gauge: Optional[TideGaugeModel] = None
    bfe: Optional[SpatialJoinModel] = None
    svi: Optional[SviModel] = None
    road_width: Optional[float] = 5
    cyclones: Optional[bool] = True
    cyclone_basin: Optional[Basins] = None
    obs_point: Optional[list[ObsPointModel]] = None
    probabilistic_set: Optional[str] = None
    infographics: Optional[bool] = True


def read_toml(fn: Union[str, Path]) -> dict:
    """
    Read a TOML file and return its contents as a dictionary.

    Args:
        fn (str): The path to the TOML file.

    Returns
    -------
    dict: The contents of the TOML file as a dictionary.
    """
    with open(fn, mode="rb") as fp:
        toml = tomli.load(fp)
    return toml


def read_config(config: str) -> ConfigModel:
    """
    Read a configuration file and returns the validated attributes.

    Args:
        config (str): The path to the configuration file.

    Returns
    -------
        ConfigModel: The validated attributes from the configuration file.
    """
    toml = read_toml(config)
    attrs = ConfigModel.model_validate(toml)
    return attrs


def spatial_join(
    objects: gpd.GeoDataFrame,
    layer: Union[str, gpd.GeoDataFrame],
    field_name: str,
    rename: Optional[str] = None,
    filter: Optional[bool] = False,
) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    """
    Perform a spatial join between two GeoDataFrames.

    Args:
        objects (gpd.GeoDataFrame): The GeoDataFrame representing the objects.
        layer (Union[str, gpd.GeoDataFrame]): The GeoDataFrame or file path of the layer to join with.
        field_name (str): The name of the field to use for the join.
        rename (Optional[str], optional): The new name to assign to the joined field. Defaults to None.

    Returns
    -------
        tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]: A tuple containing the joined GeoDataFrame and the layer GeoDataFrame.

    """
    # Read in layer and keep only column of interest
    if not isinstance(layer, gpd.GeoDataFrame):
        layer = gpd.read_file(layer)
    layer = layer[[field_name, "geometry"]]
    layer = layer.to_crs(objects.crs)
    # Spatial join of the layers
    objects_joined = objects.sjoin(layer)
    # if needed filter out unused objects in the layer
    if filter:
        layer_inds = objects_joined["index_right"].dropna().unique()
        layer = layer.iloc[np.sort(layer_inds)].reset_index(drop=True)
    objects_joined = objects_joined[["Object ID", field_name]]
    # rename field if provided
    if rename:
        objects_joined = objects_joined.rename(columns={field_name: rename})
        layer = layer.rename(columns={field_name: rename})
    return objects_joined, layer


def path_check(path: str) -> str:
    """
    Check if the given path is absolute and return the absolute path.

    Args:
        path (str): The path to be checked.

    Returns
    -------
        str: The absolute path.

    Raises
    ------
        ValueError: If the path is not absolute and no config_path is provided.
    """
    path = Path(path)
    if not path.is_absolute():
        if config_path is not None:
            path = Path(config_path).parent.joinpath(path).resolve()
        else:
            raise ValueError(f"Value '{path}' should be an absolute path.")
    return str(path)


class Database:
    """
    Represents a FloodAdapt database.

    Args:
        config (ConfigModel): The configuration model for the database.
        overwrite (bool, optional): Whether to overwrite an existing database folder. Defaults to True.
    """

    def __init__(self, config: ConfigModel, overwrite=False):
        self.config = config
        config.database_path = path_check(config.database_path)
        root = Path(config.database_path).joinpath(config.name)

        if root.exists() and not overwrite:
            raise ValueError(
                f"There is already a Database folder in '{root.as_posix()}'."
            )
        if root.exists() and overwrite:
            rmtree(root)
        root.mkdir(parents=True)

        self.logger = FloodAdaptLogging().getLogger(__name__)

        self.logger.info(f"Initializing a FloodAdapt database in '{root.as_posix()}'")
        self.root = root
        self.site_attrs = {"name": config.name, "description": config.description}
        self.static_path = self.root.joinpath("static")
        self.site_path = self.static_path.joinpath("site")

    def make_folder_structure(self):
        """
        Create the folder structure for the database.

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
        Create standard objects for the FloodAdapt model.

        This method creates a strategy with no measures and a projection with current
        physical and socio-economic conditions, and saves them to the database.
        """
        # Load database
        Settings(
            database_root=self.root.parent,
            database_name=self.config.name,
        )
        read_database(Settings().database_root, Settings().database_name)
        # Create no measures strategy
        strategy = create_strategy({"name": "no_measures", "measures": []})
        save_strategy(strategy)
        # Create current conditions projection
        projection = create_projection(
            {
                "name": "current",
                "physical_projection": {},
                "socio_economic_change": {},
            }
        )
        save_projection(projection)
        # If provided use probabilistic set
        # TODO better check if configuration of event set is correct?
        if len(self.site_attrs["standard_objects"]["events"]) > 0:
            event_set = self.site_attrs["standard_objects"]["events"][0]
            if event_set:
                mode = get_event_mode(event_set)
                if mode != "risk":
                    self.logger.error(
                        f"Provided probabilistic event set '{event_set}' is not configured correctly! This event should have a risk mode."
                    )

    def _join_building_footprints(self, building_footprints, field_name):
        """
        Join building footprints with existing building data and updates the exposure CSV.

        Args:
            building_footprints (GeoDataFrame): GeoDataFrame containing the building footprints to be joined.
            field_name (str): The field name to use for the spatial join.

        Returns
        -------
            None

        This method performs the following steps:
        1. Reads the exposure CSV file.
        2. Performs a spatial join between the buildings and building footprints.
        3. Ensures that in case of multiple values, the first is kept.
        4. Creates a folder to store the building footprints.
        5. Saves the spatial file for future use.
        6. Merges the joined buildings with the exposure CSV and saves it.
        7. Updates the site attributes with the relative path to the saved building footprints.
        8. Logs the location where the building footprints are saved.
        """
        buildings = self.buildings
        exposure_csv = pd.read_csv(self.exposure_csv_path)
        buildings_joined, building_footprints = spatial_join(
            buildings,
            building_footprints,
            field_name,
            rename="BF_FID",
            filter=True,
        )
        # Make sure in case of multiple values that the first is kept
        buildings_joined = (
            buildings_joined.groupby("Object ID").first().sort_values(by=["Object ID"])
        )
        # Create folder
        bf_folder = Path(self.fiat_model.root).joinpath(
            "exposure", "building_footprints"
        )
        bf_folder.mkdir()
        # Save the spatial file for future use
        geo_path = bf_folder.joinpath("building_footprints.gpkg")
        building_footprints.to_file(geo_path)
        # Save to exposure csv
        exposure_csv = exposure_csv.merge(buildings_joined, on="Object ID", how="left")
        exposure_csv.to_csv(self.exposure_csv_path, index=False)
        # Save site attributes
        rel_path = Path(geo_path.relative_to(self.static_path)).as_posix()
        self.site_attrs["fiat"]["building_footprints"] = str(rel_path)
        self.logger.info(
            f"Building footprints saved at {self.static_path.joinpath(rel_path).resolve().as_posix()}"
        )

    def read_fiat(self):
        """
        Read the FIAT model and extracts relevant information for the site configuration.

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
        self.config.fiat = path_check(self.config.fiat)
        path = self.config.fiat
        self.logger.info(f"Reading FIAT model from {Path(path).as_posix()}.")
        # First copy FIAT model to database
        fiat_path = self.root.joinpath("static", "templates", "fiat")
        shutil.copytree(path, fiat_path)

        # Then read the model with hydromt-FIAT
        self.fiat_model = FiatModel(root=fiat_path, mode="w+")
        self.fiat_model.read()

        # Clip exposure to hazard extent
        # self._clip_hazard_extend()

        # Read in geometries of buildings
        # ind = self.fiat_model.exposure.geom_names.index("buildings")
        # self.buildings = self.fiat_model.exposure.exposure_geoms[ind].copy()
        self.exposure_csv_path = fiat_path.joinpath("exposure", "exposure.csv")

        # Get center of area of interest
        # center = self.buildings.dissolve().centroid.to_crs(4326)[0]
        # self.site_attrs["lat"] = center.y
        # self.site_attrs["lon"] = center.x

        # Read FIAT attributes for site config
        self.site_attrs["fiat"] = {}
        self.site_attrs["fiat"]["exposure_crs"] = self.fiat_model.exposure.crs
        self.site_attrs["fiat"]["floodmap_type"] = "water_level"  # TODO for now fixed
        self.site_attrs["fiat"]["non_building_names"] = ["road"]  # TODO for now fixed
        self.site_attrs["fiat"]["damage_unit"] = self.fiat_model.exposure.damage_unit
        fiat_units = self.fiat_model.config["vulnerability"]["unit"]
        if fiat_units == "ft":
            fiat_units = "feet"
        self.site_attrs["sfincs"]["floodmap_units"] = fiat_units
        self.site_attrs["sfincs"]["save_simulation"] = "False"

        # TODO make footprints an optional argument and use points as the minimum default spatial description
        # TODO restructure footprint options with less if statements

        # First check if the config has a spatial join provided for building footprints
        footprints_found = False
        if not isinstance(self.config.building_footprints, SpatialJoinModel):
            check_col = (
                "BF_FID" in self.fiat_model.exposure.exposure_db.columns
            )  # check if it is spatially joined already
            # Check if the file exists
            add_attrs = self.fiat_model.spatial_joins["additional_attributes"]
            if add_attrs:
                if "BF_FID" in [attr["name"] for attr in add_attrs]:
                    ind = [attr["name"] for attr in add_attrs].index("BF_FID")
                    footprints = add_attrs[ind]
                    footprints_path = fiat_path.joinpath(footprints["file"])
                    check_file = footprints_path.exists()
                else:
                    check_file = False
            else:
                check_file = False
            if check_file and not check_col:
                self.logger.error(
                    f"Exposure csv is missing the 'BF_FID' column to connect to the footprints located at {footprints_path}."
                )
                raise NotImplementedError
            if check_file and check_col:
                self.site_attrs["fiat"]["building_footprints"] = str(
                    Path(footprints_path.relative_to(self.static_path)).as_posix()
                )
                self.logger.info(
                    f"Using the building footprints located at {footprints_path}."
                )
                footprints_found = True
            # check if geometries are already footprints
            build_ind = self.fiat_model.exposure.geom_names.index("buildings")
            build_geoms = self.fiat_model.exposure.exposure_geoms[build_ind]
            if isinstance(build_geoms.geometry.iloc[0], Polygon):
                path0 = Path(self.fiat_model.root).joinpath(
                    self.fiat_model.config["exposure"]["geom"]["file1"]
                )
                # copy footprints to new location
                if not footprints_found:
                    path1 = Path(self.fiat_model.root).joinpath(
                        "building_footprints", "building_footprints.gpkg"
                    )
                    if not path1.parent.exists():
                        path1.parent.mkdir()
                    shutil.copyfile(path0, path1)

                # make geometries points
                build_geoms["geometry"] = build_geoms["geometry"].centroid
                build_geoms.to_file(path0)

                # add column for connection
                if not footprints_found:
                    exposure = self.fiat_model.exposure.exposure_db.set_index(
                        "Object ID"
                    )
                    build_geoms["BF_FID"] = build_geoms["Object ID"]
                    build_geoms = build_geoms.set_index("Object ID")
                    build_geoms["Extraction Method"] = "centroid"
                    exposure["BF_FID"] = build_geoms["BF_FID"]
                    exposure["Extraction Method"] = build_geoms["Extraction Method"]
                    exposure.reset_index().to_csv(self.exposure_csv_path, index=False)
                    footprints_found = True

            # Use other method to get Footprint
            if not footprints_found:
                if self.config.building_footprints == "OSM":
                    self.logger.info(
                        "Building footprint data will be downloaded from Open Street Maps."
                    )
                    region_path = Path(self.fiat_model.root).joinpath(
                        "geoms", "region.geojson"
                    )
                    if not region_path.exists():
                        self.logger.error("No region file found in the FIAT model.")
                    region = gpd.read_file(region_path).to_crs(4326)
                    polygon = Polygon(region.boundary.to_numpy()[0])
                    footprints = get_buildings_from_osm(polygon)
                    footprints["BF_FID"] = np.arange(1, len(footprints) + 1)
                    footprints = footprints[["BF_FID", "geometry"]]
                    self._join_building_footprints(footprints, "BF_FID")
                    footprints_found = True
            if not footprints_found:
                self.logger.error(
                    "No building footprints are available. These are needed in FloodAdapt."
                )
                raise ValueError
        else:
            self.config.building_footprints.file = path_check(
                self.config.building_footprints.file
            )
            self.logger.info(
                f"Using building footprints from {Path(self.config.building_footprints.file).as_posix()}."
            )
            # Spatially join buildings and map
            # TODO use hydromt method instead
            self._join_building_footprints(
                self.config.building_footprints.file,
                self.config.building_footprints.field_name,
            )

        # clip hazard here?
        # Read in geometries of buildings
        ind = self.fiat_model.exposure.geom_names.index("buildings")
        self.buildings = self.fiat_model.exposure.exposure_geoms[ind].copy()

        # Get center of area of interest
        center = self.buildings.dissolve().centroid.to_crs(4326)[0]
        self.site_attrs["lat"] = center.y
        self.site_attrs["lon"] = center.x

        self._clip_hazard_extend()

        # Add base flood elevation information
        if self.config.bfe:
            # TODO can we use hydromt-FIAT?
            self.config.bfe.file = path_check(self.config.bfe.file)
            self.logger.info(
                f"Using map from {Path(self.config.bfe.file).as_posix()} as base flood elevation."
            )
            # Spatially join buildings and map
            buildings_joined, bfe = spatial_join(
                self.buildings, self.config.bfe.file, self.config.bfe.field_name
            )
            # Make sure in case of multiple values that the max is kept
            buildings_joined = (
                buildings_joined.groupby("Object ID")
                .max(self.config.bfe.field_name)
                .sort_values(by=["Object ID"])
                .reset_index()
            )
            # Create folder
            bfe_folder = self.static_path.joinpath("bfe")
            bfe_folder.mkdir()
            # Save the spatial file for future use
            geo_path = bfe_folder.joinpath("bfe.gpkg")
            bfe.to_file(geo_path)
            # Save csv with building values
            csv_path = bfe_folder.joinpath("bfe.csv")
            buildings_joined.to_csv(csv_path, index=False)
            # Save site attributes
            self.site_attrs["fiat"]["bfe"] = {}
            self.site_attrs["fiat"]["bfe"]["geom"] = str(
                Path(geo_path.relative_to(self.static_path)).as_posix()
            )
            self.site_attrs["fiat"]["bfe"]["table"] = str(
                Path(csv_path.relative_to(self.static_path)).as_posix()
            )
            self.site_attrs["fiat"]["bfe"]["field_name"] = self.config.bfe.field_name
        else:
            self.logger.warning(
                "No base flood elevation provided. Elevating building relative to base flood elevation will not be possible in FloodAdapt."
            )

        # Read aggregation areas
        self.site_attrs["fiat"]["aggregation"] = []

        # If there are no aggregation areas make a schematic one from the region file
        # TODO make aggregation areas not mandatory
        if not self.fiat_model.spatial_joins["aggregation_areas"]:
            exposure_csv = pd.read_csv(self.exposure_csv_path)
            region_path = Path(self.fiat_model.root).joinpath("geoms", "region.geojson")
            if region_path.exists():
                region = gpd.read_file(region_path)
                region = region.explode().reset_index()
                region["id"] = ["region_" + str(i) for i in np.arange(len(region)) + 1]
                aggregation_path = Path(self.fiat_model.root).joinpath(
                    "exposure", "geoms", "region.geojson"
                )
                if not aggregation_path.parent.exists():
                    aggregation_path.parent.mkdir()
                region[["id", "geometry"]].to_file(aggregation_path, index=False)
                aggr = {}
                aggr["name"] = "region"
                aggr["file"] = str(
                    aggregation_path.relative_to(self.static_path).as_posix()
                )
                aggr["field_name"] = "id"
                self.site_attrs["fiat"]["aggregation"].append(aggr)

                # Add column in FIAT
                buildings_joined, _ = spatial_join(
                    self.buildings,
                    region,
                    "id",
                    rename="Aggregation Label: region",
                )
                exposure_csv = exposure_csv.merge(
                    buildings_joined, on="Object ID", how="left"
                )
                exposure_csv.to_csv(self.exposure_csv_path, index=False)
                self.logger.warning(
                    "No aggregation areas were available in the FIAT model. The region file will be used as a mock aggregation area."
                )
            else:
                self.logger.error(
                    "No aggregation areas were available in the FIAT model and no region geometry file is available. FloodAdapt needs at least one!"
                )
        else:
            for aggr in self.fiat_model.spatial_joins["aggregation_areas"]:
                # Make sure paths are correct
                aggr["file"] = str(
                    self.static_path.joinpath("templates", "fiat", aggr["file"])
                    .relative_to(self.static_path)
                    .as_posix()
                )
                if aggr["equity"] is not None:
                    aggr["equity"]["census_data"] = str(
                        self.static_path.joinpath(
                            "templates", "fiat", aggr["equity"]["census_data"]
                        )
                        .relative_to(self.static_path)
                        .as_posix()
                    )
                self.site_attrs["fiat"]["aggregation"].append(aggr)
            self.logger.info(
                f"The aggregation types {[aggr['name'] for aggr in self.fiat_model.spatial_joins['aggregation_areas']]} from the FIAT model are going to be used."
            )

        # Read SVI
        if self.config.svi:
            self.config.svi.file = path_check(self.config.svi.file)
            exposure_csv = pd.read_csv(self.exposure_csv_path)
            buildings_joined, svi = spatial_join(
                self.buildings,
                self.config.svi.file,
                self.config.svi.field_name,
                rename="SVI",
                filter=True,
            )
            # Add column to exposure
            if "SVI" in exposure_csv.columns:
                self.logger.info(
                    f"'SVI' column in the FIAT exposure csv will be replaced by {Path(self.config.svi.file).as_posix()}."
                )
                del exposure_csv["SVI"]
            else:
                self.logger.info(
                    f"'SVI' column in the FIAT exposure csv will be filled by {Path(self.config.svi.file).as_posix()}."
                )
            exposure_csv = exposure_csv.merge(
                buildings_joined, on="Object ID", how="left"
            )
            exposure_csv.to_csv(self.exposure_csv_path, index=False)
            # Create folder
            svi_folder = self.root.joinpath("static", "templates", "fiat", "svi")
            svi_folder.mkdir()
            # Save the spatial file for future use
            geo_path = svi_folder.joinpath("svi.gpkg")
            svi.to_file(geo_path)
            # Save site attributes
            self.site_attrs["fiat"]["svi"] = {}
            self.site_attrs["fiat"]["svi"]["geom"] = str(
                Path(geo_path.relative_to(self.static_path)).as_posix()
            )
            self.site_attrs["fiat"]["svi"]["field_name"] = "SVI"
            self.logger.info(
                f"An SVI map can be shown in FloodAdapt GUI using '{self.config.svi.field_name}' column from {Path(self.config.svi.file).as_posix()}"
            )
        else:
            if "SVI" in self.fiat_model.exposure.exposure_db.columns:
                self.logger.info("'SVI' column present in the FIAT exposure csv.")
                add_attrs = self.fiat_model.spatial_joins["additional_attributes"]
                if "SVI" in [attr["name"] for attr in add_attrs]:
                    ind = [attr["name"] for attr in add_attrs].index("SVI")
                    svi = add_attrs[ind]
                    svi_path = fiat_path.joinpath(svi["file"])
                    self.site_attrs["fiat"]["svi"] = {}
                    self.site_attrs["fiat"]["svi"]["geom"] = str(
                        Path(svi_path.relative_to(self.static_path)).as_posix()
                    )
                    self.site_attrs["fiat"]["svi"]["field_name"] = svi["field_name"]
                    self.logger.info(
                        f"An SVI map can be shown in FloodAdapt GUI using '{svi['field_name']}' column from {svi['field_name']}"
                    )
                else:
                    self.logger.warning("No SVI map found!")
            else:
                self.logger.warning(
                    "'SVI' column not present in the FIAT exposure csv. Vulnerability type infometrics cannot be produced."
                )

        # Make sure that FIAT roads are polygons
        self.roads = False
        if "roads" in self.fiat_model.exposure.geom_names:
            self.roads = True
            exposure_csv = pd.read_csv(self.exposure_csv_path)
            roads_ind = self.fiat_model.exposure.geom_names.index("roads")
            roads = self.fiat_model.exposure.exposure_geoms[roads_ind]
            roads_path = Path(self.fiat_model.root).joinpath(
                self.fiat_model.config["exposure"]["geom"]["file2"]
            )

            # TODO do we need the lanes column?
            if "Segment Length" not in exposure_csv.columns:
                self.logger.warning(
                    "'Segment Length' column not present in the FIAT exposure csv. Road impact infometrics cannot be produced."
                )

            # TODO should this should be performed through hydromt-FIAT?
            if not isinstance(roads.geometry.iloc[0], Polygon):
                roads = roads.to_crs(roads.estimate_utm_crs())
                roads.geometry = roads.geometry.buffer(
                    self.config.road_width / 2, cap_style=2
                )
                roads = roads.to_crs(self.fiat_model.exposure.crs)
                if roads_path.exists():
                    roads_path.unlink()
                roads.to_file(roads_path)
                self.logger.info(
                    f"FIAT road objects transformed from lines to polygons assuming a road width of {self.config.road_width} meters."
                )
        else:
            self.logger.warning(
                "Road objects are not available in the FIAT model and thus would not be available in FloodAdapt."
            )
            # TODO check how this naming of output geoms should become more explicit!
        if self.roads:
            self.site_attrs["fiat"]["roads_file_name"] = "spatial2.gpkg"
        self.site_attrs["fiat"]["new_development_file_name"] = "spatial3.gpkg"
        self.site_attrs["fiat"]["save_simulation"] = (
            "False"  # default is not to save simulations
        )

    def read_sfincs(self):
        """
        Read the SFINCS model and sets the necessary attributes for the site configuration.

        This method performs the following steps:
        1. Copies the sfincs model to the database.
        2. Reads the model using hydromt-SFINCS.
        3. Sets the necessary attributes for the site configuration.
        """
        self.config.sfincs = path_check(self.config.sfincs)
        path = self.config.sfincs

        # First copy sfincs model to database
        sfincs_path = self.root.joinpath("static", "templates", "overland")
        shutil.copytree(path, sfincs_path)

        # Then read the model with hydromt-SFINCS
        self.sfincs = SfincsModel(root=sfincs_path, mode="r+")
        self.sfincs.read()
        self.logger.info(
            f"Reading overland SFINCS model from {sfincs_path.as_posix()}."
        )

        self.site_attrs["sfincs"] = {}
        self.site_attrs["sfincs"]["csname"] = self.sfincs.crs.name
        self.site_attrs["sfincs"]["cstype"] = self.sfincs.crs.type_name.split(" ")[
            0
        ].lower()
        if self.config.sfincs_offshore:
            self.site_attrs["sfincs"]["offshore_model"] = "offshore"
        self.site_attrs["sfincs"]["overland_model"] = "overland"

    def read_offshore_sfincs(self):
        """
        Read the offshore SFINCS model and sets the necessary attributes for the site configuration.

        This method reads the offshore SFINCS model and performs the following steps:
        1. Copies the offshore sfincs model to the database.
        2. Connects the boundary points of the overland model to the output points of the offshore model.

        """
        if not self.config.sfincs_offshore:
            self.logger.warning(
                "No offshore SFINCS model was provided. Some event types will not be available in FloodAdapt"
            )
            return
        self.config.sfincs_offshore = path_check(self.config.sfincs_offshore)
        path = self.config.sfincs_offshore
        # TODO check if extents of offshore cover overland
        # First copy sfincs model to database
        sfincs_offshore_path = self.root.joinpath("static", "templates", "offshore")
        shutil.copytree(path, sfincs_offshore_path)
        self.logger.info(f"Reading offshore SFINCS model from {Path(path).as_posix()}.")
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
        self.logger.info(
            "Output points of the offshore SFINCS model were reconfigured to the boundary points of the overland SFINCS model."
        )

    def add_rivers(self):
        """
        Add rivers to the site attributes.

        If `self.config.river` is empty, a dummy river is added with default values.
        Otherwise, the rivers specified in `self.config.river` are added.
        """
        if "dis" not in self.sfincs.forcing:
            self.logger.warning("No rivers found in the SFINCS model.")
            return
        river_locs = self.sfincs.forcing["dis"].vector.to_gdf()
        river_locs.crs = self.sfincs.crs
        self.site_attrs["river"] = []

        for i, row in river_locs.iterrows():
            river = {}
            river["name"] = f"river_{i}"
            river["description"] = f"river_{i}"
            river["x_coordinate"] = row.geometry.x
            river["y_coordinate"] = row.geometry.y
            mean_dis = UnitfulDischarge(
                value=self.sfincs.forcing["dis"]
                .sel(index=i)
                .to_numpy()
                .mean(),  # in m3/s
                units="m3/s",
            )
            if self.config.unit_system == "imperial":
                mean_dis.value = mean_dis.convert("cfs")
                mean_dis.units = "cfs"
            river["mean_discharge"] = mean_dis
            self.site_attrs["river"].append(river)
        self.logger.warning(
            f"{len(river_locs)} river(s) were identified from the SFINCS model and will be available in FloodAdapt for discharge input."
        )
        # TODO add rivers in the SFINCS model through the config?

    def add_dem(self):
        """
        Move DEM files from the SFINCS model to the FloodAdapt model.

        If the DEM files are found in the SFINCS model, they are moved to the corresponding
        location in the FloodAdapt model. The filenames and units of the DEM files are
        stored in the `site_attrs` dictionary.
        """
        tiles_sfincs = Path(self.sfincs.root).joinpath("tiles")
        fa_path1 = self.root.joinpath("static", "dem", "tiles")

        # check for subgrid file
        fn = "dep_subgrid.tif"
        subgrid_sfincs = Path(self.sfincs.root).joinpath("subgrid", fn)
        if subgrid_sfincs.exists():
            fa_path2 = self.root.joinpath("static", "dem", fn)
        else:
            self.logger.error(
                f"A subgrid depth geotiff file should be available at {subgrid_sfincs}."
            )

        # Check if tiles already exist in the SFINCS model
        if tiles_sfincs.exists():
            shutil.move(tiles_sfincs, fa_path1)
            # Make sure name of tile indices is correct
            if fa_path1.joinpath("index").exists():
                os.rename(fa_path1.joinpath("index"), fa_path1.joinpath("indices"))
            self.logger.info(
                "Tiles were already available in the SFINCS model and will directly be used in FloodAdapt."
            )
        else:
            fa_path1.mkdir(parents=True)
            # Make tiles
            self.sfincs.setup_tiles(
                path=fa_path1,
                datasets_dep=[{"elevtn": subgrid_sfincs}],
                zoom_range=[0, 13],
                fmt="png",
            )
            self.logger.info(
                f"Tiles were created using the {subgrid_sfincs} as the elevation map."
            )
        # Copy subgrid file
        shutil.copy(subgrid_sfincs, fa_path2)

        # add site configs
        self.site_attrs["dem"] = {}
        self.site_attrs["dem"]["filename"] = fn
        self.site_attrs["dem"]["units"] = (
            "meters"  # This is always in meters from SFINCS
        )

    def update_fiat_elevation(self):
        """
        Update the ground elevations of FIAT objects based on the SFINCS ground elevation map.

        This method reads the DEM file and the exposure CSV file, and updates the ground elevations
        of the FIAT objects (roads and buildings) based on the nearest elevation values from the DEM.
        """
        dem_file = self.static_path.joinpath("dem", self.site_attrs["dem"]["filename"])
        # TODO resolve issue with double geometries in hydromt-FIAT and use update_ground_elevation method instead
        # self.fiat_model.update_ground_elevation(dem_file)
        self.logger.info(
            "Updating FIAT objects ground elevations from SFINCS ground elevation map."
        )
        SFINCS_units = UnitfulLength(
            value=1.0, units="meters"
        )  # SFINCS is always in meters
        FIAT_units = self.site_attrs["sfincs"]["floodmap_units"]
        conversion_factor = SFINCS_units.convert(FIAT_units)

        if conversion_factor != 1:
            self.logger.info(
                f"Ground elevation for FIAT objects is in '{FIAT_units}', while SFINCS ground elevation is in 'meters'. Values in the exposure csv will be converted by a factor of {conversion_factor}"
            )

        exposure_csv_path = Path(self.fiat_model.root).joinpath(
            "exposure", "exposure.csv"
        )
        exposure = pd.read_csv(exposure_csv_path)
        dem = rxr.open_rasterio(dem_file)
        if "roads" in self.fiat_model.exposure.geom_names:
            roads_path = Path(self.fiat_model.root) / "exposure" / "roads.gpkg"
            roads = gpd.read_file(roads_path).to_crs(dem.spatial_ref.crs_wkt)
            roads["geometry"] = roads.geometry.centroid  # get centroids

            x_points = xr.DataArray(roads["geometry"].x, dims="points")
            y_points = xr.DataArray(roads["geometry"].y, dims="points")
            roads["elev"] = (
                dem.sel(x=x_points, y=y_points, band=1, method="nearest").to_numpy()
                * conversion_factor
            )

            exposure.loc[
                exposure["Primary Object Type"] == "road", "Ground Floor Height"
            ] = 0
            exposure = exposure.merge(
                roads[["Object ID", "elev"]], on="Object ID", how="left"
            )
            exposure.loc[
                exposure["Primary Object Type"] == "road", "Ground Elevation"
            ] = exposure.loc[exposure["Primary Object Type"] == "road", "elev"]
            del exposure["elev"]

        buildings_path = Path(self.fiat_model.root) / "exposure" / "buildings.gpkg"
        points = gpd.read_file(buildings_path).to_crs(dem.spatial_ref.crs_wkt)
        x_points = xr.DataArray(points["geometry"].x, dims="points")
        y_points = xr.DataArray(points["geometry"].y, dims="points")
        points["elev"] = (
            dem.sel(x=x_points, y=y_points, band=1, method="nearest").to_numpy()
            * conversion_factor
        )
        exposure = exposure.merge(
            points[["Object ID", "elev"]], on="Object ID", how="left"
        )
        exposure.loc[exposure["Primary Object Type"] != "road", "Ground Elevation"] = (
            exposure.loc[exposure["Primary Object Type"] != "road", "elev"]
        )
        del exposure["elev"]

        exposure.to_csv(exposure_csv_path, index=False)

    def add_cyclone_dbs(self):
        """
        Download and adds a cyclone track database to the site attributes.

        If the `cyclone_basin` configuration is provided, it downloads the cyclone track database for the specified basin.
        Otherwise, it downloads the cyclone track database for all basins.

        The downloaded database is stored in the 'static/cyclone_track_database' directory.
        """
        if not self.config.cyclones or not self.config.sfincs_offshore:
            self.logger.warning("No cyclones will be available in the database.")
            return
        if self.config.cyclone_basin:
            basin = self.config.cyclone_basin
        else:
            basin = "ALL"
        name = f"IBTrACS.{basin}.v04r00.nc"
        url = f"https://www.ncei.noaa.gov/data/international-best-track-archive-for-climate-stewardship-ibtracs/v04r00/access/netcdf/{name}"
        self.logger.info(f"Downloading cyclone track database from {url}")
        fn = self.root.joinpath("static", "cyclone_track_database", name)
        fn.parent.mkdir()
        try:
            urlretrieve(url, fn)
        except Exception as e:
            print(e)
            self.logger.error(f"Could not retrieve cyclone track database from {url}")
        self.site_attrs["cyclone_track_database"] = {}
        self.site_attrs["cyclone_track_database"]["file"] = name

    def add_tide_gauge(self):
        """
        Add water level information to the site attributes.

        This method adds water level information to the `site_attrs` dictionary.
        It sets default values for the water level reference, MSL (Mean Sea Level),
        and local datum. The height values are set to 0 by default.
        """
        # Start by defining default values for water levels
        self.site_attrs["water_level"] = {}

        self.site_attrs["water_level"]["msl"] = {}
        self.site_attrs["water_level"]["msl"]["name"] = "MSL"
        self.site_attrs["water_level"]["msl"]["height"] = {}
        self.site_attrs["water_level"]["msl"]["height"]["value"] = 0.0
        self.site_attrs["water_level"]["msl"]["height"]["units"] = self.site_attrs[
            "sfincs"
        ]["floodmap_units"]

        self.site_attrs["water_level"]["localdatum"] = {}
        self.site_attrs["water_level"]["localdatum"]["name"] = "MSL"
        self.site_attrs["water_level"]["localdatum"]["height"] = {}
        self.site_attrs["water_level"]["localdatum"]["height"]["value"] = 0.0
        self.site_attrs["water_level"]["localdatum"]["height"]["units"] = (
            self.site_attrs["sfincs"]["floodmap_units"]
        )

        self.site_attrs["water_level"]["reference"] = {}
        self.site_attrs["water_level"]["reference"]["name"] = "MSL"
        self.site_attrs["water_level"]["reference"]["height"] = {}
        self.site_attrs["water_level"]["reference"]["height"]["value"] = 0.0
        self.site_attrs["water_level"]["reference"]["height"]["units"] = (
            self.site_attrs["sfincs"]["floodmap_units"]
        )
        self.site_attrs["water_level"]["other"] = []

        zero_wl_msg = "No water level references were found. It is assumed that MSL is equal to the datum used in the SFINCS overland model. You can provide these values with the tide_gauge.msl and tide_gauge.datum attributes in the site.toml."

        # Then check if there is any extra configurations given
        if self.config.tide_gauge is None:
            self.logger.warning(
                "Tide gauge information not provided. Historical nearshore gauged events will not be available in FloodAdapt!"
            )
            self.logger.warning(zero_wl_msg)
        else:
            if self.config.tide_gauge.source != "file":
                if self.config.tide_gauge.ref is not None:
                    ref = self.config.tide_gauge.ref
                else:
                    ref = "MLLW"
                station = self._get_closest_station(ref)
                if station is not None:
                    # Add tide_gauge information in site toml
                    self.site_attrs["tide_gauge"] = {}
                    # Mandatory fields
                    self.site_attrs["tide_gauge"]["source"] = (
                        self.config.tide_gauge.source
                    )
                    self.site_attrs["tide_gauge"]["ID"] = int(station["id"])
                    # Extra fields
                    self.site_attrs["tide_gauge"]["name"] = station["name"]
                    self.site_attrs["tide_gauge"]["lon"] = station["lon"]
                    self.site_attrs["tide_gauge"]["lat"] = station["lat"]
                    self.site_attrs["water_level"]["msl"]["height"]["value"] = station[
                        "msl"
                    ]
                    self.site_attrs["water_level"]["localdatum"]["name"] = station[
                        "datum_name"
                    ]
                    self.site_attrs["water_level"]["localdatum"]["height"]["value"] = (
                        station["datum"]
                    )
                    self.site_attrs["water_level"]["reference"]["name"] = station[
                        "reference"
                    ]
                    for name in ["MLLW", "MHHW"]:
                        wl_info = {}
                        wl_info["name"] = name
                        wl_info["height"] = {}
                        wl_info["height"]["value"] = station[name.lower()]
                        wl_info["height"]["units"] = self.site_attrs["sfincs"][
                            "floodmap_units"
                        ]
                        self.site_attrs["water_level"]["other"].append(wl_info)

                else:
                    self.logger.warning(zero_wl_msg)
            if self.config.tide_gauge.source == "file":
                self.config.tide_gauge.file = path_check(self.config.tide_gauge.file)
                self.site_attrs["tide_gauge"] = {}
                self.site_attrs["tide_gauge"]["source"] = "file"
                file_path = Path(self.static_path).joinpath(
                    "tide_gauges", Path(self.config.tide_gauge.file).name
                )
                if not file_path.parent.exists():
                    file_path.parent.mkdir()
                shutil.copyfile(self.config.tide_gauge.file, file_path)
                self.site_attrs["tide_gauge"]["file"] = str(
                    Path(file_path.relative_to(self.static_path)).as_posix()
                )
                self.logger.warning(zero_wl_msg)

    def _get_closest_station(self, ref: str = "MLLW"):
        """
        Find the closest tide gauge station to the SFINCS domain and retrieves its metadata.

        Args:
            ref (str, optional): The reference level for water level measurements. Defaults to "MLLW".

        Returns
        -------
            dict: A dictionary containing the metadata of the closest tide gauge station.
                The dictionary includes the following keys:
                - "id": The station ID.
                - "name": The station name.
                - "datum": The difference between the station's datum and the reference level.
                - "datum_name": The name of the datum used by the station.
                - "msl": The difference between the Mean Sea Level (MSL) and the reference level.
                - "reference": The reference level used for water level measurements.
                - "lon": The longitude of the station.
                - "lat": The latitude of the station.
        """
        # Get available stations from source
        obs_data = obs.source(self.config.tide_gauge.source)
        obs_data.get_active_stations()
        obs_stations = obs_data.gdf()
        # Calculate distance from SFINCS region to all available stations in degrees
        obs_stations["distance"] = obs_stations.distance(
            self.sfincs.region.to_crs(4326).geometry.item()
        )
        # Get the closest station and its distance in meters
        closest_station = obs_stations[
            obs_stations["distance"] == obs_stations["distance"].min()
        ]
        distance = round(
            closest_station.to_crs(self.sfincs.region.crs)
            .distance(self.sfincs.region.geometry.item())
            .item(),
            0,
        )
        units = self.site_attrs["sfincs"]["floodmap_units"]
        distance = UnitfulLength(value=distance, units="meters")
        self.logger.info(
            f"The closest tide gauge from {self.config.tide_gauge.source} is located {distance.convert(units)} {units} from the SFINCS domain"
        )
        # Check if user provided max distance
        # TODO make sure units are explicit for max_distance
        if self.config.tide_gauge.max_distance is not None:
            units_new = self.config.tide_gauge.max_distance.units
            distance_new = UnitfulLength(
                value=distance.convert(units_new), units=units_new
            )
            if distance_new.value > self.config.tide_gauge.max_distance.value:
                self.logger.warning(
                    f"This distance is larger than the 'max_distance' value of {self.config.tide_gauge.max_distance.value} {units_new} provided in the config file. The station cannot be used."
                )
                return None

        # get station id
        station_id = closest_station["id"].item()
        # read station metadata
        station_metadata = obs_data.get_meta_data(closest_station.id.item())
        # TODO check if all stations can be used? Tidal attr?
        # Get water levels by using the ref provided
        datum_name = station_metadata["datums"]["OrthometricDatum"]
        datums = station_metadata["datums"]["datums"]
        names = [datum["name"] for datum in datums]

        ref_value = datums[names.index(ref)]["value"]

        meta = {}
        meta["id"] = station_id
        meta["name"] = station_metadata["name"]
        meta["datum"] = round(datums[names.index(datum_name)]["value"] - ref_value, 3)
        meta["datum_name"] = datum_name
        meta["msl"] = round(datums[names.index("MSL")]["value"] - ref_value, 3)
        meta["mllw"] = round(datums[names.index("MLLW")]["value"] - ref_value, 3)
        meta["mhhw"] = round(datums[names.index("MHHW")]["value"] - ref_value, 3)
        meta["reference"] = ref
        meta["lon"] = closest_station.geometry.x.item()
        meta["lat"] = closest_station.geometry.y.item()

        self.logger.info(
            f"The tide gauge station '{station_metadata['name']}' from {self.config.tide_gauge.source} will be used to download nearshore historical water level time-series."
        )

        self.logger.info(
            f"The station metadata will be used to fill in the water_level attribute in the site.toml. The reference level will be {ref}."
        )

        return meta

    def add_slr(self):
        """
        Add sea level rise (SLR) attributes to the site.

        This method adds SLR attributes to the `site_attrs` dictionary. It sets default values for SLR relative to the year 2020 and a vertical offset of 0.
        The units for the vertical offset are obtained from the `sfincs` attribute in the `site_attrs` dictionary.
        """
        # TODO better default values
        self.site_attrs["slr"] = {}
        vertical_offset = self.config.slr.vertical_offset.model_copy()
        # Make sure units are consistent
        self.site_attrs["slr"]["vertical_offset"] = {}
        self.site_attrs["slr"]["vertical_offset"]["value"] = vertical_offset.convert(
            self.site_attrs["sfincs"]["floodmap_units"]
        )
        self.site_attrs["slr"]["vertical_offset"]["units"] = self.site_attrs["sfincs"][
            "floodmap_units"
        ]
        # If slr scenarios are given put them in the correct locations
        if self.config.slr.scenarios:
            self.config.slr.scenarios.file = path_check(self.config.slr.scenarios.file)
            self.site_attrs["slr"]["scenarios"] = self.config.slr.scenarios
            slr_path = self.static_path.joinpath("slr")
            slr_path.mkdir()
            new_file = slr_path.joinpath(Path(self.config.slr.scenarios.file).name)
            # copy file
            shutil.copyfile(self.config.slr.scenarios.file, new_file)
            # add site attributes
            self.site_attrs["slr"]["scenarios"] = {}
            self.site_attrs["slr"]["scenarios"]["file"] = new_file.relative_to(
                self.static_path
            ).as_posix()
            self.site_attrs["slr"]["scenarios"]["relative_to_year"] = (
                self.config.slr.scenarios.relative_to_year
            )

    def add_obs_points(self):
        """
        Add observation points to the site attributes.

        This method iterates over the `obs_point` list in the `config` object and appends the model dump of each observation point
        to the `obs_point` attribute in the `site_attrs` dictionary.
        """
        if self.config.obs_point is not None:
            self.logger.info("Observation points were provided in the config file.")
            self.site_attrs["obs_point"] = []
            for op in self.config.obs_point:
                self.site_attrs["obs_point"].append(op.model_dump())

    def add_gui_params(self):
        """
        Add GUI parameters to the site attributes dictionary.

        This method reads default units from a template, sets default values for tide, reads default colors from the template,
        derives bins from the config max attributes, and adds visualization layers.
        """
        # Read default units from template
        self.site_attrs["gui"] = self._get_default_units()
        # Check if the water level attribute include info on MHHW and MSL
        other = [attr["name"] for attr in self.site_attrs["water_level"]["other"]]
        if "MHHW" in other:
            amplitude = (
                self.site_attrs["water_level"]["other"][other.index("MHHW")]["height"][
                    "value"
                ]
                - self.site_attrs["water_level"]["msl"]["height"]["value"]
            )
            self.logger.info(
                f"The default tidal amplitude in the GUI will be {amplitude} {self.site_attrs['gui']['default_length_units']}, calculated as the difference between MHHW and MSL from the tide gauge data."
            )
        else:
            amplitude = 0.0
            self.logger.warning(
                "The default tidal amplitude in the GUI will be 0.0, since no tide-gauge water levels are available. You can change this in the site.toml with the 'gui.tide_harmonic_amplitude' attribute."
            )

        self.site_attrs["gui"]["tide_harmonic_amplitude"] = {
            "value": amplitude,  # TODO where should this come from?
            "units": self.site_attrs["gui"]["default_length_units"],
        }
        # Read default colors from template
        self.site_attrs["gui"]["mapbox_layers"] = self._get_bin_colors()
        # Derive bins from config max attributes
        fd_max = self.config.gui.max_flood_depth
        self.site_attrs["gui"]["mapbox_layers"]["flood_map_depth_min"] = (
            0  # mask areas with flood depth lower than this (zero = all depths shown) # TODO How to define this?
        )
        self.site_attrs["gui"]["mapbox_layers"]["flood_map_zbmax"] = (
            -9999  # TODO How to define this?
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

        if "svi" in self.site_attrs["fiat"]:
            self.site_attrs["gui"]["mapbox_layers"]["svi_bins"] = [
                0.05,
                0.2,
                0.4,
                0.6,
                0.8,
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
        Add general attributes to the site_attrs dictionary.

        This method adds various attributes related to risk, standard objects, and benefits
        to the site_attrs dictionary.
        """
        self.site_attrs["risk"] = {}
        self.site_attrs["risk"]["return_periods"] = [
            1,
            2,
            5,
            10,
            25,
            50,
            100,
        ]  # TODO this could be an input?
        self.site_attrs["flood_frequency"] = {}
        self.site_attrs["flood_frequency"]["flooding_threshold"] = {}
        self.site_attrs["flood_frequency"]["flooding_threshold"]["value"] = (
            0  # TODO this could be an input?
        )
        self.site_attrs["flood_frequency"]["flooding_threshold"]["units"] = (
            self.site_attrs["sfincs"]["floodmap_units"]
        )

        # Copy prob set if given
        if self.config.probabilistic_set:
            self.config.probabilistic_set = path_check(self.config.probabilistic_set)
            self.logger.info(
                f"{self.site_attrs['name']} probabilistic event set imported from {self.config.probabilistic_set}"
            )
            prob_event_name = Path(self.config.probabilistic_set).name
            path_1 = self.root.joinpath("input", "events", prob_event_name)
            shutil.copytree(self.config.probabilistic_set, path_1)
        else:
            self.logger.warning(
                "probabilistic event set not provided. Risk scenarios cannot be run."
            )
        self.site_attrs["standard_objects"] = {}
        if self.config.probabilistic_set:
            self.site_attrs["standard_objects"]["events"] = [prob_event_name]
        else:
            self.site_attrs["standard_objects"]["events"] = []
        self.site_attrs["standard_objects"]["projections"] = ["current"]
        self.site_attrs["standard_objects"]["strategies"] = ["no_measures"]

        # TODO how to define the benefit objects?
        self.site_attrs["benefits"] = {}
        self.site_attrs["benefits"]["current_year"] = 2023
        self.site_attrs["benefits"]["current_projection"] = "current"
        self.site_attrs["benefits"]["baseline_strategy"] = "no_measures"
        if self.config.probabilistic_set:
            self.site_attrs["benefits"]["event_set"] = prob_event_name
        else:
            self.site_attrs["benefits"]["event_set"] = ""

    def add_static_files(self):
        """
        Copy static files from the 'templates' folder to the 'static' folder.

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
        Copy the infometrics and infographics templates to the appropriate location and modifies the metrics_config.toml files.

        This method copies the templates from the 'infometrics' and 'infographics' folders to the 'static/templates' folder in the root directory.
        It then modifies the 'metrics_config.toml' and 'metrics_config_risk.toml' files by updating the 'aggregateBy' attribute with the names
        of the aggregations defined in the 'fiat' section of the 'site_attrs' attribute.
        """
        # TODO there should be generalized infometric queries with NSI or OSM, and with SVI or without. Then Based on the user input these should be chosen automatically
        templates_path = Path(__file__).parent.resolve().joinpath("templates")

        # Create template folder
        path_im = self.root.joinpath("static", "templates", "infometrics")
        path_im.mkdir()

        # Copy mandatory metric configs
        path_im_temp = templates_path.joinpath("infometrics")
        for file in path_im_temp.glob("*.toml"):
            shutil.copy(file, path_im)

        # If infographics are going to be created in FA, get template metric configurations
        if self.config.infographics:
            self.site_attrs["fiat"]["infographics"] = "True"

            # Check what type of infographics should be used
            if self.config.unit_system == "imperial":
                self.metrics_folder_name = "US_NSI"
                self.logger.info(
                    "Default NSI infometrics and infographics will be created."
                )
            elif self.config.unit_system == "metric":
                self.metrics_folder_name = "OSM"
                self.logger.info(
                    "Default OSM infometrics and infographics will be created."
                )

            if "svi" in self.site_attrs["fiat"]:
                svi_folder_name = "with_SVI"
            else:
                svi_folder_name = "without_SVI"

            # Copy metrics config for infographics
            path_0 = templates_path.joinpath(
                "infometrics", self.metrics_folder_name, svi_folder_name
            )
            for file in path_0.glob("*.toml"):
                shutil.copy(file, path_im)

            # Copy additional risk config
            file = templates_path.joinpath(
                "infometrics",
                self.metrics_folder_name,
                "metrics_additional_risk_configs.toml",
            )
            shutil.copy(file, path_im)

            # Copy infographics config
            path_ig_temp = templates_path.joinpath(
                "infographics", self.metrics_folder_name
            )
            path_ig = self.root.joinpath("static", "templates", "infographics")
            path_ig.mkdir()
            files_ig = ["styles.css", "config_charts.toml"]
            if "svi" in self.site_attrs["fiat"]:
                files_ig.append("config_risk_charts.toml")
                files_ig.append("config_people.toml")
            if self.roads:
                files_ig.append("config_roads.toml")
            for file in files_ig:
                shutil.copy(path_ig_temp.joinpath(file), path_ig.joinpath(file))

            # Copy images
            path_0 = templates_path.joinpath("infographics", "images")
            path_1 = self.root.joinpath("static", "templates", "infographics", "images")
            shutil.copytree(path_0, path_1)
        else:
            self.site_attrs["fiat"]["infographics"] = "False"

        path = self.root.joinpath("static", "templates", "infometrics")
        files = list(path.glob("*metrics_config*.toml"))
        # Update aggregation areas in metrics config
        for file in files:
            file = path.joinpath(file)
            attrs = read_toml(file)
            # add aggration levels
            attrs["aggregateBy"] = [
                aggr["name"] for aggr in self.site_attrs["fiat"]["aggregation"]
            ]
            # take out road metrics if needed
            if not self.roads:
                attrs["queries"] = [
                    query
                    for query in attrs["queries"]
                    if "road" not in query["name"].lower()
                ]
            # Replace Damage Unit
            for i, query in enumerate(attrs["queries"]):
                if "$" in query["long_name"]:
                    query["long_name"] = query["long_name"].replace(
                        "$", self.fiat_model.config["exposure"]["damage_unit"]
                    )

            # replace the SVI threshold if needed
            if self.config.svi:
                for i, query in enumerate(attrs["queries"]):
                    query["filter"] = query["filter"].replace(
                        "SVI_threshold", str(self.config.svi.threshold)
                    )
            with open(file, "wb") as f:
                tomli_w.dump(attrs, f)

    def save_site_config(self):
        """
        Save the site configuration to a TOML file.

        This method creates a TOML file at the specified location and saves the site configuration
        using the `Site` class. The site configuration is obtained from the `site_attrs` attribute.
        """
        site_config_path = self.root.joinpath("static", "site", "site.toml")
        site_config_path.parent.mkdir()

        site = Site.load_dict(self.site_attrs)
        site.save(filepath=site_config_path)

    def _clip_hazard_extend(self):
        """
        Clip the exposure data to the bounding box of the hazard data.

        This method clips the exposure data to the bounding box of the hazard data. It creates a GeoDataFrame
        from the hazard polygons, and then uses the `gpd.clip` function to clip the exposure geometries to the
        bounding box of the hazard polygons. If the exposure data contains roads, it is split into two separate
        GeoDataFrames: one for buildings and one for roads. The clipped exposure data is then saved back to the
        `exposure_db` attribute of the `FiatModel` object.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        gdf = self.fiat_model.exposure.get_full_gdf(
            self.fiat_model.exposure.exposure_db
        )
        crs = gdf.crs
        sfincs_extend = self.sfincs.region
        sfincs_extend = sfincs_extend.to_crs(crs)
        sfincs_geom = sfincs_extend.unary_union

        # Clip the fiat region
        clipped_region = self.fiat_model.region.clip(sfincs_extend)
        self.fiat_model.geoms["region"] = clipped_region

        # Clip the building footprints
        self.fiat_model.building_footprint = self.fiat_model.building_footprint[
            self.fiat_model.building_footprint["geometry"].within(sfincs_geom)
        ]
        bf_fid = self.fiat_model.building_footprint["BF_FID"]
        fieldname = "BF_FID"

        # Clip the exposure geometries
        # Filter buildings and roads
        if gdf["Primary Object Type"].str.contains("road").any():
            gdf_roads = gdf[gdf["Primary Object Type"].str.contains("road")]
            gdf_roads = gdf_roads[gdf_roads["geometry"].within(sfincs_geom)]
            gdf_buildings = gdf[~gdf.isin(gdf_roads)]
            gdf_buildings = gdf_buildings[gdf_buildings[fieldname].isin(bf_fid)]
            idx_buildings = self.fiat_model.exposure.geom_names.index("buildings")
            idx_roads = self.fiat_model.exposure.geom_names.index("roads")
            self.fiat_model.exposure.exposure_geoms[idx_buildings] = gdf_buildings[
                ["Object ID", "geometry"]
            ]
            self.fiat_model.exposure.exposure_geoms[idx_roads] = gdf_roads[
                ["Object ID", "geometry"]
            ]
        else:
            gdf = gdf[gdf[fieldname].isin(bf_fid)]
            self.fiat_model.exposure.exposure_geoms[0] = gdf[["Object ID", "geometry"]]

        # Save exposure dataframe
        del gdf["geometry"]
        self.fiat_model.exposure.exposure_db = gdf

        # Write fiat model
        self.fiat_model.write()

    def _get_default_units(self):
        """
        Retrieve the default units based on the configured GUI unit system.

        Returns
        -------
            dict: A dictionary containing the default units.
        """
        type = self.config.unit_system
        templates_path = Path(__file__).parent.resolve().joinpath("templates")
        default_units = read_toml(
            templates_path.joinpath("default_units", f"{type}.toml")
        )
        return default_units

    def _get_bin_colors(self):
        """
        Retrieve the bin colors from the bin_colors.toml file.

        Returns
        -------
            dict: A dictionary containing the bin colors.
        """
        templates_path = Path(__file__).parent.resolve().joinpath("templates")
        bin_colors = read_toml(
            templates_path.joinpath("mapbox_layers", "bin_colors.toml")
        )
        return bin_colors


def main(config: str | dict):
    """
    Build the FloodAdapt model.

    Args:
        config_path (str): Path to the configuration file.

    Returns
    -------
        None
    """
    # First check if input is dictionary or path
    if isinstance(config, str):
        global config_path
        config_path = config
        config = read_config(config_path)
        print(
            f"Reading FloodAdapt building configuration from {Path(config_path).as_posix()}"
        )
        # If database path is not given use the location of the config file
        if not config.database_path:
            dbs_path = Path(config_path).parent.joinpath("Database")
            if not dbs_path.exists():
                dbs_path.mkdir()
            config.database_path = str(dbs_path.as_posix())
            print(
                f"'database_path' attribute is not provided in the config file. The database will be save at '{config.database_path}'"
            )
    elif isinstance(config, dict):
        config = ConfigModel.model_validate(config)
        print("Reading FloodAdapt building configuration from input dictionary.")
        # If database path is not given raise error
        if not config.database_path:
            raise ValueError(
                "'database_path' attribute needs to be provided in the config file, for the database to be saved."
            )

    # Create a Database object
    dbs = Database(config)
    # Open logger file
    with FloodAdaptLogging.to_file(
        file_path=dbs.root.joinpath("floodadapt_builder.log")
    ):
        # Workflow to create the database using the object methods
        dbs.make_folder_structure()
        dbs.read_sfincs()
        dbs.read_fiat()
        dbs.read_offshore_sfincs()
        dbs.add_dem()
        dbs.update_fiat_elevation()
        dbs.add_rivers()
        dbs.add_obs_points()
        dbs.add_cyclone_dbs()
        dbs.add_static_files()
        dbs.add_tide_gauge()
        dbs.add_gui_params()
        dbs.add_slr()
        # TODO add scs rainfall curves
        dbs.add_general_attrs()
        dbs.add_infometrics()
        dbs.save_site_config()
        dbs.create_standard_objects()
        dbs.logger.info("FloodAdapt database creation finished!")


if __name__ == "__main__":
    while True:
        path = input(
            "Please provide the path to the database creation configuration toml: \n"
        )
        try:
            main(path)
        except Exception as e:
            print(e)
        quit = input("Do you want to quit? (y/n)")
        if quit == "y":
            exit()
