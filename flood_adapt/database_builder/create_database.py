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
from hydromt_fiat.fiat import FiatModel as HydroMtFiatModel
from hydromt_sfincs import SfincsModel as HydroMtSfincsModel
from pydantic import BaseModel, Field
from shapely import MultiPolygon
from shapely.geometry import Polygon

from flood_adapt.adapter.fiat_adapter import _FIAT_COLUMNS
from flood_adapt.api.events import get_event_mode
from flood_adapt.api.projections import create_projection, save_projection
from flood_adapt.api.static import read_database
from flood_adapt.api.strategies import create_strategy, save_strategy
from flood_adapt.misc.config import Settings
from flood_adapt.misc.log import FloodAdaptLogging
from flood_adapt.object_model.hazard.interface.tide_gauge import (
    TideGaugeModel,
    TideGaugeSource,
)
from flood_adapt.object_model.interface.config.fiat import (
    AggregationModel,
    BenefitsModel,
    BFEModel,
    EquityModel,
    FiatConfigModel,
    FiatModel,
    RiskModel,
    SVIModel,
)
from flood_adapt.object_model.interface.config.gui import (
    GuiModel,
    GuiUnitModel,
    MapboxLayersModel,
    PlottingModel,
    SyntheticTideModel,
    VisualizationLayersModel,
)
from flood_adapt.object_model.interface.config.sfincs import (
    CycloneTrackDatabaseModel,
    DatumModel,
    DemModel,
    FloodFrequencyModel,
    FloodModel,
    ObsPointModel,
    RiverModel,
    SfincsConfigModel,
    SfincsModel,
    SlrModel,
    SlrScenariosModel,
    WaterlevelReferenceModel,
)
from flood_adapt.object_model.interface.config.site import (
    Site,
    SiteModel,
    StandardObjectModel,
)
from flood_adapt.object_model.io import unit_system as us

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


class GuiConfigModel(BaseModel):
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


class TideGaugeConfigModel(BaseModel):
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

    source: TideGaugeSource
    file: Optional[str] = None
    max_distance: Optional[us.UnitfulLength] = None
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
        vertical_offset (us.UnitfulLength): The vertical offset of the SLR model, measured in meters.
    """

    vertical_offset: us.UnitfulLength = us.UnitfulLength(
        value=0, units=us.UnitTypesLength.meters
    )


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
    tide_gauge : Optional[TideGaugeConfigModel], default None
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
    obs_point : Optional[list[ObsPointModel]], default None
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
    sfincs_reference: Optional[str] = "MSL"
    sfincs_offshore: Optional[str] = None
    fiat: str
    unit_system: UnitSystems
    gui: GuiConfigModel
    aggregation_areas: Optional[list[SpatialJoinModel]] = None
    building_footprints: Optional[SpatialJoinModel | FootprintsOptions] = (
        FootprintsOptions.OSM
    )
    fiat_buildings_name: Optional[str] = "buildings"
    fiat_roads_name: Optional[str] = "roads"
    slr: Optional[SlrModelDef] = SlrModelDef()
    tide_gauge: Optional[TideGaugeConfigModel] = None
    bfe: Optional[SpatialJoinModel] = None
    svi: Optional[SviModel] = None
    road_width: Optional[float] = 5
    cyclones: Optional[bool] = True
    cyclone_basin: Optional[Basins] = None
    obs_point: Optional[list[ObsPointModel]] = None
    probabilistic_set: Optional[str] = None
    infographics: Optional[bool] = True


def read_toml(fn: Path) -> dict:
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


def read_config(config: Path) -> ConfigModel:
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
    objects_joined = objects.sjoin(layer, how="left", predicate="intersects")

    # Keep only the first intersection for each object
    objects_joined = (
        objects_joined.groupby(_FIAT_COLUMNS.object_id).first().reset_index()
    )

    # if needed filter out unused objects in the layer
    if filter:
        layer_inds = objects_joined["index_right"].dropna().unique()
        layer = layer.iloc[np.sort(layer_inds)].reset_index(drop=True)
    objects_joined = objects_joined[[_FIAT_COLUMNS.object_id, field_name]]
    # rename field if provided
    if rename:
        objects_joined = objects_joined.rename(columns={field_name: rename})
        layer = layer.rename(columns={field_name: rename})
    return objects_joined, layer


def path_check(str_path: str, config_path: Optional[Path] = None) -> str:
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
    path = Path(str_path)
    if not path.is_absolute():
        if config_path is not None:
            path = Path(config_path).parent.joinpath(path).resolve()
        else:
            raise ValueError(f"Value '{path}' should be an absolute path.")
    return str(path)


class DatabaseBuilder:
    """
    The `DatabaseBuilder` class is responsible for creating a FloodAdapt database.

    Args:
        config_path (Path): The path to the configuration file for the database. Contents should adhere to the `ConfigModel` schema.
        overwrite (bool, optional): Whether to overwrite an existing database folder. Defaults to True.
    """

    def __init__(self, config_path: Path, overwrite: bool = False):
        config = read_config(config_path)
        self.config_path = config_path

        if config.database_path is None:
            dbs_path = Path(config_path).parent / "Database"
            if not dbs_path.exists():
                dbs_path.mkdir(parents=True)
        elif not Path(config.database_path).is_absolute():
            dbs_path = (config_path.parent / Path(config.database_path)).resolve()
        else:
            dbs_path = Path(config.database_path).resolve()

        config.database_path = str(dbs_path)
        print(f"Creating FloodAdapt database at {config.database_path}")

        self.config = config
        root = Path(self.config.database_path).joinpath(self.config.name)

        if root.exists() and not overwrite:
            raise ValueError(
                f"There is already a Database folder in '{root.as_posix()}'."
            )
        if root.exists() and overwrite:
            rmtree(root)
        root.mkdir(parents=True)

        self.logger = FloodAdaptLogging.getLogger("DatabaseBuilder")

        self.logger.info(f"Initializing a FloodAdapt database in '{root.as_posix()}'")
        self.root = root
        self.site_attrs = {
            "name": self.config.name,
            "description": self.config.description,
        }
        self.static_path = self.root.joinpath("static")
        self.site_path = self.static_path.joinpath("config")

    def build(self):
        # Open logger file
        with FloodAdaptLogging.to_file(
            file_path=self.root.joinpath("floodadapt_builder.log")
        ):
            # Workflow to create the database using the object methods
            self.make_folder_structure()

            # Set environment variables after folder structure is created
            Settings(DATABASE_ROOT=self.root.parent, DATABASE_NAME=self.root.name)

            self.read_sfincs()
            self.read_fiat()
            self.read_offshore_sfincs()
            self.add_dem()
            self.update_fiat_elevation()
            self.add_rivers()
            self.add_obs_points()
            self.add_cyclone_dbs()
            self.add_static_files()
            self.add_tide_gauge()
            self.add_gui_params()
            self.add_slr()
            # TODO add scs rainfall curves
            self.add_general_attrs()
            self.add_infometrics()
            self.save_config()
            self.create_standard_objects()
            self.logger.info("FloodAdapt database creation finished!")

    def _check_path(self, str_path: str):
        return path_check(str_path, self.config_path)

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
        read_database(self.root.parent, self.config.name)
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
        if len(self.site_attrs["standard_objects"].events) > 0:
            event_set = self.site_attrs["standard_objects"].events[0]
            if event_set:
                mode = get_event_mode(event_set)
                if mode != "risk":
                    self.logger.error(
                        f"Provided probabilistic event set '{event_set}' is not configured correctly! This event should have a risk mode."
                    )

    def _join_building_footprints(
        self, building_footprints: gpd.GeoDataFrame, field_name: str
    ) -> Path:
        """
        Join building footprints with existing building data and updates the exposure CSV.

        Args:
            building_footprints (GeoDataFrame): GeoDataFrame containing the building footprints to be joined.
            field_name (str): The field name to use for the spatial join.

        Returns
        -------
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
        buildings = self.fiat_model.exposure.exposure_geoms[self.build_ind]
        exposure_csv = self.fiat_model.exposure.exposure_db
        buildings_joined, building_footprints = spatial_join(
            buildings,
            building_footprints,
            field_name,
            rename="BF_FID",
            filter=True,
        )
        # Make sure in case of multiple values that the first is kept
        buildings_joined = (
            buildings_joined.groupby(_FIAT_COLUMNS.object_id)
            .first()
            .sort_values(by=[_FIAT_COLUMNS.object_id])
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
        exposure_csv = exposure_csv.merge(
            buildings_joined, on=_FIAT_COLUMNS.object_id, how="left"
        )
        # Set model building footprints
        self.fiat_model.building_footprint = building_footprints
        self.fiat_model.exposure.exposure_db = exposure_csv

        # Save site attributes
        buildings_path = geo_path.relative_to(self.static_path)
        self.logger.info(
            f"Building footprints saved at {self.static_path.joinpath(buildings_path).resolve().as_posix()}"
        )

        return geo_path

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
        self.config.fiat = self._check_path(self.config.fiat)
        path = self.config.fiat
        self.logger.info(f"Reading FIAT model from {Path(path).as_posix()}.")
        # First copy FIAT model to database
        fiat_path = self.root.joinpath("static", "templates", "fiat")
        shutil.copytree(path, fiat_path)

        # Then read the model with hydromt-FIAT
        self.fiat_model = HydroMtFiatModel(root=fiat_path, mode="w+")
        self.fiat_model.read()

        # Make sure only csv objects have geometries
        for i, geoms in enumerate(self.fiat_model.exposure.exposure_geoms):
            keep = geoms[_FIAT_COLUMNS.object_id].isin(
                self.fiat_model.exposure.exposure_db[_FIAT_COLUMNS.object_id]
            )
            geoms = geoms[keep].reset_index(drop=True)
            self.fiat_model.exposure.exposure_geoms[i] = geoms

        # Clip hazard and reset buildings # TODO use hydromt-FIAT instead
        if not self.fiat_model.region.empty:
            self._clip_hazard_extend()

        # Read in geometries of buildings
        build_ind = self.fiat_model.exposure.geom_names.index(
            self.config.fiat_buildings_name
        )
        self.build_ind = build_ind

        # Get center of area of interest
        if not self.fiat_model.region.empty:
            center = self.fiat_model.region.dissolve().centroid.to_crs(4326)[0]
        else:
            center = (
                self.fiat_model.exposure.exposure_geoms[build_ind]
                .dissolve()
                .centroid.to_crs(4326)[0]
            )
        self.site_attrs["lat"] = center.y
        self.site_attrs["lon"] = center.x

        # TODO make footprints an optional argument and use points as the minimum default spatial description
        # TODO restructure footprint options with less if statements

        # First check if the config has a spatial join provided for building footprints
        footprints_found = False
        footprints_path = None
        if not isinstance(self.config.building_footprints, SpatialJoinModel):
            # First check if it is spatially joined already
            check_col = "BF_FID" in self.fiat_model.exposure.exposure_db.columns
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
            if check_file and not check_col:
                self.logger.error(
                    f"Exposure csv is missing the 'BF_FID' column to connect to the footprints located at {footprints_path}."
                )
                raise NotImplementedError
            if check_file and check_col:
                self.logger.info(
                    f"Using the building footprints located at {footprints_path}."
                )
                footprints_found = True

            # Then check if geometries are already footprints
            if isinstance(
                self.fiat_model.exposure.exposure_geoms[build_ind].geometry.iloc[0],
                (Polygon, MultiPolygon),
            ):
                footprints_found = True

            # Else use other method to get Footprint
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
                    footprints_path = self._join_building_footprints(
                        footprints, "BF_FID"
                    )
                    footprints_found = True
            if not footprints_found:
                msg = "No building footprints are available. Buildings will be plotted with a default shape in FloodAdapt."
                self.logger.warning(msg)
        else:
            self.config.building_footprints.file = self._check_path(
                self.config.building_footprints.file
            )
            self.logger.info(
                f"Using building footprints from {Path(self.config.building_footprints.file).as_posix()}."
            )
            # Spatially join buildings and map
            # TODO use hydromt method instead
            footprints_path = self._join_building_footprints(
                self.config.building_footprints.file,
                self.config.building_footprints.field_name,
            )

        # Add base flood elevation information
        if self.config.bfe:
            # TODO can we use hydromt-FIAT?
            self.config.bfe.file = self._check_path(self.config.bfe.file)
            self.logger.info(
                f"Using map from {Path(self.config.bfe.file).as_posix()} as base flood elevation."
            )
            # Spatially join buildings and map
            buildings_joined, bfe = spatial_join(
                self.fiat_model.exposure.exposure_geoms[build_ind],
                self.config.bfe.file,
                self.config.bfe.field_name,
            )
            # Make sure in case of multiple values that the max is kept
            buildings_joined = (
                buildings_joined.groupby(_FIAT_COLUMNS.object_id)
                .max(self.config.bfe.field_name)
                .sort_values(by=[_FIAT_COLUMNS.object_id])
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
            # Save attributes
            bfe_config = BFEModel(
                geom=str(Path(geo_path.relative_to(self.static_path)).as_posix()),
                table=str(Path(csv_path.relative_to(self.static_path)).as_posix()),
                field_name=self.config.bfe.field_name,
            )
        else:
            self.logger.warning(
                "No base flood elevation provided. Elevating building relative to base flood elevation will not be possible in FloodAdapt."
            )
            bfe_config = None

        # Read aggregation areas
        aggregation_config = []

        # If there are no aggregation areas make a schematic one from the region file
        # TODO make aggregation areas not mandatory
        # TODO can we use Hydromt-FIAT
        if self.config.aggregation_areas:
            for aggr in self.config.aggregation_areas:
                # Add column in FIAT
                aggr_name = Path(aggr.file).stem
                exposure_csv = self.fiat_model.exposure.exposure_db
                buildings_joined, aggr_areas = spatial_join(
                    self.fiat_model.exposure.exposure_geoms[build_ind],
                    self._check_path(aggr.file),
                    aggr.field_name,
                    rename=_FIAT_COLUMNS.aggregation_label.format(name=aggr_name),
                )
                aggr_path = Path(self.fiat_model.root).joinpath(
                    "exposure", "aggregation_areas", f"{Path(aggr.file).stem}.gpkg"
                )
                aggr_areas.to_file(aggr_path)
                exposure_csv = exposure_csv.merge(
                    buildings_joined, on=_FIAT_COLUMNS.object_id, how="left"
                )
                self.fiat_model.exposure.exposure_db = exposure_csv
                self.fiat_model.spatial_joins["aggregation_areas"].append(
                    {
                        "name": aggr_name,
                        "file": aggr_path.relative_to(self.fiat_model.root),
                        "field_name": _FIAT_COLUMNS.aggregation_label.format(
                            name=aggr_name
                        ),
                        "equity": None,
                    }
                )

        if (
            not self.fiat_model.spatial_joins["aggregation_areas"]
            and not self.config.aggregation_areas
        ):
            exposure_csv = self.fiat_model.exposure.exposure_db
            region_path = Path(self.fiat_model.root).joinpath("geoms", "region.geojson")
            if region_path.exists():
                region = gpd.read_file(region_path)
                region = region.explode().reset_index()
                region["aggr_id"] = [
                    "region_" + str(i) for i in np.arange(len(region)) + 1
                ]
                aggregation_path = Path(self.fiat_model.root).joinpath(
                    "aggregation_areas", "region.geojson"
                )
                if not aggregation_path.parent.exists():
                    aggregation_path.parent.mkdir()

                region.to_file(aggregation_path)
                aggr = AggregationModel(
                    name="region",
                    file=str(aggregation_path.relative_to(self.static_path).as_posix()),
                    field_name="aggr_id",
                )
                aggregation_config.append(aggr)

                # Add column in FIAT
                buildings_joined, _ = spatial_join(
                    self.fiat_model.exposure.exposure_geoms[build_ind],
                    region,
                    "aggr_id",
                    rename=_FIAT_COLUMNS.aggregation_label.format(name="region"),
                )
                exposure_csv = exposure_csv.merge(
                    buildings_joined, on=_FIAT_COLUMNS.object_id, how="left"
                )
                self.fiat_model.exposure.exposure_db = exposure_csv
                self.logger.warning(
                    "No aggregation areas were available in the FIAT model. The region file will be used as a mock aggregation area."
                )
            else:
                msg = "No aggregation areas were available in the FIAT model and no region geometry file is available. FloodAdapt needs at least one!"
                self.logger.error(msg)
                raise ValueError(msg)
        else:
            for aggr_0 in self.fiat_model.spatial_joins["aggregation_areas"]:
                if aggr_0["equity"] is not None:
                    equity_config = EquityModel(
                        census_data=str(
                            self.static_path.joinpath(
                                "templates", "fiat", aggr_0["equity"]["census_data"]
                            )
                            .relative_to(self.static_path)
                            .as_posix()
                        ),
                        percapitaincome_label=aggr_0["equity"]["percapitaincome_label"],
                        totalpopulation_label=aggr_0["equity"]["totalpopulation_label"],
                    )
                else:
                    equity_config = None

                aggr = AggregationModel(
                    name=aggr_0["name"],
                    file=str(
                        self.static_path.joinpath("templates", "fiat", aggr_0["file"])
                        .relative_to(self.static_path)
                        .as_posix()
                    ),
                    field_name=aggr_0["field_name"],
                    equity=equity_config,
                )
                aggregation_config.append(aggr)
            self.logger.info(
                f"The aggregation types {[aggr['name'] for aggr in self.fiat_model.spatial_joins['aggregation_areas']]} from the FIAT model are going to be used."
            )

        # Read SVI
        svi_config = None
        if self.config.svi:
            self.config.svi.file = self._check_path(self.config.svi.file)
            exposure_csv = self.fiat_model.exposure.exposure_db
            buildings_joined, svi = spatial_join(
                self.fiat_model.exposure.exposure_geoms[build_ind],
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
                buildings_joined, on=_FIAT_COLUMNS.object_id, how="left"
            )
            self.fiat_model.exposure.exposure_db = exposure_csv
            # Create folder
            svi_folder = self.root.joinpath("static", "templates", "fiat", "svi")
            svi_folder.mkdir()
            # Save the spatial file for future use
            svi_path = svi_folder.joinpath("svi.gpkg")
            svi.to_file(svi_path)
            self.logger.info(
                f"An SVI map can be shown in FloodAdapt GUI using '{self.config.svi.field_name}' column from {Path(self.config.svi.file).as_posix()}"
            )
            # Save site attributes
            svi_config = SVIModel(
                geom=str(Path(svi_path.relative_to(self.static_path)).as_posix()),
                field_name="SVI",
            )
        elif "SVI" in self.fiat_model.exposure.exposure_db.columns:
            self.logger.info("'SVI' column present in the FIAT exposure csv.")
            add_attrs = self.fiat_model.spatial_joins["additional_attributes"]
            if "SVI" in [attr["name"] for attr in add_attrs]:
                ind = [attr["name"] for attr in add_attrs].index("SVI")
                svi = add_attrs[ind]
                svi_path = fiat_path.joinpath(svi["file"])
                self.logger.info(
                    f"An SVI map can be shown in FloodAdapt GUI using '{svi['field_name']}' column from {svi['file']}"
                )
                # Save site attributes
                svi_config = SVIModel(
                    geom=str(Path(svi_path.relative_to(self.static_path)).as_posix()),
                    field_name=svi["field_name"],
                )
            else:
                self.logger.warning("No SVI map found!")
        else:
            self.logger.warning(
                "'SVI' column not present in the FIAT exposure csv. Vulnerability type infometrics cannot be produced."
            )

        # Make sure that FIAT roads are polygons
        self.roads = False
        if self.config.fiat_roads_name in self.fiat_model.exposure.geom_names:
            self.roads = True
            roads_ind = self.fiat_model.exposure.geom_names.index(
                self.config.fiat_roads_name
            )
            roads = self.fiat_model.exposure.exposure_geoms[roads_ind]
            roads_geom_filename = self.fiat_model.config["exposure"]["geom"][
                f"file{roads_ind+1}"
            ]
            roads_path = Path(self.fiat_model.root).joinpath(roads_geom_filename)

            # TODO do we need the lanes column?
            if (
                _FIAT_COLUMNS.segment_length
                not in self.fiat_model.exposure.exposure_db.columns
            ):
                self.logger.warning(
                    f"'{_FIAT_COLUMNS.segment_length}' column not present in the FIAT exposure csv. Road impact infometrics cannot be produced."
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
                self.fiat_model.exposure.exposure_geoms[roads_ind] = roads
                self.logger.info(
                    f"FIAT road objects transformed from lines to polygons assuming a road width of {self.config.road_width} meters."
                )
        else:
            self.logger.warning(
                "Road objects are not available in the FIAT model and thus would not be available in FloodAdapt."
            )
            # TODO check how this naming of output geoms should become more explicit!

        if self.fiat_model.exposure.damage_unit is not None:
            dmg_unit = self.fiat_model.exposure.damage_unit
        else:
            dmg_unit = "$"
            self.logger.warning(
                "Delft-FIAT model was missing damage units so '$' was assumed."
            )

        # If there is at least on object that uses the area method, use water depths for FA calcs
        if (
            self.fiat_model.exposure.exposure_db[_FIAT_COLUMNS.extraction_method]
            == "area"
        ).any():
            floodmap_type = "water_depth"
        else:
            floodmap_type = "water_level"

        # Update output geoms names
        output_geom = {}
        counter = 0
        for key in self.fiat_model.config["exposure"]["geom"].keys():
            if "file" in key:
                counter += 1
                output_geom[f"name{counter}"] = Path(
                    self.fiat_model.config["exposure"]["geom"][key]
                ).name
        self.fiat_model.config["output"]["geom"] = output_geom
        self.fiat_model.write()

        if footprints_path is not None:
            footprints_path = (
                Path(footprints_path).relative_to(self.static_path).as_posix()
            )

        # Store FIAT configuration
        self.site_attrs["fiat"] = {}
        self.site_attrs["fiat"]["config"] = FiatConfigModel(
            exposure_crs=self.fiat_model.exposure.crs,
            bfe=bfe_config,
            aggregation=aggregation_config,
            floodmap_type=floodmap_type,
            non_building_names=["road"],  # TODO check names from exposure
            damage_unit=dmg_unit,
            building_footprints=footprints_path,
            roads_file_name=f"{self.config.fiat_roads_name}.gpkg"
            if self.roads
            else None
            if self.roads
            else None,
            new_development_file_name="new_development_area.gpkg",  # TODO allow for different naming
            save_simulation=False,  # default is not to save simulations
            svi=svi_config,
            infographics=True if self.config.infographics else False,
        )

    def read_sfincs(self):
        """
        Read the SFINCS model and sets the necessary attributes for the site configuration.

        This method performs the following steps:
        1. Copies the sfincs model to the database.
        2. Reads the model using hydromt-SFINCS.
        3. Sets the necessary attributes for the site configuration.
        """
        self.config.sfincs = self._check_path(self.config.sfincs)
        path = self.config.sfincs

        # First copy sfincs model to database
        sfincs_path = self.root.joinpath("static", "templates", "overland")
        shutil.copytree(path, sfincs_path)

        # Then read the model with hydromt-SFINCS
        self.sfincs = HydroMtSfincsModel(root=sfincs_path, mode="r+")
        self.sfincs.read()
        self.logger.info(
            f"Reading overland SFINCS model from {sfincs_path.as_posix()}."
        )

        # Store SFINCS config
        off_model = (
            FloodModel(name="offshore", reference="MSL")
            if self.config.sfincs_offshore
            else None
        )
        overland_model = FloodModel(
            name="overland", reference=self.config.sfincs_reference
        )
        self.site_attrs["sfincs"] = {}
        self.site_attrs["sfincs"]["config"] = SfincsConfigModel(
            csname=self.sfincs.crs.name,
            cstype=self.sfincs.crs.type_name.split(" ")[0].lower(),
            offshore_model=off_model,
            overland_model=overland_model,
            floodmap_units=us.UnitTypesLength.feet
            if self.config.unit_system == UnitSystems.imperial
            else us.UnitTypesLength.meters,
            save_simulation=False,  # for now this defaults to False
        )

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
        self.config.sfincs_offshore = self._check_path(self.config.sfincs_offshore)
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
        src_file = Path(self.sfincs.root).joinpath("sfincs.src")
        if not src_file.exists():
            self.site_attrs["sfincs"]["river"] = None
            self.logger.warning("No rivers found in the SFINCS model.")
            return
        df = pd.read_csv(src_file, delim_whitespace=True, header=None, names=["x", "y"])
        river_locs = gpd.GeoDataFrame(
            df, geometry=gpd.points_from_xy(df.x, df.y), crs=self.sfincs.crs
        )
        rivers = []

        dis_values = "dis" in self.sfincs.forcing

        for i, row in river_locs.iterrows():
            if dis_values:
                val = (
                    self.sfincs.forcing["dis"].sel(index=i + 1).to_numpy().mean()
                )  # sfincs has 1 based-indexing
            else:
                val = 0.0
            mean_dis = us.UnitfulDischarge(
                value=val,
                units=us.UnitTypesDischarge.cms,
            )
            if self.config.unit_system == UnitSystems.imperial:
                mean_dis = us.UnitfulDischarge(
                    value=mean_dis.convert(us.UnitTypesDischarge.cfs),
                    units=us.UnitTypesDischarge.cfs,
                )
            river = RiverModel(
                name=f"river_{i}",
                description=f"river_{i}",
                x_coordinate=row.geometry.x,
                y_coordinate=row.geometry.y,
                mean_discharge=mean_dis,
            )

            rivers.append(river)
        self.logger.warning(
            f"{len(river_locs)} river(s) were identified from the SFINCS model and will be available in FloodAdapt for discharge input."
        )
        self.site_attrs["sfincs"]["river"] = rivers
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
            msg = (
                f"A subgrid depth geotiff file should be available at {subgrid_sfincs}."
            )
            self.logger.error(msg)
            raise ValueError(msg)

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
        self.site_attrs["sfincs"]["dem"] = DemModel(
            filename=fn,
            units=us.UnitTypesLength.meters,  # This is always in meters from SFINCS
        )

    def update_fiat_elevation(self):
        """
        Update the ground elevations of FIAT objects based on the SFINCS ground elevation map.

        This method reads the DEM file and the exposure CSV file, and updates the ground elevations
        of the FIAT objects (roads and buildings) based on the nearest elevation values from the DEM.
        """
        dem_file = self.static_path.joinpath(
            "dem", self.site_attrs["sfincs"]["dem"].filename
        )
        # TODO resolve issue with double geometries in hydromt-FIAT and use update_ground_elevation method instead
        # self.fiat_model.update_ground_elevation(dem_file)
        self.logger.info(
            "Updating FIAT objects ground elevations from SFINCS ground elevation map."
        )
        SFINCS_units = us.UnitfulLength(
            value=1.0, units=us.UnitTypesLength.meters
        )  # SFINCS is always in meters
        FIAT_units = self.site_attrs["sfincs"]["config"].floodmap_units
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
        # TODO this should be in hydromt FIAT
        if self.config.fiat_roads_name in self.fiat_model.exposure.geom_names:
            roads_path = (
                Path(self.fiat_model.root)
                / "exposure"
                / f"{self.config.fiat_roads_name}.gpkg"
            )
            roads = gpd.read_file(roads_path).to_crs(dem.spatial_ref.crs_wkt)
            roads["geometry"] = roads.geometry.centroid  # get centroids

            x_points = xr.DataArray(roads["geometry"].x, dims="points")
            y_points = xr.DataArray(roads["geometry"].y, dims="points")
            roads["elev"] = (
                dem.sel(x=x_points, y=y_points, band=1, method="nearest").to_numpy()
                * conversion_factor
            )

            exposure.loc[
                exposure[_FIAT_COLUMNS.primary_object_type] == "road",
                _FIAT_COLUMNS.ground_floor_height,
            ] = 0
            exposure = exposure.merge(
                roads[[_FIAT_COLUMNS.object_id, "elev"]],
                on=_FIAT_COLUMNS.object_id,
                how="left",
            )
            exposure.loc[
                exposure[_FIAT_COLUMNS.primary_object_type] == "road",
                _FIAT_COLUMNS.ground_elevation,
            ] = exposure.loc[
                exposure[_FIAT_COLUMNS.primary_object_type] == "road", "elev"
            ]
            del exposure["elev"]

        buildings_path = (
            Path(self.fiat_model.root)
            / "exposure"
            / f"{self.config.fiat_buildings_name}.gpkg"
        )
        points = gpd.read_file(buildings_path).to_crs(dem.spatial_ref.crs_wkt)
        points["geometry"] = points.geometry.centroid
        x_points = xr.DataArray(points["geometry"].x, dims="points")
        y_points = xr.DataArray(points["geometry"].y, dims="points")
        points["elev"] = (
            dem.sel(x=x_points, y=y_points, band=1, method="nearest").to_numpy()
            * conversion_factor
        )
        exposure = exposure.merge(
            points[[_FIAT_COLUMNS.object_id, "elev"]],
            on=_FIAT_COLUMNS.object_id,
            how="left",
        )
        exposure.loc[
            exposure[_FIAT_COLUMNS.primary_object_type] != "road",
            _FIAT_COLUMNS.ground_elevation,
        ] = exposure.loc[exposure[_FIAT_COLUMNS.primary_object_type] != "road", "elev"]
        del exposure["elev"]

        exposure.to_csv(exposure_csv_path, index=False)

    def add_cyclone_dbs(self):
        """
        Download and adds a cyclone track database to the site attributes.

        If the `cyclone_basin` configuration is provided, it downloads the cyclone track database for the specified basin.
        Otherwise, it downloads the cyclone track database for all basins.

        The downloaded database is stored in the 'static/cyclone_track_database' directory.
        """
        self.site_attrs["sfincs"]["cyclone_track_database"] = None
        if not self.config.cyclones or not self.config.sfincs_offshore:
            self.logger.warning("No cyclones will be available in the database.")
            return
        if self.config.cyclone_basin:
            basin = self.config.cyclone_basin
        else:
            basin = "ALL"
        name = f"IBTrACS.{basin}.v04r01.nc"
        url = f"https://www.ncei.noaa.gov/data/international-best-track-archive-for-climate-stewardship-ibtracs/v04r01/access/netcdf/{name}"
        self.logger.info(f"Downloading cyclone track database from {url}")
        fn = self.root.joinpath("static", "cyclone_track_database", name)
        fn.parent.mkdir()
        try:
            urlretrieve(url, fn)
        except Exception as e:
            print(e)
            self.logger.error(f"Could not retrieve cyclone track database from {url}")

        # Store config
        self.site_attrs["sfincs"]["cyclone_track_database"] = CycloneTrackDatabaseModel(
            file=name
        )

    def add_tide_gauge(self):
        """
        Add water level information to the site attributes.

        This method adds water level information to the `site_attrs` dictionary.
        It sets default values for the water level reference, MSL (Mean Sea Level),
        and local datum. The height values are set to 0 by default.
        """
        # Start by defining default values for water levels
        # In case no further information is provided a local datum and msl of 0 will be assumed
        elv_units = self.site_attrs["sfincs"]["config"].floodmap_units
        water_level_config = WaterlevelReferenceModel(
            reference="MSL",  # TODO allow users to configure
            datums=[
                DatumModel(
                    name="MSL", height=us.UnitfulLength(value=0.0, units=elv_units)
                ),
            ],
        )

        zero_wl_msg = "No water level references were found. It is assumed that MSL is equal to the datum used in the SFINCS overland model. You can provide these values with the tide_gauge.msl and tide_gauge.datum attributes in the site.toml."

        # Then check if there is any extra configurations given
        if self.config.tide_gauge is None:
            self.logger.warning(
                "Tide gauge information not provided. Historical nearshore gauged events will not be available in FloodAdapt!"
            )
            self.site_attrs["sfincs"]["tide_gauge"] = None
            self.logger.warning(zero_wl_msg)
        else:
            if self.config.tide_gauge.source != TideGaugeSource.file:
                if self.config.tide_gauge.ref is not None:
                    ref = self.config.tide_gauge.ref
                else:
                    ref = "MLLW"  # If reference is not provided use MLLW
                water_level_config.reference = ref
                station = self._get_closest_station(
                    ref
                )  # This always return values in meters currently
                if station is not None:
                    # Add tide_gauge information in site toml
                    self.site_attrs["sfincs"]["tide_gauge"] = TideGaugeModel(
                        name=station["name"],
                        description=f"observations from '{self.config.tide_gauge.source}' api",
                        source=self.config.tide_gauge.source,
                        reference="MSL",
                        ID=int(station["id"]),
                        lon=station["lon"],
                        lat=station["lat"],
                        units=us.UnitTypesLength.meters,
                    )

                    local_datum = DatumModel(
                        name=station["datum_name"],
                        height=us.UnitfulLength(
                            value=station["datum"], units=station["units"]
                        ).transform(elv_units),
                    )
                    # Make sure existing MSL datum is overwritten
                    water_level_config.datums = [
                        datum
                        for datum in water_level_config.datums
                        if datum.name != "MSL"
                    ]
                    water_level_config.datums.append(local_datum)

                    msl = DatumModel(
                        name="MSL",
                        height=us.UnitfulLength(
                            value=station["msl"], units=station["units"]
                        ).transform(elv_units),
                    )

                    water_level_config.datums.append(msl)

                    for name in ["MLLW", "MHHW"]:
                        height = us.UnitfulLength(
                            value=station[name.lower()], units=station["units"]
                        ).transform(elv_units)

                        wl_info = DatumModel(
                            name=name,
                            height=height,
                        )
                        water_level_config.datums.append(wl_info)
                else:
                    self.logger.warning(zero_wl_msg)
            if self.config.tide_gauge.source == "file":
                self.config.tide_gauge.file = self._check_path(
                    self.config.tide_gauge.file
                )
                file_path = Path(self.static_path).joinpath(
                    "tide_gauges", Path(self.config.tide_gauge.file).name
                )
                if not file_path.parent.exists():
                    file_path.parent.mkdir()
                shutil.copyfile(self.config.tide_gauge.file, file_path)
                self.site_attrs["sfincs"]["tide_gauge"] = TideGaugeModel(
                    description="observations from file stored in database",
                    source="file",
                    file=str(Path(file_path.relative_to(self.static_path)).as_posix()),
                    units=us.UnitTypesLength.meters,
                )
                self.logger.warning(zero_wl_msg)

        # store config
        self.site_attrs["sfincs"]["water_level"] = (
            WaterlevelReferenceModel.model_validate(water_level_config)
        )

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
        units = self.site_attrs["sfincs"]["config"].floodmap_units
        distance = us.UnitfulLength(value=distance, units=us.UnitTypesLength.meters)
        self.logger.info(
            f"The closest tide gauge from {self.config.tide_gauge.source} is located {distance.convert(units)} {units} from the SFINCS domain"
        )
        # Check if user provided max distance
        # TODO make sure units are explicit for max_distance
        if self.config.tide_gauge.max_distance is not None:
            units_new = self.config.tide_gauge.max_distance.units
            distance_new = us.UnitfulLength(
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
        meta["units"] = station_metadata["datums"]["units"]
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

        # Make sure units are consistent and make config
        vertical_offset = us.UnitfulLength(
            value=self.config.slr.vertical_offset.convert(
                self.site_attrs["sfincs"]["config"].floodmap_units
            ),
            units=self.site_attrs["sfincs"]["config"].floodmap_units,
        )

        # If slr scenarios are given put them in the correct locations
        if self.config.slr.scenarios:
            self.config.slr.scenarios.file = self._check_path(
                self.config.slr.scenarios.file
            )
            slr_path = self.static_path.joinpath("slr")
            slr_path.mkdir()
            new_file = slr_path.joinpath(Path(self.config.slr.scenarios.file).name)
            # copy file
            shutil.copyfile(self.config.slr.scenarios.file, new_file)
            # make config
            slr_scenarios = SlrScenariosModel(
                file=new_file.relative_to(self.static_path).as_posix(),
                relative_to_year=self.config.slr.scenarios.relative_to_year,
            )
        else:
            slr_scenarios = None
        # store config
        self.site_attrs["sfincs"]["slr"] = SlrModel(
            vertical_offset=vertical_offset, scenarios=slr_scenarios
        )

    def add_obs_points(self):
        """
        Add observation points to the site attributes.

        This method iterates over the `obs_point` list in the `config` object and appends the model dump of each observation point
        to the `obs_point` attribute in the `site_attrs` dictionary.
        """
        if self.config.obs_point is not None:
            self.logger.info("Observation points were provided in the config file.")
            # Store config
            self.site_attrs["sfincs"]["obs_point"] = self.config.obs_point
        else:
            self.site_attrs["sfincs"]["obs_point"] = None

    def add_gui_params(self):
        """
        Add GUI parameters to the site attributes dictionary.

        This method reads default units from a template, sets default values for tide, reads default colors from the template,
        derives bins from the config max attributes, and adds visualization layers.
        """
        # Read default units from template
        units = GuiUnitModel(**self._get_default_units())

        # Check if the water level attribute include info on MHHW and MSL
        datums = self.site_attrs["sfincs"]["water_level"].datums

        if "MHHW" in [d.name for d in datums]:
            amplitude = (
                self.site_attrs["sfincs"]["water_level"].get_datum("MHHW").height.value
                - self.site_attrs["sfincs"]["water_level"].get_datum("MSL").height.value
            )
            self.logger.info(
                f"The default tidal amplitude in the GUI will be {amplitude} {units.default_length_units.value}, calculated as the difference between MHHW and MSL from the tide gauge data."
            )
        else:
            amplitude = 0.0
            self.logger.warning(
                "The default tidal amplitude in the GUI will be 0.0, since no tide-gauge water levels are available. You can change this in the site.toml with the 'gui.tide_harmonic_amplitude' attribute."
            )
        default_tide_harmonic_amplitude = us.UnitfulLength(
            value=np.round(amplitude, 3), units=units.default_length_units
        )

        # Read default colors from template
        fd_max = self.config.gui.max_flood_depth
        ad_max = self.config.gui.max_aggr_dmg
        ftd_max = self.config.gui.max_footprint_dmg
        b_max = self.config.gui.max_benefits
        mapbox_layers = MapboxLayersModel(
            flood_map_depth_min=0.0,  # mask areas with flood depth lower than this (zero = all depths shown) # TODO How to define this?
            flood_map_zbmax=-9999,  # mask areas with elevation lower than this (very negative = show all calculated flood depths) # TODO How to define this?,
            flood_map_bins=[0.2 * fd_max, 0.6 * fd_max, fd_max],
            damage_decimals=0,
            footprints_dmg_type="absolute",
            aggregation_dmg_bins=[
                0.00001,
                0.1 * ad_max,
                0.25 * ad_max,
                0.5 * ad_max,
                ad_max,
            ],
            footprints_dmg_bins=[
                0.00001,
                0.06 * ftd_max,
                0.2 * ftd_max,
                0.4 * ftd_max,
                ftd_max,
            ],
            benefits_bins=[0, 0.01, 0.02 * b_max, 0.2 * b_max, b_max],
            svi_bins=[0.05, 0.2, 0.4, 0.6, 0.8]
            if hasattr(self.site_attrs["fiat"]["config"], "svi")
            else None,
            **self._get_bin_colors(),
        )

        # Add visualization layers
        # TODO add option to input layer
        visualization_layers = VisualizationLayersModel(
            default_bin_number=4,
            default_colors=["#FFFFFF", "#FEE9CE", "#E03720", "#860000"],
        )

        plotting = PlottingModel(
            excluded_datums=["NAVD88"],
            synthetic_tide=SyntheticTideModel(
                harmonic_amplitude=default_tide_harmonic_amplitude,
                datum="MSL",
            ),
        )

        # Store config
        self.site_attrs["gui"] = GuiModel(
            units=units,
            plotting=plotting,
            mapbox_layers=mapbox_layers,
            visualization_layers=visualization_layers,
        )

    def add_general_attrs(self):
        """
        Add general attributes to the site_attrs dictionary.

        This method adds various attributes related to risk, standard objects, and benefits
        to the site_attrs dictionary.
        """
        self.site_attrs["fiat"]["risk"] = RiskModel(
            return_periods=[1, 2, 5, 10, 25, 50, 100]
        )  # TODO this could be an input?

        self.site_attrs["sfincs"]["flood_frequency"] = FloodFrequencyModel(
            flooding_threshold=us.UnitfulLength(
                value=0.0, units=self.site_attrs["sfincs"]["config"].floodmap_units
            )  # TODO this could be an input?
        )

        # Copy prob set if given
        if self.config.probabilistic_set:
            self.config.probabilistic_set = self._check_path(
                self.config.probabilistic_set
            )
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

        self.site_attrs["standard_objects"] = StandardObjectModel(
            events=[prob_event_name] if self.config.probabilistic_set else [],
            projections=["current"],
            strategies=["no_measures"],
        )
        # TODO how to define the benefit objects?
        self.site_attrs["fiat"]["benefits"] = BenefitsModel(
            current_year=2023,
            current_projection="current",
            baseline_strategy="no_measures",
            event_set=prob_event_name if self.config.probabilistic_set else "",
        )

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

            if self.site_attrs["fiat"]["config"].svi is not None:
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

        path = self.root.joinpath("static", "templates", "infometrics")
        files = list(path.glob("*metrics_config*.toml"))
        # Update aggregation areas in metrics config
        for file in files:
            file = path.joinpath(file)
            attrs = read_toml(file)
            # add aggration levels
            attrs["aggregateBy"] = [
                aggr.name for aggr in self.site_attrs["fiat"]["config"].aggregation
            ]
            # take out road metrics if needed
            if not self.roads:
                attrs["queries"] = [
                    query
                    for query in attrs["queries"]
                    if "road" not in query["name"].lower()
                ]
            # Replace Damage Unit
            # TODO do this in a better manner
            for i, query in enumerate(attrs["queries"]):
                if "$" in query["long_name"]:
                    query["long_name"] = query["long_name"].replace(
                        "$", self.site_attrs["fiat"]["config"].damage_unit
                    )

            # replace the SVI threshold if needed
            if self.config.svi:
                for i, query in enumerate(attrs["queries"]):
                    query["filter"] = query["filter"].replace(
                        "SVI_threshold", str(self.config.svi.threshold)
                    )
            with open(file, "wb") as f:
                tomli_w.dump(attrs, f)

    def save_config(self):
        """
        Save the site configuration to a TOML file.

        This method creates a TOML file at the specified location and saves the site configuration
        using the `Site` class. The site configuration is obtained from the `site_attrs` attribute.
        """
        # Define save locations for the config
        site_config_path = self.root.joinpath("static", "config", "site.toml")
        site_config_path.parent.mkdir()

        # Create and validate object for config
        site = SiteModel(
            name=self.site_attrs["name"],
            description=self.site_attrs["description"],
            lat=self.site_attrs["lat"],
            lon=self.site_attrs["lon"],
            standard_objects=self.site_attrs["standard_objects"],
            gui=self.site_attrs["gui"],
            sfincs=SfincsModel(
                config=self.site_attrs["sfincs"]["config"],
                water_level=self.site_attrs["sfincs"]["water_level"],
                cyclone_track_database=self.site_attrs["sfincs"][
                    "cyclone_track_database"
                ],
                slr=self.site_attrs["sfincs"]["slr"],
                # scs = SCSModel,  # optional for the US to use SCS rainfall curves
                dem=self.site_attrs["sfincs"]["dem"],
                flood_frequency=self.site_attrs["sfincs"]["flood_frequency"],
                tide_gauge=self.site_attrs["sfincs"]["tide_gauge"],
                river=self.site_attrs["sfincs"]["river"],
                obs_point=self.site_attrs["sfincs"]["obs_point"],
            ),
            fiat=FiatModel(
                config=self.site_attrs["fiat"]["config"],
                risk=self.site_attrs["fiat"]["risk"],
                benefits=self.site_attrs["fiat"]["benefits"],
            ),
        )

        # Save configs
        site_obj = Site.load_dict(site)
        site_obj.save(site_config_path)

    @staticmethod
    def _clip_gdf(
        gdf1: gpd.GeoDataFrame, gdf2: gpd.GeoDataFrame, predicate: str = "within"
    ):
        gdf_new = gpd.sjoin(gdf1, gdf2, how="inner", predicate=predicate)
        gdf_new = gdf_new.drop(
            columns=[
                col
                for col in gdf_new.columns
                if col.endswith("_right") or (col in gdf2.columns and col != "geometry")
            ]
        )

        return gdf_new

    def _clip_hazard_extend(self, clip_footprints=True):
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

        # Clip the fiat region
        clipped_region = self.fiat_model.region.to_crs(crs).clip(sfincs_extend)
        self.fiat_model.geoms["region"] = clipped_region

        # Clip the exposure geometries
        # Filter buildings and roads
        road_inds = gdf[_FIAT_COLUMNS.primary_object_type].str.contains("road")
        # Ensure road_inds is a boolean Series
        if not road_inds.dtype == bool:
            road_inds = road_inds.astype(bool)
        # Clip buildings
        gdf_buildings = gdf[~road_inds]
        gdf_buildings = self._clip_gdf(
            gdf_buildings, clipped_region, predicate="within"
        ).reset_index(drop=True)

        if road_inds.any():
            # Clip roads
            gdf_roads = gdf[road_inds]
            gdf_roads = self._clip_gdf(
                gdf_roads, clipped_region, predicate="within"
            ).reset_index(drop=True)

            idx_buildings = self.fiat_model.exposure.geom_names.index(
                self.config.fiat_buildings_name
            )
            idx_roads = self.fiat_model.exposure.geom_names.index(
                self.config.fiat_roads_name
            )
            self.fiat_model.exposure.exposure_geoms[idx_buildings] = gdf_buildings[
                [_FIAT_COLUMNS.object_id, "geometry"]
            ]
            self.fiat_model.exposure.exposure_geoms[idx_roads] = gdf_roads[
                [_FIAT_COLUMNS.object_id, "geometry"]
            ]
            gdf = pd.concat([gdf_buildings, gdf_roads])
        else:
            gdf = gdf_buildings
            self.fiat_model.exposure.exposure_geoms[0] = gdf[
                [_FIAT_COLUMNS.object_id, "geometry"]
            ]

        # Save exposure dataframe
        del gdf["geometry"]
        self.fiat_model.exposure.exposure_db = gdf

        # Clip the building footprints
        fieldname = "BF_FID"
        if clip_footprints and not self.fiat_model.building_footprint.empty:
            # Get buildings after filtering and their footprint id
            self.fiat_model.building_footprint = self.fiat_model.building_footprint[
                self.fiat_model.building_footprint[fieldname].isin(
                    gdf_buildings[fieldname]
                )
            ]

    def _get_default_units(self):
        """
        Retrieve the default units based on the configured GUI unit system.

        Returns
        -------
            dict: A dictionary containing the default units.
        """
        units_path = (
            Path(__file__).parent.resolve()
            / "templates"
            / "default_units"
            / f"{self.config.unit_system.value}.toml"
        )
        return read_toml(units_path)

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


if __name__ == "__main__":
    while True:
        config_path = Path(
            input(
                "Please provide the path to the database creation configuration toml: \n"
            )
        )
        try:
            dbs = DatabaseBuilder(config_path=config_path)
            dbs.build()
        except Exception as e:
            print(e)
        quit = input("Do you want to quit? (y/n)")
        if quit == "y":
            exit()
