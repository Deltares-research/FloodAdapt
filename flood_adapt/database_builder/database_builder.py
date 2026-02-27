import datetime
import gc
import logging
import math
import re
import shutil
import warnings
from enum import Enum
from pathlib import Path
from typing import Literal, Optional, Union
from urllib.request import urlretrieve

import cht_observations.observation_stations as obs
import geopandas as gpd
import numpy as np
import pandas as pd
import rioxarray as rxr
import xarray as xr
from hydromt_fiat import FiatModel as HydromtFiatModel
from hydromt_fiat.data_apis.open_street_maps import get_buildings_from_osm
from hydromt_sfincs import SfincsModel as HydromtSfincsModel
from hydromt_sfincs.workflows.downscaling import make_index_cog
from pydantic import BaseModel, Field, model_validator
from shapely import MultiLineString, MultiPolygon, Polygon
from shapely.ops import nearest_points

from flood_adapt.adapter.fiat_adapter import _FIAT_COLUMNS
from flood_adapt.config.fiat import (
    FiatConfigModel,
    FiatModel,
)
from flood_adapt.config.gui import (
    AggregationDmgLayer,
    BenefitsLayer,
    FieldName,
    FilterCondition,
    FilterGroup,
    FloodMapLayer,
    FootprintsDmgLayer,
    GuiModel,
    GuiUnitModel,
    LogicalOperator,
    MetricLayer,
    OutputLayers,
    PlottingModel,
    SyntheticTideModel,
    VisualizationLayers,
)
from flood_adapt.config.hazard import (
    Cstype,
    CycloneTrackDatabaseModel,
    DatumModel,
    DemModel,
    FloodModel,
    ObsPointModel,
    RiverModel,
    SCSModel,
    SlrScenariosModel,
    WaterlevelReferenceModel,
)
from flood_adapt.config.impacts import (
    AggregationModel,
    BenefitsModel,
    BFEModel,
    EquityModel,
    FloodmapType,
    RiskModel,
    SVIModel,
)
from flood_adapt.config.sfincs import (
    SfincsConfigModel,
    SfincsModel,
)
from flood_adapt.config.site import (
    Site,
    StandardObjectModel,
)
from flood_adapt.database_builder.metrics_utils import (
    BuildingsInfographicModel,
    EventInfographicModel,
    HomesInfographicModel,
    MetricModel,
    Metrics,
    RiskInfographicModel,
    RoadsInfographicModel,
)
from flood_adapt.dbs_classes.database import Database
from flood_adapt.misc.debug_timer import debug_timer
from flood_adapt.misc.io import read_toml, write_toml
from flood_adapt.misc.log import FloodAdaptLogging
from flood_adapt.misc.utils import modified_environ
from flood_adapt.objects.events.event_set import EventSet
from flood_adapt.objects.forcing import unit_system as us
from flood_adapt.objects.forcing.tide_gauge import (
    TideGauge,
    TideGaugeSource,
)
from flood_adapt.objects.projections.projections import (
    PhysicalProjection,
    Projection,
    SocioEconomicChange,
)
from flood_adapt.objects.strategies.strategies import Strategy

logger = FloodAdaptLogging.getLogger("DatabaseBuilder")


def path_check(str_path: str, config_path: Optional[Path] = None) -> str:
    """Check if the given path is absolute and return the absolute path.

    Parameters
    ----------
    str_path : str
        The path to be checked.
    config_path : Optional[Path], default None
        The base path to resolve relative paths.

    Returns
    -------
    str
        The absolute path as a string.

    Raises
    ------
    ValueError
        If the path is not absolute and no config_path is provided.
    """
    path = Path(str_path)
    if not path.is_absolute():
        if config_path is not None:
            path = Path(config_path).parent.joinpath(path).resolve()
        else:
            raise ValueError(f"Value '{path}' should be an absolute path.")
    return path.as_posix()


def make_relative(str_path: str | Path, toml_path: Path) -> str:
    """Make a path relative to the config file path.

    Parameters
    ----------
    str_path : str | Path
        The path to be made relative.
    toml_path : Path
        The path to the config file.

    Returns
    -------
    str
        The relative path as a string.
    """
    path = Path(str_path)
    if not path.is_absolute():
        return path.as_posix()
    try:
        relative_path = path.relative_to(toml_path.parent)
        return relative_path.as_posix()
    except ValueError:
        return path.as_posix()


class SpatialJoinModel(BaseModel):
    """
    Model for representing a spatial join between geometries and tabular data.

    Attributes
    ----------
    file : str
        Path to the file containing the spatial data to join.
    field_name : str
        Name of the field used for joining.
    name : Optional[str]
        Name of the spatial join (optional).
    units : Optional[us.UnitfulLength]
        Unit system for the spatial data (optional).
    """

    file: str
    field_name: str
    name: Optional[str] = None
    units: Optional[us.UnitfulLength] = None


class UnitSystems(str, Enum):
    """
    Enumeration for supported unit systems.

    Values
    ------
    imperial : Imperial units (feet, miles, etc.)
    metric : Metric units (meters, kilometers, etc.)
    """

    imperial = "imperial"
    metric = "metric"


class FootprintsOptions(str, Enum):
    """
    Enumeration for building footprints data sources.

    Values
    ------
    OSM : Use OpenStreetMap for building footprints.
    """

    OSM = "OSM"


class Basins(str, Enum):
    """
    Enumeration of global cyclone basins.

    Values
    ------
    NA : North Atlantic
    SA : South Atlantic
    EP : Eastern North Pacific (includes Central Pacific)
    WP : Western North Pacific
    SP : South Pacific
    SI : South Indian
    NI : North Indian
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
    Configuration for FloodAdapt GUI visualization scaling.

    Attributes
    ----------
    max_flood_depth : float
        Maximum flood depth for visualization bins (last bin is ">value").
    max_aggr_dmg : float
        Maximum aggregated damage for visualization bins.
    max_footprint_dmg : float
        Maximum footprint damage for visualization bins.
    max_benefits : float
        Maximum benefits for visualization bins.
    additional_aggregated_layers : Optional[list[MetricLayer]]
        Additional metric layers for aggregation (optional).
    topobathy_min_max : Union[tuple[float, float], Literal["dem"]]
        Min/max values for DEM color scaling; set to "dem" to derive from the
        elevation raster or provide explicit bounds in GUI units.
    """

    max_flood_depth: float
    max_aggr_dmg: float
    max_footprint_dmg: float
    max_benefits: float
    additional_aggregated_layers: Optional[list[MetricLayer]] = None
    topobathy_min_max: Union[tuple[float, float], Literal["dem"]] = "dem"


class SviConfigModel(SpatialJoinModel):
    """
    Model for Social Vulnerability Index (SVI) spatial join.

    Inherits from SpatialJoinModel.

    Attributes
    ----------
    threshold : float
        Threshold value to specify vulnerability.
    """

    threshold: float


class TideGaugeConfigModel(BaseModel):
    """
    Model for tide gauge configuration.

    Attributes
    ----------
    source : TideGaugeSource
        Source of tide gauge data.
    description : str
        Description of the tide gauge.
    ref : Optional[str]
        Reference name (should match water level references).
    id : Optional[int]
        Station ID.
    lon : Optional[float]
        Longitude.
    lat : Optional[float]
        Latitude.
    file : Optional[str]
        Path to tide gauge data file.
    max_distance : Optional[us.UnitfulLength]
        Maximum distance for gauge association.
    """

    source: TideGaugeSource
    description: str = ""
    ref: Optional[str] = None
    id: Optional[int] = None
    lon: Optional[float] = None
    lat: Optional[float] = None
    file: Optional[str] = None
    max_distance: Optional[us.UnitfulLength] = None


class ConfigModel(BaseModel):
    """
    Main configuration model for FloodAdapt database builder.

    Attributes
    ----------
    name : str
        Name of the site (must be valid for folder names).
    description : Optional[str]
        Description of the site.
    database_path : Optional[str]
        Path to the database root directory.
    unit_system : UnitSystems
        Unit system for all calculations (imperial or metric).
    is_coastal: Optional[bool] = None
        Indicates whether the site is coastal.
    gui : GuiConfigModel
        GUI visualization scaling configuration.
    infographics : bool
        Enable/disable infographics.
    event_infographics : Optional[EventInfographicModel]
        Configuration for event infographics.
    risk_infographics : Optional[RiskInfographicModel]
        Configuration for risk infographics.
    event_additional_infometrics : Optional[list[MetricModel]]
        Additional event infometrics.
    risk_additional_infometrics : Optional[list[MetricModel]]
        Additional risk infometrics.
    fiat : str
        Path to the FIAT model directory.
    aggregation_areas : Optional[list[SpatialJoinModel]]
        List of aggregation area spatial join models.
    building_footprints : Optional[SpatialJoinModel | FootprintsOptions]
        Building footprints source or spatial join model.
    fiat_buildings_name : str | list[str]
        Name(s) of buildings geometry in FIAT model.
    fiat_roads_name : Optional[str]
        Name of roads geometry in FIAT model.
    bfe : Optional[SpatialJoinModel]
        Base Flood Elevation spatial join model.
    svi : Optional[SviConfigModel]
        Social Vulnerability Index spatial join model.
    road_width : us.UnitfulLength
        Road width (default 5 meters).
    return_periods : Optional[list[int]]
        List of return periods for risk calculations.
    floodmap_type : Optional[FloodmapType]
        Type of floodmap to use.
    references : Optional[WaterlevelReferenceModel]
        Water level reference model.
    sfincs_overland : FloodModel
        Overland SFINCS model configuration.
    sfincs_offshore : Optional[FloodModel]
        Offshore SFINCS model configuration.
    dem : Optional[DemModel]
        Digital Elevation Model configuration.
    river_names : Optional[list[str]]
        List of river names (optional).
    excluded_datums : list[str]
        List of datums to exclude from plotting.
    slr_scenarios : Optional[SlrScenariosModel]
        Sea level rise scenarios configuration.
    scs : Optional[SCSModel]
        SCS model configuration.x
    tide_gauge : Optional[TideGaugeConfigModel] #TODO Change name to gauge to cover inland cases?
        Tide gauge configuration.
    cyclones : Optional[bool]
        Enable/disable cyclones.
    cyclone_basin : Optional[Basins]
        Cyclone basin selection.
    obs_point : Optional[list[ObsPointModel]]
        List of observation point models.
    probabilistic_set : Optional[str]
        Path to probabilistic event set.
    """

    # General
    name: str = Field(..., min_length=1, pattern='^[^<>:"/\\\\|?* ]*$')
    description: Optional[str] = None
    database_path: Optional[str] = None
    unit_system: UnitSystems
    is_coastal: Optional[bool] = None
    gui: GuiConfigModel
    infographics: bool = True
    event_infographics: Optional[EventInfographicModel] = None
    risk_infographics: Optional[RiskInfographicModel] = None
    event_additional_infometrics: Optional[list[MetricModel]] = None
    risk_additional_infometrics: Optional[list[MetricModel]] = None

    # FIAT
    fiat: str
    aggregation_areas: Optional[list[SpatialJoinModel]] = None
    building_footprints: Optional[SpatialJoinModel | FootprintsOptions] = (
        FootprintsOptions.OSM
    )
    fiat_buildings_name: str | list[str] = "buildings"
    fiat_roads_name: Optional[str] = "roads"
    bfe: Optional[SpatialJoinModel] = None
    svi: Optional[SviConfigModel] = None
    road_width: us.UnitfulLength = us.UnitfulLength(
        value=5.0, units=us.UnitTypesLength.meters
    )
    return_periods: Optional[list[int]] = None
    floodmap_type: Optional[FloodmapType] = None

    # SFINCS
    references: Optional[WaterlevelReferenceModel] = None
    sfincs_overland: FloodModel
    sfincs_offshore: Optional[FloodModel] = None
    dem: Optional[DemModel] = None
    river_names: Optional[list[str]] = None
    excluded_datums: list[str] = Field(default_factory=list)

    slr_scenarios: Optional[SlrScenariosModel] = None
    scs: Optional[SCSModel] = None
    tide_gauge: Optional[TideGaugeConfigModel] = None
    cyclones: Optional[bool] = True
    cyclone_basin: Optional[Basins] = None
    obs_point: Optional[list[ObsPointModel]] = None
    probabilistic_set: Optional[str] = None

    @model_validator(mode="after")
    def validate_offshore_for_non_coastal(self) -> "ConfigModel":
        if self.is_coastal is False and self.sfincs_offshore is not None:
            raise ValueError(
                "When 'is_coastal' is False (thus this is an inland site), 'sfincs_offshore' cannot be provided."
            )
        return self

    @staticmethod
    def read(toml_path: Union[str, Path]) -> "ConfigModel":
        """
        Read a configuration file and returns the validated attributes.

        Args:
            toml_path (str | Path): The path to the configuration file.

        Returns
        -------
            ConfigModel: The validated attributes from the configuration file.
        """
        toml = read_toml(toml_path)
        config = ConfigModel.model_validate(toml)

        # check if database path is provided and use config_file path if not
        if config.database_path is None:
            dbs_path = Path(toml_path).parent / "Database"
            if not dbs_path.exists():
                dbs_path.mkdir(parents=True)
            config.database_path = dbs_path.as_posix()
        # check if paths are relative to the config file and make them absolute
        config.database_path = path_check(config.database_path, toml_path)
        config.fiat = path_check(config.fiat, toml_path)
        config.sfincs_overland.name = path_check(config.sfincs_overland.name, toml_path)
        if config.dem:
            config.dem.filename = path_check(config.dem.filename, toml_path)
        if config.sfincs_offshore:
            config.sfincs_offshore.name = path_check(
                config.sfincs_offshore.name, toml_path
            )
        if isinstance(config.building_footprints, SpatialJoinModel):
            config.building_footprints.file = path_check(
                config.building_footprints.file, toml_path
            )
        if config.tide_gauge and config.tide_gauge.file:
            config.tide_gauge.file = path_check(config.tide_gauge.file, toml_path)
        if config.svi:
            config.svi.file = path_check(config.svi.file, toml_path)
        if config.bfe:
            config.bfe.file = path_check(config.bfe.file, toml_path)
        if config.slr_scenarios:
            config.slr_scenarios.file = path_check(config.slr_scenarios.file, toml_path)
        if config.probabilistic_set:
            config.probabilistic_set = path_check(config.probabilistic_set, toml_path)
        if config.aggregation_areas:
            for aggr in config.aggregation_areas:
                aggr.file = path_check(aggr.file, toml_path)

        return config

    def write(self, toml_path: Path) -> None:
        """
        Write the configuration model to a TOML file.

        Parameters
        ----------
        toml_path : Path
            The path to the TOML file where the configuration will be saved.
        """
        config_dict = self.model_dump(exclude_none=True)

        # Make paths relative to the config file
        config_dict["database_path"] = make_relative(
            config_dict["database_path"], toml_path
        )
        config_dict["fiat"] = make_relative(config_dict["fiat"], toml_path)
        config_dict["sfincs_overland"]["name"] = make_relative(
            config_dict["sfincs_overland"]["name"], toml_path
        )
        if self.dem:
            config_dict["dem"]["filename"] = make_relative(
                config_dict["dem"]["filename"], toml_path
            )
        if config_dict.get("sfincs_offshore"):
            config_dict["sfincs_offshore"]["name"] = make_relative(
                config_dict["sfincs_offshore"]["name"], toml_path
            )
        if isinstance(self.building_footprints, SpatialJoinModel):
            config_dict["building_footprints"]["file"] = make_relative(
                config_dict["building_footprints"]["file"], toml_path
            )
        if self.tide_gauge and self.tide_gauge.file:
            config_dict["tide_gauge"]["file"] = make_relative(
                config_dict["tide_gauge"]["file"], toml_path
            )
        if self.svi:
            config_dict["svi"]["file"] = make_relative(
                config_dict["svi"]["file"], toml_path
            )
        if self.bfe:
            config_dict["bfe"]["file"] = make_relative(
                config_dict["bfe"]["file"], toml_path
            )
        if self.slr_scenarios:
            config_dict["slr_scenarios"]["file"] = make_relative(
                config_dict["slr_scenarios"]["file"], toml_path
            )

        if config_dict.get("probabilistic_set"):
            config_dict["probabilistic_set"] = make_relative(
                config_dict["probabilistic_set"], toml_path
            )

        if config_dict.get("aggregation_areas"):
            for ag in config_dict["aggregation_areas"]:
                ag["file"] = make_relative(ag["file"], toml_path)

        toml_path.parent.mkdir(parents=True, exist_ok=True)
        write_toml(config_dict, toml_path)


class DatabaseBuilder:
    _has_roads: bool = False
    _aggregation_areas: Optional[list] = None
    _probabilistic_set_name: Optional[str] = None

    def __init__(self, config: ConfigModel):
        self.config = config

        # Set database root
        if config.database_path:
            self.root = Path(config.database_path).joinpath(self.config.name)
        else:
            raise ValueError(
                "Database path is not provided. Please provide a path using the 'database_path' attribute."
            )

        # Read info that needs to be used to create other models
        self.unit_system = self.create_default_units()

    @property
    def static_path(self) -> Path:
        return self.root / "static"

    @debug_timer
    def build(self, overwrite: bool = False) -> None:
        # Check if database already exists
        if self.root.exists():
            if overwrite:
                shutil.rmtree(self.root)
                warnings.warn(
                    f"There is already a Database folder in '{self.root.as_posix()}, which will be overwritten'."
                )
            else:
                raise ValueError(
                    f"There is already a Database folder in '{self.root.as_posix()}'."
                )
        # Create database folder
        self.root.mkdir(parents=True)

        with FloodAdaptLogging.to_file(
            file_path=self.root.joinpath("database_builder.log")
        ):
            logger.info(f"Creating a FloodAdapt database in '{self.root.as_posix()}'")

            # Make folder structure and read models
            self.setup()

            # Prepare site configuration
            site = self.create_site_config()
            site.save(self.static_path / "config" / "site.toml")

            # Add infometric and infographic configurations
            self.create_infometrics()

            # Save standard objects
            self.create_standard_objects()

            # Save log file
            logger.info("FloodAdapt database creation finished!")

    @debug_timer
    def setup(self) -> None:
        # Create the models
        self.make_folder_structure()

        # Read user models and copy to templates
        self.read_template_fiat_model()
        self.read_template_sfincs_overland_model()
        self.read_template_sfincs_offshore_model()

        # Copy standard static files
        self.add_static_files()

    @debug_timer
    def set_standard_objects(self):
        # Define name and create object
        self._no_measures_strategy_name = "no_measures"
        self._current_projection_name = "current"
        if self._probabilistic_set_name is not None:
            event_list = [self._probabilistic_set_name]
        else:
            event_list = []
        std_obj = StandardObjectModel(
            events=event_list,
            projections=[self._current_projection_name],
            strategies=[self._no_measures_strategy_name],
        )
        return std_obj

    @debug_timer
    def create_standard_objects(self):
        with modified_environ(
            DATABASE_ROOT=str(self.root.parent),
            DATABASE_NAME=self.root.name,
        ):
            logger.info("Creating `no measures` strategy and `current` projection.")
            # Create database instance
            db = Database(
                database_root=self.root.parent, database_name=self.config.name
            )
            # Create no measures strategy
            strategy = Strategy(
                name=self._no_measures_strategy_name,
                measures=[],
            )
            db.strategies.add(strategy)
            # Create current projection
            projection = Projection(
                name=self._current_projection_name,
                physical_projection=PhysicalProjection(),
                socio_economic_change=SocioEconomicChange(),
            )
            db.projections.add(projection)
            # Check prob set
            if self._probabilistic_set_name is not None:
                path_toml = (
                    db.input_path
                    / "events"
                    / self._probabilistic_set_name
                    / f"{self._probabilistic_set_name}.toml"
                )
                try:
                    EventSet.load_file(path_toml)
                except Exception as e:
                    raise ValueError(
                        f"Provided probabilistic event set '{self._probabilistic_set_name}' is not valid. Error: {e}"
                    )
            db.flush()

    ### TEMPLATE READERS ###
    @debug_timer
    def read_template_fiat_model(self):
        user_provided = self._check_exists_and_absolute(self.config.fiat)

        # Read config model
        HydromtFiatModel(root=str(user_provided), mode="r+").read()

        # Success, so copy to db and read again
        location_in_db = self.static_path / "templates" / "fiat"
        if location_in_db.exists():
            shutil.rmtree(location_in_db)
        shutil.copytree(user_provided, location_in_db)
        in_db = HydromtFiatModel(root=str(location_in_db), mode="r+")
        in_db.read()
        # Add check to make sure the geoms are correct
        # TODO this should be handled in hydromt-FIAT
        no_geoms = len(
            [name for name in in_db.config["exposure"]["geom"].keys() if "file" in name]
        )
        in_db.exposure.exposure_geoms = in_db.exposure.exposure_geoms[:no_geoms]
        in_db.exposure._geom_names = in_db.exposure._geom_names[:no_geoms]

        # Make sure that a region polygon is included
        if "region" not in in_db.geoms:
            gdf = in_db.exposure.get_full_gdf(in_db.exposure.exposure_db)
            # Combine all geometries into a single geometry
            merged_geometry = gdf.unary_union

            # If the result is not a polygon, you can create a convex hull
            if not isinstance(merged_geometry, Polygon):
                merged_geometry = merged_geometry.convex_hull
            # Create a new GeoDataFrame with the resulting polygon
            in_db.geoms["region"] = gpd.GeoDataFrame(
                geometry=[merged_geometry], crs=gdf.crs
            )

        self.fiat_model = in_db

    @debug_timer
    def read_template_sfincs_overland_model(self):
        user_provided = self._check_exists_and_absolute(
            self.config.sfincs_overland.name
        )
        user_model = HydromtSfincsModel(root=str(user_provided), mode="r")
        user_model.read()
        if user_model.crs is None:
            raise ValueError("CRS is not defined in the SFINCS model.")

        location_in_db = self.static_path / "templates" / "overland"
        if location_in_db.exists():
            shutil.rmtree(location_in_db)
        shutil.copytree(user_provided, location_in_db)
        in_db = HydromtSfincsModel(root=str(location_in_db), mode="r+")
        in_db.read()
        self.sfincs_overland_model = in_db

    @debug_timer
    def read_template_sfincs_offshore_model(self):
        if self.config.sfincs_offshore is None:
            self.sfincs_offshore_model = None
            return
        user_provided = self._check_exists_and_absolute(
            self.config.sfincs_offshore.name
        )
        user_model = HydromtSfincsModel(root=str(user_provided), mode="r+")
        user_model.read()
        if user_model.crs is None:
            raise ValueError("CRS is not defined in the SFINCS model.")
        epsg = user_model.crs.to_epsg()

        location_in_db = self.static_path / "templates" / "offshore"
        if location_in_db.exists():
            shutil.rmtree(location_in_db)
        shutil.copytree(user_provided, location_in_db)
        in_db = HydromtSfincsModel(str(location_in_db), mode="r+")
        in_db.read(epsg=epsg)
        self.sfincs_offshore_model = in_db

    ### FIAT ###
    @debug_timer
    def create_fiat_model(self) -> FiatModel:
        fiat = FiatModel(
            config=self.create_fiat_config(),
            benefits=self.create_benefit_config(),
            risk=self.create_risk_model(),
        )
        return fiat

    @debug_timer
    def create_risk_model(self) -> RiskModel:
        # Check if return periods are provided
        if not self.config.return_periods:
            risk = RiskModel()
            logger.warning(
                f"No return periods provided for performing risk calculations. Using default return periods {risk.return_periods}."
            )
        else:
            risk = RiskModel(return_periods=self.config.return_periods)
        return risk

    @debug_timer
    def create_benefit_config(self) -> Optional[BenefitsModel]:
        if self._probabilistic_set_name is None:
            logger.warning(
                "No probabilistic set found in the config, benefits will not be available."
            )
            return None
        return BenefitsModel(
            current_year=datetime.datetime.now().year,
            current_projection="current",
            baseline_strategy="no_measures",
            event_set=self._probabilistic_set_name,
        )

    @debug_timer
    def create_fiat_config(self) -> FiatConfigModel:
        # Make sure only csv objects have geometries
        self._delete_extra_geometries()

        footprints = self.create_footprints()
        if footprints is not None:
            footprints = footprints.as_posix()

        # Clip hazard and reset buildings # TODO use hydromt-FIAT instead
        if not self.fiat_model.region.empty:
            self._clip_hazard_extend()

        # Store result for possible future use in create_infographics
        self._aggregation_areas = self.create_aggregation_areas()

        roads_gpkg = self.create_roads()

        # Get classes of non-building objects
        non_buildings = ~self.fiat_model.exposure.exposure_db[
            _FIAT_COLUMNS.object_id
        ].isin(self._get_fiat_building_geoms()[_FIAT_COLUMNS.object_id])
        non_building_names = list(
            self.fiat_model.exposure.exposure_db[_FIAT_COLUMNS.primary_object_type][
                non_buildings
            ].unique()
        )

        # Update elevations
        self.update_fiat_elevation()

        self._svi = self.create_svi()

        config = FiatConfigModel(
            exposure_crs=self.fiat_model.exposure.crs,
            floodmap_type=self.read_floodmap_type(),
            bfe=self.create_bfe(),
            non_building_names=non_building_names,
            damage_unit=self.read_damage_unit(),
            building_footprints=footprints,
            roads_file_name=roads_gpkg,
            new_development_file_name=self.create_new_developments(),
            save_simulation=False,  # TODO
            infographics=self.config.infographics,
            aggregation=self._aggregation_areas,
            svi=self._svi,
        )

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
        # Make sure objects are ordered based on object id
        self.fiat_model.exposure.exposure_db = (
            self.fiat_model.exposure.exposure_db.sort_values(
                by=[_FIAT_COLUMNS.object_id], ignore_index=True
            )
        )
        # Update FIAT model with the new config
        self.fiat_model.write()

        return config

    @debug_timer
    def update_fiat_elevation(self):
        """
        Update the ground elevations of FIAT objects based on the SFINCS ground elevation map.

        This method reads the DEM file and the exposure CSV file, and updates the ground elevations
        of the FIAT objects (roads and buildings) based on the nearest elevation values from the DEM.
        """
        dem_file = self._dem_path
        # TODO resolve issue with double geometries in hydromt-FIAT and use update_ground_elevation method instead
        # self.fiat_model.update_ground_elevation(dem_file, grnd_elev_unit="meters")
        logger.info(
            "Updating FIAT objects ground elevations from SFINCS ground elevation map."
        )
        # Get unit conversion factor
        SFINCS_units = us.UnitfulLength(
            value=1.0, units=us.UnitTypesLength.meters
        )  # SFINCS is always in meters
        FIAT_units = self.unit_system.default_length_units
        conversion_factor = SFINCS_units.convert(FIAT_units)

        if not math.isclose(conversion_factor, 1):
            logger.info(
                f"Ground elevation for FIAT objects is in '{FIAT_units}', while SFINCS ground elevation is in 'meters'. Values in the exposure csv will be converted by a factor of {conversion_factor}"
            )
        # Read in DEM and objects
        exposure = self.fiat_model.exposure.exposure_db
        dem = rxr.open_rasterio(dem_file)
        gdf = self._get_fiat_gdf_full()

        # Ensure gdf has the same CRS as dem
        # Determine the CRS to use for sampling
        if (
            hasattr(self.sfincs_overland_model, "crs")
            and self.sfincs_overland_model.crs is not None
        ):
            target_crs = self.sfincs_overland_model.crs
        elif (
            hasattr(dem, "rio") and hasattr(dem.rio, "crs") and dem.rio.crs is not None
        ):
            target_crs = dem.rio.crs
        else:
            target_crs = gdf.crs
            logger.warning(
                "Could not determine CRS from SFINCS model or DEM raster. Assuming the CRS is the same as the FIAT model."
            )

        if gdf.crs != target_crs:
            gdf = gdf.to_crs(target_crs)

        # Sample DEM at the centroid of each geometry
        gdf["centroid"] = gdf.geometry.centroid
        x_points = xr.DataArray(gdf["centroid"].x, dims="points")
        y_points = xr.DataArray(gdf["centroid"].y, dims="points")
        gdf["elev"] = (
            dem.sel(x=x_points, y=y_points, band=1, method="nearest").to_numpy()
            * conversion_factor
        )

        # Merge updated elevation back into exposure DataFrame
        exposure = exposure.merge(
            gdf[[_FIAT_COLUMNS.object_id, "elev"]],
            on=_FIAT_COLUMNS.object_id,
            how="left",
        )
        exposure[_FIAT_COLUMNS.ground_elevation] = exposure["elev"]
        del exposure["elev"]

        self.fiat_model.exposure.exposure_db = self._clean_suffix_columns(exposure)

    def read_damage_unit(self) -> str:
        if self.fiat_model.exposure.damage_unit is None:
            logger.warning(
                "Delft-FIAT model was missing damage units so '$' was assumed."
            )
            self.fiat_model.exposure.damage_unit = "$"
        return self.fiat_model.exposure.damage_unit

    @debug_timer
    def read_floodmap_type(self) -> FloodmapType:
        if self.config.floodmap_type is not None:
            return self.config.floodmap_type
        else:
            # If there is at least on object that uses the area method, use water depths for FA calcs
            if (
                self.fiat_model.exposure.exposure_db[_FIAT_COLUMNS.extraction_method]
                == "area"
            ).any():
                return FloodmapType.water_depth
            else:
                return FloodmapType.water_level

    @debug_timer
    def create_roads(self) -> Optional[str]:
        # Make sure that FIAT roads are polygons
        if self.config.fiat_roads_name not in self.fiat_model.exposure.geom_names:
            logger.warning(
                "Road objects are not available in the FIAT model and thus would not be available in FloodAdapt."
            )
            # TODO check how this naming of output geoms should become more explicit!
            return None

        roads = self.fiat_model.exposure.exposure_geoms[self._get_fiat_road_index()]

        # TODO do we need the lanes column?
        if (
            _FIAT_COLUMNS.segment_length
            not in self.fiat_model.exposure.exposure_db.columns
        ):
            logger.warning(
                f"'{_FIAT_COLUMNS.segment_length}' column not present in the FIAT exposure csv. Road impact infometrics cannot be produced."
            )

        # TODO should this should be performed through hydromt-FIAT?
        if not isinstance(roads.geometry.iloc[0], Polygon):
            roads = roads.to_crs(roads.estimate_utm_crs())
            road_width = self.config.road_width.convert(us.UnitTypesLength.meters)
            roads.geometry = roads.geometry.buffer(road_width / 2, cap_style=2)
            roads = roads.to_crs(self.fiat_model.exposure.crs)
            self.fiat_model.exposure.exposure_geoms[self._get_fiat_road_index()] = roads
            logger.info(
                f"FIAT road objects transformed from lines to polygons assuming a road width of {self.config.road_width} meters."
            )

        self._has_roads = True
        return f"{self.config.fiat_roads_name}.gpkg"

    @debug_timer
    def create_new_developments(self) -> Optional[str]:
        return "new_development_area.gpkg"

    @debug_timer
    def create_footprints(self) -> Optional[Path]:
        if isinstance(self.config.building_footprints, SpatialJoinModel):
            # Use the provided building footprints
            building_footprints_file = self._check_exists_and_absolute(
                self.config.building_footprints.file
            )

            logger.info(
                f"Using building footprints from {Path(building_footprints_file).as_posix()}."
            )
            # Spatially join buildings and map
            # TODO use hydromt method instead
            path = self._join_building_footprints(
                self.config.building_footprints.file,
                self.config.building_footprints.field_name,
            )
            return path
        elif self.config.building_footprints == FootprintsOptions.OSM:
            logger.info(
                "Building footprint data will be downloaded from Open Street Maps."
            )
            region = self.fiat_model.region
            if region is None:
                raise ValueError(
                    "No region file found in the FIAT model. Building footprints cannot be created."
                )
            region = region.to_crs(4326)
            if isinstance(region.boundary.to_numpy()[0], MultiLineString):
                polygon = Polygon(
                    region.boundary.to_numpy()[0].envelope
                )  # TODO check if this is correct
            else:
                polygon = Polygon(region.boundary.to_numpy()[0])
            footprints = get_buildings_from_osm(polygon)
            footprints["BF_FID"] = np.arange(1, len(footprints) + 1)
            footprints = footprints[["BF_FID", "geometry"]]
            path = self._join_building_footprints(footprints, "BF_FID")
            return path
        # Then check if geometries are already footprints
        elif isinstance(
            self._get_fiat_building_geoms().geometry.iloc[0],
            (Polygon, MultiPolygon),
        ):
            logger.info(
                "Building footprints are already available in the FIAT model geometry files."
            )
            return None
        # check if it is spatially joined and/or exists already
        elif "BF_FID" in self.fiat_model.exposure.exposure_db.columns:
            add_attrs = self.fiat_model.spatial_joins["additional_attributes"]
            fiat_path = Path(self.fiat_model.root)

            if not (add_attrs and "BF_FID" in [attr["name"] for attr in add_attrs]):
                raise KeyError(
                    "While 'BF_FID' column exists, connection to a spatial footprints file is missing."
                )

            ind = [attr["name"] for attr in add_attrs].index("BF_FID")
            footprints = add_attrs[ind]
            footprints_path = fiat_path / footprints["file"]

            if not footprints_path.exists():
                raise FileNotFoundError(
                    f"While 'BF_FID' column exists, building footprints file {footprints_path} not found."
                )

            logger.info(f"Using the building footprints located at {footprints_path}.")
            return footprints_path.relative_to(self.static_path)

        # Other methods
        else:
            logger.warning(
                "No building footprints are available. Buildings will be plotted with a default shape in FloodAdapt."
            )
            return None

    @debug_timer
    def create_bfe(self) -> Optional[BFEModel]:
        if self.config.bfe is None:
            logger.warning(
                "No base flood elevation provided. Elevating building relative to base flood elevation will not be possible in FloodAdapt."
            )
            return None

        # TODO can we use hydromt-FIAT?
        bfe_file = self._check_exists_and_absolute(self.config.bfe.file)

        logger.info(
            f"Using map from {Path(bfe_file).as_posix()} as base flood elevation."
        )

        # Spatially join buildings and map
        buildings_joined, bfe = self.spatial_join(
            self._get_fiat_building_geoms(),
            bfe_file,
            self.config.bfe.field_name,
        )

        # Make sure in case of multiple values that the max is kept
        buildings_joined = (
            buildings_joined.groupby(_FIAT_COLUMNS.object_id)
            .max(self.config.bfe.field_name)
            .sort_values(by=[_FIAT_COLUMNS.object_id])
            .reset_index()
        )

        # Save the files
        fa_bfe_file = self.static_path / "bfe" / "bfe.gpkg"
        fa_bfe_file.parent.mkdir(parents=True, exist_ok=True)
        bfe.to_file(fa_bfe_file)
        csv_path = fa_bfe_file.parent / "bfe.csv"
        buildings_joined.to_csv(csv_path, index=False)

        # Update the units if provided

        # Save attributes
        return BFEModel(
            geom=fa_bfe_file.relative_to(self.static_path).as_posix(),
            table=csv_path.relative_to(self.static_path).as_posix(),
            field_name=self.config.bfe.field_name,
            units=self.config.bfe.units,
        )

    @debug_timer
    def create_aggregation_areas(self) -> list[AggregationModel]:
        # TODO split this to 3 methods?
        aggregation_areas = []

        # first check if the FIAT model has existing aggregation areas
        if self.fiat_model.spatial_joins["aggregation_areas"]:
            # Use the aggregation areas from the FIAT model
            for aggr in self.fiat_model.spatial_joins["aggregation_areas"]:
                # Check if the exposure csv has the correct column
                col_name = _FIAT_COLUMNS.aggregation_label.format(name=aggr["name"])
                if col_name not in self.fiat_model.exposure.exposure_db.columns:
                    raise KeyError(
                        f"While aggregation area '{aggr['name']}' exists in the spatial joins of the FIAT model, the column '{col_name}' is missing in the exposure csv."
                    )
                # Check equity config
                if aggr["equity"] is not None:
                    equity_config = EquityModel(
                        census_data=str(
                            self.static_path.joinpath(
                                "templates", "fiat", aggr["equity"]["census_data"]
                            )
                            .relative_to(self.static_path)
                            .as_posix()
                        ),
                        percapitaincome_label=aggr["equity"]["percapitaincome_label"],
                        totalpopulation_label=aggr["equity"]["totalpopulation_label"],
                    )
                else:
                    equity_config = None
                # Make aggregation config
                aggr = AggregationModel(
                    name=aggr["name"],
                    file=str(
                        self.static_path.joinpath("templates", "fiat", aggr["file"])
                        .relative_to(self.static_path)
                        .as_posix()
                    ),
                    field_name=aggr["field_name"],
                    equity=equity_config,
                )
                aggregation_areas.append(aggr)

                logger.info(
                    f"Aggregation areas: {aggr.name} from the FIAT model are going to be used."
                )

        # Then check if the user has provided extra aggregation areas in the config
        if self.config.aggregation_areas:
            # Loop through aggr areas given in config
            for aggr in self.config.aggregation_areas:
                # Get name of type of aggregation area
                if aggr.name is not None:
                    aggr_name = aggr.name
                else:
                    aggr_name = Path(aggr.file).stem
                # If aggregation area already in FIAT model raise Error
                if aggr_name in [aggr.name for aggr in aggregation_areas]:
                    logger.warning(
                        f"Aggregation area '{aggr_name}' already exists in the FIAT model. The input aggregation area will be ignored."
                    )
                    continue
                # Do spatial join of FIAT objects and aggregation areas
                exposure_csv = self.fiat_model.exposure.exposure_db
                gdf = self._get_fiat_gdf_full()
                gdf_joined, aggr_areas = self.spatial_join(
                    objects=gdf[[_FIAT_COLUMNS.object_id, "geometry"]],
                    layer=str(self._check_exists_and_absolute(aggr.file)),
                    field_name=aggr.field_name,
                    rename=_FIAT_COLUMNS.aggregation_label.format(name=aggr_name),
                    filter=True,
                )
                aggr_path = Path(self.fiat_model.root).joinpath(
                    "exposure", "aggregation_areas", f"{Path(aggr.file).stem}.gpkg"
                )
                aggr_path.parent.mkdir(parents=True, exist_ok=True)
                aggr_areas.to_file(aggr_path)
                exposure_csv = exposure_csv.merge(
                    gdf_joined, on=_FIAT_COLUMNS.object_id, how="left"
                )
                self.fiat_model.exposure.exposure_db = self._clean_suffix_columns(
                    exposure_csv
                )
                # Update spatial joins in FIAT model
                if self.fiat_model.spatial_joins["aggregation_areas"] is None:
                    self.fiat_model.spatial_joins["aggregation_areas"] = []
                self.fiat_model.spatial_joins["aggregation_areas"].append(
                    {
                        "name": aggr_name,
                        "file": aggr_path.relative_to(self.fiat_model.root).as_posix(),
                        "field_name": _FIAT_COLUMNS.aggregation_label.format(
                            name=aggr_name
                        ),
                        "equity": None,  # TODO allow adding equity as well?
                    }
                )
                # Update the aggregation areas list in the config
                aggregation_areas.append(
                    AggregationModel(
                        name=aggr_name,
                        file=aggr_path.relative_to(self.static_path).as_posix(),
                        field_name=_FIAT_COLUMNS.aggregation_label.format(
                            name=aggr_name
                        ),
                    )
                )
                logger.info(
                    f"Aggregation areas: {aggr_name} provided in the config are going to be used."
                )

        # No config provided, no aggr areas in the model -> try to use the region file as a mock aggregation area
        if (
            not self.fiat_model.spatial_joins["aggregation_areas"]
            and not self.config.aggregation_areas
        ):
            exposure_csv = self.fiat_model.exposure.exposure_db
            region = self.fiat_model.geoms["region"]
            region = region.explode().reset_index()
            region["aggr_id"] = ["region_" + str(i) for i in np.arange(len(region)) + 1]
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
            aggregation_areas.append(aggr)

            # Add column in FIAT
            gdf = self._get_fiat_gdf_full()
            gdf_joined, aggr_areas = self.spatial_join(
                objects=gdf[[_FIAT_COLUMNS.object_id, "geometry"]],
                layer=region,
                field_name="aggr_id",
                rename=_FIAT_COLUMNS.aggregation_label.format(name="region"),
            )
            exposure_csv = exposure_csv.merge(
                gdf_joined, on=_FIAT_COLUMNS.object_id, how="left"
            )
            self.fiat_model.exposure.exposure_db = self._clean_suffix_columns(
                exposure_csv
            )
            logger.warning(
                "No aggregation areas were available in the FIAT model and none were provided in the config file. The region file will be used as a mock aggregation area."
            )
        return aggregation_areas

    @debug_timer
    def create_svi(self) -> Optional[SVIModel]:
        if self.config.svi:
            svi_file = self._check_exists_and_absolute(self.config.svi.file)
            exposure_csv = self.fiat_model.exposure.exposure_db
            buildings_joined, svi = self.spatial_join(
                self._get_fiat_building_geoms(),
                svi_file,
                self.config.svi.field_name,
                rename="SVI",
                filter=True,
            )
            # Add column to exposure
            if "SVI" in exposure_csv.columns:
                logger.info(
                    f"'SVI' column in the FIAT exposure csv will be replaced by {svi_file.as_posix()}."
                )
                del exposure_csv["SVI"]
            else:
                logger.info(
                    f"'SVI' column in the FIAT exposure csv will be filled by {svi_file.as_posix()}."
                )
            exposure_csv = exposure_csv.merge(
                buildings_joined, on=_FIAT_COLUMNS.object_id, how="left"
            )
            self.fiat_model.exposure.exposure_db = self._clean_suffix_columns(
                exposure_csv
            )

            # Save the spatial file for future use
            svi_path = self.static_path / "templates" / "fiat" / "svi" / "svi.gpkg"
            svi_path.parent.mkdir(parents=True, exist_ok=True)
            svi.to_file(svi_path)
            logger.info(
                f"An SVI map can be shown in FloodAdapt GUI using '{self.config.svi.field_name}' column from {svi_file.as_posix()}"
            )

            return SVIModel(
                geom=Path(svi_path.relative_to(self.static_path)).as_posix(),
                field_name="SVI",
            )
        elif "SVI" in self.fiat_model.exposure.exposure_db.columns:
            logger.info(
                "'SVI' column present in the FIAT exposure csv. Vulnerability type infometrics can be produced."
            )
            add_attrs = self.fiat_model.spatial_joins["additional_attributes"]
            if add_attrs is None:
                logger.warning(
                    "'SVI' column present in the FIAT exposure csv, but no spatial join found with the SVI map."
                )
                return None

            if "SVI" not in [attr["name"] for attr in add_attrs]:
                logger.warning("No SVI map found to display in the FloodAdapt GUI!")
                return None

            ind = [attr["name"] for attr in add_attrs].index("SVI")
            svi = add_attrs[ind]
            svi_path = self.static_path / "templates" / "fiat" / svi["file"]
            logger.info(
                f"An SVI map can be shown in FloodAdapt GUI using '{svi['field_name']}' column from {svi['file']}"
            )
            # Save site attributes
            return SVIModel(
                geom=Path(svi_path.relative_to(self.static_path)).as_posix(),
                field_name=svi["field_name"],
            )

        else:
            logger.warning(
                "'SVI' column not present in the FIAT exposure csv. Vulnerability type infometrics cannot be produced."
            )
            return None

    ### SFINCS ###
    @debug_timer
    def create_sfincs_config(self) -> SfincsModel:
        # call these functions before others to make sure water level references are updated
        config = self.create_sfincs_model_config()
        self.water_level_references = self.create_water_level_references()
        self.tide_gauge = self.create_tide_gauge()

        sfincs = SfincsModel(
            config=config,
            water_level=self.water_level_references,
            has_wl_boundaries=self._determine_if_wl_boundaries(),
            slr_scenarios=self.create_slr(),
            dem=self.create_dem_model(),
            scs=self.create_scs_model(),
            cyclone_track_database=self.create_cyclone_track_database(),
            tide_gauge=self.tide_gauge,
            river=self.create_rivers(),
            obs_point=self.create_observation_points(),
        )

        return sfincs

    @debug_timer
    def create_water_level_references(self) -> WaterlevelReferenceModel:
        sfincs_ref = self.config.sfincs_overland.reference
        if self.config.references is None:
            logger.warning(
                f"No water level references provided in the config file. Using reference provided for overland SFINCS model '{sfincs_ref}' as the main reference."
            )
            refs = WaterlevelReferenceModel(
                reference=sfincs_ref,
                datums=[
                    DatumModel(
                        name=sfincs_ref,
                        height=us.UnitfulLength(
                            value=0.0, units=self.unit_system.default_length_units
                        ),
                    )
                ],
            )
        else:
            # Check if sfincs_ref is in the references
            if sfincs_ref not in [ref.name for ref in self.config.references.datums]:
                raise ValueError(
                    f"Reference '{sfincs_ref}' not found in the provided references."
                )
            else:
                refs = self.config.references

        return refs

    @debug_timer
    def create_cyclone_track_database(self) -> Optional[CycloneTrackDatabaseModel]:
        if not self.config.cyclones or not self.config.sfincs_offshore:
            logger.warning("No cyclones will be available in the database.")
            return None

        if self.config.cyclone_basin:
            basin = self.config.cyclone_basin
        else:
            basin = "ALL"

        name = f"IBTrACS.{basin.value}.v04r01.nc"
        url = f"https://www.ncei.noaa.gov/data/international-best-track-archive-for-climate-stewardship-ibtracs/v04r01/access/netcdf/{name}"
        logger.info(f"Downloading cyclone track database from {url}")
        fn = Path(self.root) / "static" / "cyclone_track_database" / name
        fn.parent.mkdir(parents=True, exist_ok=True)

        try:
            urlretrieve(url, fn)
        except Exception:
            logger.warning(f"Could not retrieve cyclone track database from {url}")
            logger.warning("No cyclones will be available in the database.")
            return None

        return CycloneTrackDatabaseModel(file=name)

    @debug_timer
    def create_scs_model(self) -> Optional[SCSModel]:
        if self.config.scs is None:
            return None
        scs_file = self._check_exists_and_absolute(self.config.scs.file)
        db_scs_file = self.static_path / "scs" / scs_file.name
        db_scs_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(scs_file, db_scs_file)

        return SCSModel(file=scs_file.name, type=self.config.scs.type)

    @debug_timer
    def create_dem_model(self) -> DemModel:
        subgrid_sfincs_folder = Path(self.sfincs_overland_model.root) / "subgrid"
        subgrid_sfincs_folder_exist = subgrid_sfincs_folder.is_dir()
        if self.config.dem:
            subgrid_sfincs = Path(self.config.dem.filename)
        else:
            logger.warning(
                "No subgrid depth geotiff file provided in the config file. Using the one from the SFINCS model."
            )
            if not subgrid_sfincs_folder_exist:
                raise FileNotFoundError(
                    f"Subgrid folder {subgrid_sfincs_folder} does not exist in the SFINCS model."
                )
            if self.sfincs_overland_model.grid_type == "quadtree":
                # If SFINCS is quadtree use the 0 level
                subgrid_sfincs = subgrid_sfincs_folder / "dep_subgrid_lev0.tif"
            else:
                subgrid_sfincs = subgrid_sfincs_folder / "dep_subgrid.tif"
        # Check that file exists and get absolute path
        dem_file = self._check_exists_and_absolute(str(subgrid_sfincs))
        # Define where it will be stored in the database
        fa_subgrid_path = self.static_path / "dem" / dem_file.name
        fa_subgrid_path.parent.mkdir(parents=True, exist_ok=True)

        shutil.copy2(dem_file, fa_subgrid_path)

        fa_index_path = self.static_path / "dem" / "index.tif"
        # Make index cog
        make_index_cog(
            model=self.sfincs_overland_model,
            indices_fn=fa_index_path,
            topobathy_fn=fa_subgrid_path,
        )
        logger.info(
            f"An index file was created using the {subgrid_sfincs.as_posix()} as the elevation map, and save at {fa_index_path.as_posix()}."
        )

        self._dem_path = fa_subgrid_path

        # Get min max values
        if self.config.gui.topobathy_min_max == "dem":
            dem: xr.DataArray = rxr.open_rasterio(fa_subgrid_path)
            conversion_factor = us.UnitfulLength(
                value=1.0, units=us.UnitTypesLength.meters
            ).convert(self.unit_system.default_length_units)

            cmin = float(dem.min().compute().item()) * conversion_factor
            cmax = float(dem.max().compute().item()) * conversion_factor
            cmin = round(cmin, 0)
            cmax = round(cmax, 0)
            self.topobathy_min_max = (cmin, cmax)
        else:
            self.topobathy_min_max = self.config.gui.topobathy_min_max
        # Remove the original subgrid folder if it exists
        gc.collect()
        if subgrid_sfincs_folder_exist:
            try:
                shutil.rmtree(subgrid_sfincs_folder)
            except Exception:
                logger.warning(
                    f"Could not delete temporary SFINCS subgrid folder at {subgrid_sfincs_folder.as_posix()}."
                )

        # Dem file always assumed to be in /static/dem
        return DemModel(
            filename=fa_subgrid_path.name,
            units=us.UnitTypesLength.meters,  # SINFCS always in meters
            index_filename=fa_index_path.name,
        )

    @debug_timer
    def create_sfincs_model_config(self) -> SfincsConfigModel:
        config = SfincsConfigModel(
            csname=self.sfincs_overland_model.crs.name,
            cstype=Cstype(
                self.sfincs_overland_model.crs.type_name.split(" ")[0].lower()
            ),
            offshore_model=self.create_offshore_model(),
            overland_model=self.create_overland_model(),
            floodmap_units=self.unit_system.default_length_units,
            save_simulation=False,
        )

        return config

    @debug_timer
    def create_slr(self) -> Optional[SlrScenariosModel]:
        if self.config.slr_scenarios is None:
            return None

        self.config.slr_scenarios.file = str(
            self._check_exists_and_absolute(self.config.slr_scenarios.file)
        )
        slr_path = self.static_path / "slr_scenarios"
        slr_path.mkdir()
        new_file = slr_path / Path(self.config.slr_scenarios.file).name
        shutil.copyfile(self.config.slr_scenarios.file, new_file)

        return SlrScenariosModel(
            file=new_file.relative_to(self.static_path).as_posix(),
            relative_to_year=self.config.slr_scenarios.relative_to_year,
        )

    @debug_timer
    def create_observation_points(self) -> Union[list[ObsPointModel], None]:
        if self.config.obs_point is None:
            obs_points = []
        else:
            logger.info("Observation points were provided in the config file.")
            obs_points = self.config.obs_point

        model_region = self.sfincs_overland_model.region.union_all()

        if self.tide_gauge is not None:
            # Check if tide gauge is within model domain
            coord = (
                gpd.GeoSeries(
                    gpd.points_from_xy(
                        x=[self.tide_gauge.lon], y=[self.tide_gauge.lat]
                    ),
                    crs="EPSG:4326",
                )
                .to_crs(self.sfincs_overland_model.crs)
                .iloc[0]
            )
            # Add tide gauge as obs point if within model region
            if coord.within(model_region):
                if self.tide_gauge.name is None:
                    name = "tide_gauge"
                else:
                    name = self.tide_gauge.name
                obs_points.append(
                    ObsPointModel(
                        name=name,
                        description="Tide gauge observation point",
                        ID=self.tide_gauge.ID,
                        lon=self.tide_gauge.lon,
                        lat=self.tide_gauge.lat,
                    )
                )
            else:
                boundary = model_region.boundary
                snapped = nearest_points(coord, boundary)[1]
                distance = us.UnitfulLength(
                    value=coord.distance(snapped), units=us.UnitTypesLength.meters
                )
                logger.warning(
                    f"Tide gauge lies outside the model domain by {distance}. It will not be used as an observation point in FloodAdapt."
                )

        if not obs_points:
            logger.warning(
                "No observation points were provided in the config file or created from the tide gauge. No observation points will be available in FloodAdapt."
            )
            return None

        # Check if all obs points are within model domain
        lon = [p.lon for p in obs_points]
        lat = [p.lat for p in obs_points]
        names = [p.name for p in obs_points]
        coords = gpd.GeoDataFrame(
            {"name": names},
            geometry=gpd.points_from_xy(lon, lat),
            crs="EPSG:4326",
        )
        coords = coords.to_crs(self.sfincs_overland_model.crs)
        valid_coords = coords.within(model_region)
        if not valid_coords.all():
            invalid = coords.loc[~valid_coords, "name"].tolist()
            lat = coords.loc[~valid_coords].geometry.y.tolist()
            lon = coords.loc[~valid_coords].geometry.x.tolist()
            bounds = model_region.bounds
            raise ValueError(
                f"Observation points outside model domain: {invalid}, {lat=}, {lon=}, {bounds=}"
            )

        return obs_points

    @debug_timer
    def create_rivers(self) -> list[RiverModel]:
        src_file = Path(self.sfincs_overland_model.root) / "sfincs.src"
        if not src_file.exists():
            logger.warning("No rivers found in the SFINCS model.")
            return []

        df = pd.read_csv(src_file, delim_whitespace=True, header=None, names=["x", "y"])
        river_locs = gpd.GeoDataFrame(
            df,
            geometry=gpd.points_from_xy(df.x, df.y),
            crs=self.sfincs_overland_model.crs,
        )

        if self.config.river_names:
            if len(self.config.river_names) != len(river_locs):
                msg = "The number of river names provided does not match the number of rivers found in the SFINCS model."
                logger.error(msg)
                raise ValueError(msg)
            else:
                river_locs["name"] = self.config.river_names
        else:
            river_locs["name"] = [f"river_{idx}" for idx in range(len(river_locs))]

        rivers = []
        for idx, row in river_locs.iterrows():
            if "dis" in self.sfincs_overland_model.forcing:
                discharge = (
                    self.sfincs_overland_model.forcing["dis"]
                    .sel(index=idx + 1)
                    .to_numpy()
                    .mean()
                )
            else:
                discharge = 0
                logger.warning(
                    f"No river discharge conditions were found in the SFINCS model for river {idx}. A default value of 0 will be used."
                )

            river = RiverModel(
                name=row["name"],
                x_coordinate=row.x,
                y_coordinate=row.y,
                mean_discharge=us.UnitfulDischarge(
                    value=discharge, units=self.unit_system.default_discharge_units
                ),
            )
            rivers.append(river)

        logger.info(
            f"{len(river_locs)} river(s) were identified from the SFINCS model and will be available in FloodAdapt for discharge input."
        )

        return rivers

    @debug_timer
    def create_tide_gauge(self) -> Optional[TideGauge]:
        if self.config.tide_gauge is None:
            logger.warning(
                "Tide gauge information not provided. Historical events will not have an option to use gauged data in FloodAdapt!"
            )
            return None

        if self.config.tide_gauge.source == TideGaugeSource.file:
            if self.config.tide_gauge.file is None:
                raise ValueError(
                    "Tide gauge file needs to be provided when 'file' is selected as the source."
                )
            if self.config.tide_gauge.ref is None:
                logger.warning(
                    f"Tide gauge reference not provided. '{self.water_level_references.reference}' is assumed as the reference of the water levels in the file."
                )
                self.config.tide_gauge.ref = self.water_level_references.reference
            else:
                if self.config.tide_gauge.ref not in [
                    datum.name for datum in self.water_level_references.datums
                ]:
                    raise ValueError(
                        f"Provided tide gauge reference '{self.config.tide_gauge.ref}' not found in the water level references!"
                    )

            tide_gauge_file = self._check_exists_and_absolute(
                self.config.tide_gauge.file
            )
            db_file_path = Path(self.static_path / "tide_gauges") / tide_gauge_file.name

            db_file_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(self.config.tide_gauge.file, db_file_path)

            rel_db_path = Path(db_file_path.relative_to(self.static_path)).as_posix()
            logger.warning(
                f"Tide gauge from file {rel_db_path} assumed to be in {self.unit_system.default_length_units}!"
            )
            tide_gauge = TideGauge(
                reference=self.config.tide_gauge.ref,
                description="Observations from file stored in database",
                source=TideGaugeSource.file,
                file=rel_db_path,
                lon=self.config.tide_gauge.lon,
                lat=self.config.tide_gauge.lat,
                units=self.unit_system.default_length_units,
            )

            return tide_gauge

        elif self.config.tide_gauge.source == TideGaugeSource.noaa_coops:
            if self.config.tide_gauge.ref is not None:
                ref = self.config.tide_gauge.ref
            else:
                ref = "MLLW"  # If reference is not provided use MLLW

            if self.config.tide_gauge.id is None:
                station_id = self._get_closest_station()
                logger.info(
                    "The closest NOAA tide gauge station to the site will be searched."
                )
            else:
                station_id = self.config.tide_gauge.id
                logger.info(
                    f"The NOAA tide gauge station with the provided ID {station_id} will be used."
                )
            station = self._get_station_metadata(station_id=station_id, ref=ref)
            if station is not None:
                # First create water level references based on station
                # Get datums
                datums = []
                # Get local datum
                datums.append(
                    DatumModel(
                        name=station["datum_name"],
                        height=us.UnitfulLength(
                            value=station["datum"], units=station["units"]
                        ).transform(self.unit_system.default_length_units),
                    )
                )
                # Get MSL
                datums.append(
                    DatumModel(
                        name="MSL",
                        height=us.UnitfulLength(
                            value=station["msl"], units=station["units"]
                        ).transform(self.unit_system.default_length_units),
                    )
                )
                # Get extras
                for name in ["MLLW", "MHHW"]:
                    height = us.UnitfulLength(
                        value=station[name.lower()], units=station["units"]
                    ).transform(self.unit_system.default_length_units)

                    wl_info = DatumModel(
                        name=name,
                        height=height,
                    )
                    datums.append(wl_info)

                station_refs = WaterlevelReferenceModel(reference=ref, datums=datums)

                # Check if we can translate the rest of the datums
                if self.water_level_references.reference != station_refs.reference:
                    for dat in self.water_level_references.datums:
                        if dat.name not in [
                            datum.name for datum in station_refs.datums
                        ]:
                            # If datum is not in the datums, try to convert it
                            h1 = dat.height
                            ref1 = self.water_level_references.reference
                            h2 = h1 + station_refs.get_datum(ref1).height
                            # Replace the datum in self.water_level_references.datums
                            dat.height = h2
                            logger.warning(
                                f"Datum '{dat.name}' converted to reference '{ref1}' with new height {h2}."
                            )

                # Check if datums already exist in the water level references and replace
                for datum in datums:
                    existing_datum = next(
                        (
                            dat
                            for dat in self.water_level_references.datums
                            if dat.name == datum.name
                        ),
                        None,
                    )
                    if existing_datum:
                        self.water_level_references.datums.remove(existing_datum)
                        logger.warning(
                            f"Datum '{datum.name}' already exists in config reference. Replacing it based on NOAA station data."
                        )
                    self.water_level_references.datums.append(datum)

                # Update reference datum
                self.water_level_references.reference = (
                    ref  # update the water level reference
                )
                logger.warning(f"Main water level reference set to '{ref}'.")

                # Add tide_gauge information in site toml
                tide_gauge = TideGauge(
                    name=station["name"],
                    description=f"observations from '{self.config.tide_gauge.source}' api",
                    source=self.config.tide_gauge.source,
                    reference=ref,
                    ID=int(station["id"]),
                    lon=station["lon"],
                    lat=station["lat"],
                    units=us.UnitTypesLength.meters,  # the api always asks for SI units right now
                )

            return tide_gauge
        else:
            logger.warning(
                f"Tide gauge source not recognized: {self.config.tide_gauge.source}. Historical events will not have an option to use gauged data in FloodAdapt!"
            )
            return None

    @debug_timer
    def create_offshore_model(self) -> Optional[FloodModel]:
        if self.sfincs_offshore_model is None:
            return None
        # Connect boundary points of overland to output points of offshore
        # First read in the boundary locations from the overland model
        fn = Path(self.sfincs_overland_model.root) / "sfincs.bnd"
        lines = []
        if fn.exists():
            with open(fn) as f:
                lines = f.readlines()
        coords = [(float(line.split()[0]), float(line.split()[1])) for line in lines]
        x, y = zip(*coords)
        bnd = gpd.GeoDataFrame(
            geometry=gpd.points_from_xy(x, y),
            crs=self.sfincs_overland_model.config["epsg"],
        )
        # Then transform points to offshore crs and save them as observation points
        obs_geo = bnd.to_crs(self.sfincs_offshore_model.config["epsg"])
        self.sfincs_offshore_model.setup_observation_points(obs_geo)
        self.sfincs_offshore_model.write()
        logger.info(
            "Output points of the offshore SFINCS model were reconfigured to the boundary points of the overland SFINCS model."
        )

        return FloodModel(
            name="offshore",
            reference=self.config.sfincs_offshore.reference,
            vertical_offset=self.config.sfincs_offshore.vertical_offset,
        )

    @debug_timer
    def create_overland_model(self) -> FloodModel:
        return FloodModel(
            name="overland",
            reference=self.config.sfincs_overland.reference,
        )

    ### SITE ###
    @debug_timer
    def create_site_config(self) -> Site:
        """Create the site configuration for the FloodAdapt model.

        The order of these functions is important!
        1. Create the SFINCS model.
            needs: water level references
            provides: updated water level references with optional tide gauge
        2. Create the FIAT model.
            needs: water level references and optional probabilistic event set
            provides: svi and exposure geometries
        3. Create the GUI model. (requires water level references and FIAT model to be updated)
            needs: water level references and FIAT model to be updated
            provides: gui model with output layers, visualization layers and plotting.

        """
        sfincs = self.create_sfincs_config()
        self.add_probabilistic_set()
        fiat = self.create_fiat_model()
        gui = self.create_gui_config()

        # Order doesnt matter from here
        lon, lat = self.read_location()
        std_objs = self.set_standard_objects()
        description = (
            self.config.description if self.config.description else self.config.name
        )
        is_coastal = self._determine_if_coastal()

        config = Site(
            name=self.config.name,
            description=description,
            lat=lat,
            lon=lon,
            fiat=fiat,
            gui=gui,
            sfincs=sfincs,
            standard_objects=std_objs,
            is_coastal=is_coastal,
        )
        return config

    @debug_timer
    def read_location(self) -> tuple[float, float]:
        # Get center of area of interest
        if not self.fiat_model.region.empty:
            center = self.fiat_model.region.dissolve().centroid.to_crs(4326)[0]
        else:
            center = self._get_fiat_building_geoms().dissolve().centroid.to_crs(4326)[0]
        return center.x, center.y

    @debug_timer
    def create_gui_config(self) -> GuiModel:
        gui = GuiModel(
            units=self.unit_system,
            plotting=self.create_hazard_plotting_config(),
            output_layers=self.create_output_layers_config(),
            visualization_layers=self.create_visualization_layers(),
        )

        return gui

    @debug_timer
    def create_default_units(self) -> GuiUnitModel:
        if self.config.unit_system == UnitSystems.imperial:
            return GuiUnitModel.imperial()
        elif self.config.unit_system == UnitSystems.metric:
            return GuiUnitModel.metric()
        else:
            raise ValueError(
                f"Unit system {self.config.unit_system} not recognized. Please choose 'imperial' or 'metric'."
            )

    @debug_timer
    def create_visualization_layers(self) -> VisualizationLayers:
        visualization_layers = VisualizationLayers(
            topography_cmin=self.topobathy_min_max[0],
            topography_cmax=self.topobathy_min_max[1],
        )
        if self._svi is not None:
            visualization_layers.add_layer(
                name="svi",
                long_name="Social Vulnerability Index (SVI)",
                path=str(self.static_path / self._svi.geom),
                database_path=self.root,
                field_name="SVI",
                bins=[0.05, 0.2, 0.4, 0.6, 0.8],
            )
        return visualization_layers

    @debug_timer
    def create_output_layers_config(self) -> OutputLayers:
        # Read default colors from template
        fd_max = self.config.gui.max_flood_depth
        ad_max = self.config.gui.max_aggr_dmg
        ftd_max = self.config.gui.max_footprint_dmg
        b_max = self.config.gui.max_benefits

        benefits_layer = None
        if self.config.probabilistic_set is not None:
            benefits_layer = BenefitsLayer(
                bins=[0, 0.01, 0.02 * b_max, 0.2 * b_max, b_max],
                colors=[
                    "#FF7D7D",
                    "#FFFFFF",
                    "#DCEDC8",
                    "#AED581",
                    "#7CB342",
                    "#33691E",
                ],
                threshold=0.0,
            )
        red_colors_6 = [
            "#FFFFFF",
            "#FEE9CE",
            "#FDBB84",
            "#FC844E",
            "#E03720",
            "#860000",
        ]

        aggregated_metrics = []

        building_count = MetricLayer(
            type="building_count",
            bins=[1, 10, 50, 200, 500],  # TODO provide max values
            colors=red_colors_6,
            filters=FilterGroup(
                conditions=[
                    FilterCondition(
                        field_name=FieldName.NAME,
                        values=["Count"],
                    ),
                    FilterCondition(
                        field_name=FieldName.LONG_NAME,
                        values=["(#)"],
                    ),
                ],
                operator=LogicalOperator.OR,
            ),
        )
        aggregated_metrics.append(building_count)

        if self.config.gui.additional_aggregated_layers:
            aggregated_metrics.extend(self.config.gui.additional_aggregated_layers)

        if self._has_roads:
            bins = [0.0001, 1, 5, 10, 20]  # in kms
            if self.unit_system == GuiUnitModel.imperial():
                # convert to miles
                bins = [
                    us.UnitfulLength(value=b * 1000, units=us.UnitTypesLength.meters)
                    .transform(us.UnitTypesLength.miles)
                    .value
                    for b in bins
                ]
            roads_length = MetricLayer(
                type="road_length",
                bins=bins,  # TODO provide max values
                colors=red_colors_6,
                filters=FilterGroup(
                    conditions=[
                        FilterCondition(
                            field_name=FieldName.NAME,
                            values=["RoadsLength"],
                        ),
                        FilterCondition(
                            field_name=FieldName.LONG_NAME,
                            values=["roads"],
                        ),
                    ],
                    operator=LogicalOperator.AND,
                ),
            )
            aggregated_metrics.append(roads_length)

        output_layers = OutputLayers(
            floodmap=FloodMapLayer(
                bins=[0.2 * fd_max, 0.6 * fd_max, fd_max],
                colors=["#D7ECFB", "#8ABDDD", "#1C73A4", "#081D58"],
                zbmax=-9999,
                depth_min=0.0,
            ),
            aggregation_dmg=AggregationDmgLayer(
                bins=[0.00001, 0.1 * ad_max, 0.25 * ad_max, 0.5 * ad_max, ad_max],
                colors=red_colors_6,
            ),
            aggregated_metrics=aggregated_metrics,
            footprints_dmg=FootprintsDmgLayer(
                bins=[0.00001, 0.06 * ftd_max, 0.2 * ftd_max, 0.4 * ftd_max, ftd_max],
                colors=red_colors_6,
            ),
            benefits=benefits_layer,
        )
        return output_layers

    @debug_timer
    def create_hazard_plotting_config(self) -> PlottingModel:
        datum_names = [datum.name for datum in self.water_level_references.datums]
        if "MHHW" in datum_names:
            amplitude = (
                self.water_level_references.get_datum("MHHW").height
                - self.water_level_references.get_datum("MSL").height
            )
            logger.info(
                f"The default tidal amplitude in the GUI will be {amplitude.transform(self.unit_system.default_length_units)}, calculated as the difference between MHHW and MSL from the tide gauge data."
            )
        else:
            amplitude = us.UnitfulLength(
                value=0.0, units=self.unit_system.default_length_units
            )
            logger.warning(
                "The default tidal amplitude in the GUI will be 0.0, since no tide-gauge water levels are available. You can change this in the site.toml with the 'gui.tide_harmonic_amplitude' attribute."
            )

        ref = "MSL"
        if ref not in datum_names:
            logger.warning(
                f"The Mean Sea Level (MSL) datum is not available in the site.toml. The synthetic tide will be created relative to the main reference: {self.water_level_references.reference}."
            )
            ref = self.water_level_references.reference

        plotting = PlottingModel(
            synthetic_tide=SyntheticTideModel(
                harmonic_amplitude=amplitude,
                datum=ref,
            ),
            excluded_datums=self.config.excluded_datums,
        )

        return plotting

    @debug_timer
    def create_infometrics(self):
        # Define paths for infometrics and infographics templates
        path_im = self.root.joinpath("static", "templates", "infometrics")
        path_ig = self.root.joinpath("static", "templates", "infographics")

        # Create directories and ensure they are empty
        for path in [path_im, path_ig]:
            if path.exists():
                shutil.rmtree(path)
                path.mkdir(parents=True, exist_ok=True)

        # Use images and css from the database builder templates
        templates_path = (
            Path(__file__).parent.resolve().joinpath("templates", "infographics")
        )
        shutil.copytree(templates_path, path_ig)

        # Create Metrics object
        metrics = Metrics(
            dmg_unit=self.read_damage_unit(),
            return_periods=self.create_risk_model().return_periods,
        )

        # First define the mandatory metrics
        self._create_mandatory_metrics(metrics)

        # Then the infographic metrics if needed
        if self.config.infographics:
            self._create_event_infographics(metrics)
            if self._probabilistic_set_name is not None:
                self._create_risk_infographics(metrics)

        # Then the additional metrics if needed
        self._add_additional_event_metrics(metrics)
        if self._probabilistic_set_name is not None:
            self._add_additional_risk_metrics(metrics)

        # Write the metrics config files
        self._write_infometrics(metrics, path_im, path_ig)

        self.metrics = metrics

    def _create_mandatory_metrics(self, metrics: Metrics):
        metrics.create_mandatory_metrics_event()
        if self._probabilistic_set_name is not None:
            metrics.create_mandatory_metrics_risk()

    def _create_event_infographics(self, metrics: Metrics):
        exposure_type = self._get_exposure_type()
        # If not specific infographic config is given, create a standard one
        if not self.config.event_infographics:
            buildings, svi, roads = None, None, None
            if exposure_type is None:
                logger.warning(
                    "No exposure type could be identified from the FIAT model. Standard event building infographics cannot be created."
                )
            else:
                buildings = BuildingsInfographicModel.get_template(type=exposure_type)
                if self.config.svi is not None:
                    svi = HomesInfographicModel.get_template(
                        svi_threshold=self.config.svi.threshold, type=exposure_type
                    )
                else:
                    logger.warning(
                        "No SVI information available. Standard event SVI infographics cannot be created."
                    )
                if self._has_roads:
                    roads = RoadsInfographicModel.get_template(
                        unit_system=self.config.unit_system.value
                    )
                else:
                    logger.warning(
                        "No roads available in the exposure. Standard event road infographics cannot be created."
                    )
            self.config.event_infographics = EventInfographicModel(
                buildings=buildings, svi=svi, roads=roads
            )
        metrics.create_infographics_metrics_event(config=self.config.event_infographics)

    def _create_risk_infographics(self, metrics: Metrics):
        exposure_type = self._get_exposure_type()
        # If not specific infographic config is given, create a standard one
        if not self.config.risk_infographics:
            if exposure_type is None:
                logger.warning(
                    "No exposure type could be identified from the FIAT model. Standard risk building infographics cannot be created."
                )
            else:
                self.config.risk_infographics = RiskInfographicModel.get_template(
                    svi_threshold=self.config.svi.threshold
                    if self.config.svi
                    else None,
                    type=exposure_type,
                )
        metrics.create_infographics_metrics_risk(config=self.config.risk_infographics)

    def _add_additional_event_metrics(self, metrics: Metrics):
        if self.config.event_additional_infometrics:
            for metric in self.config.event_additional_infometrics:
                metrics.add_event_metric(metric)

    def _add_additional_risk_metrics(self, metrics: Metrics):
        if self.config.risk_additional_infometrics:
            for metric in self.config.risk_additional_infometrics:
                metrics.add_risk_metric(metric)

    def _write_infometrics(self, metrics: Metrics, path_im: Path, path_ig: Path):
        if self._aggregation_areas is None:
            self._aggregation_areas = self.create_aggregation_areas()
        aggr_levels = [aggr.name for aggr in self._aggregation_areas]
        metrics.write(
            metrics_path=path_im,
            aggregation_levels=aggr_levels,
            infographics_path=path_ig,
        )

    def _determine_if_coastal(self) -> bool:
        if self.config.is_coastal is not None:
            # if coastal information is provided in the config, use it.
            if self.config.is_coastal:
                msg = f"Based on the config input 'is_coastal={self.config.is_coastal}', the site is classified as coastal."
            else:
                msg = f"Based on the config input 'is_coastal={self.config.is_coastal}', the site is classified as inland."
            logger.info(msg)
            return self.config.is_coastal

        logger.warning(
            "Explicit information on site type was not provided in the config with the 'is_coastal' parameter. The coastal/inland classification will be determined based on the SFINCS model characteristics."
        )

        # Otherwise determine based on the SFINCS model characteristics.
        if self.sfincs_offshore_model is not None:
            logger.info(
                "An offshore SFINCS model was provided, so the site is classified as coastal."
            )
            return True

        has_bnd = self._determine_if_wl_boundaries()

        if has_bnd:  # and not coastal. How to distinguish between inland with boundary and coastal without offshore model?
            logger.info(
                "Water level boundaries detected in the SFINCS overland model. The site is classified as coastal."
            )
            return True
        else:
            logger.info(
                "No water level boundaries detected in the SFINCS overland model. The site is classified as inland."
            )
            return False

    def _determine_if_wl_boundaries(self) -> bool:
        # https://sfincs.readthedocs.io/en/latest/parameters.html
        mask = (
            self.sfincs_overland_model.mask
            if self.sfincs_overland_model.mask is not None
            else xr.DataArray()
        )
        mask_has_bnd = bool(
            (mask == 2).any()
        )  # boundary points are marked with 2 in the SFINCS mask
        has_bnd_points = (
            "bndfile" in self.sfincs_overland_model.config
        )  # check if boundary points are specified
        if mask_has_bnd and has_bnd_points:
            has_bnd = True
        elif mask_has_bnd and not has_bnd_points:
            raise ValueError(
                "The SFINCS overland model mask indicates the presence of boundary points, but no boundary file is specifie in SFINCS input. This may lead to issues in the model setup"
            )
        elif has_bnd_points:
            raise ValueError(
                "A boundary file specified in the SFINCS overland model input, but the mask does not include water levels."
            )
        else:
            has_bnd = False
        return has_bnd

    @debug_timer
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
            path_1 = self.static_path / folder
            shutil.copytree(path_0, path_1)

        # Check table values
        green_infra_path = (
            self.static_path / "green_infra_table" / "green_infra_lookup_table.csv"
        )
        df = pd.read_csv(green_infra_path)
        # Convert "Infiltration depth (feet)" to the database unit system and rename column
        # Find the column that has "Infiltration depth" in its name
        infiltration_col = next(
            (col for col in df.columns if "Infiltration depth" in col), None
        )
        # Try to infer the units from the column name, e.g., "Infiltration depth (feet)"
        match = re.search(r"\((.*?)\)", infiltration_col)
        current_units = match.group(1).strip()

        # Determine target units and column name
        if self.unit_system.default_length_units != current_units:
            target_units = self.unit_system.default_length_units
            new_col = f"Infiltration depth ({target_units.value})"
            conversion_factor = us.UnitfulLength(
                value=1.0, units=current_units
            ).convert(target_units)

            df[new_col] = (df[infiltration_col] * conversion_factor).round(2)
            df = df.drop(columns=[infiltration_col])
            # Save the updated table
            df.to_csv(green_infra_path, index=False)

    @debug_timer
    def add_probabilistic_set(self):
        # Copy prob set if given
        if self.config.probabilistic_set:
            logger.info(
                f"Probabilistic event set imported from {self.config.probabilistic_set}"
            )
            prob_event_name = Path(self.config.probabilistic_set).name
            path_db = self.root.joinpath("input", "events", prob_event_name)
            shutil.copytree(self.config.probabilistic_set, path_db)
            self._probabilistic_set_name = prob_event_name
        else:
            logger.warning(
                "Probabilistic event set not provided. Risk scenarios cannot be run in FloodAdapt."
            )
            self._probabilistic_set_name = None

    ### HELPER FUNCTIONS ###
    def make_folder_structure(self) -> None:
        """
        Create the folder structure for the database.

        This method creates the necessary folder structure for the FloodAdapt database, including
        the input and static folders. It also creates subfolders within the input and
        static folders based on a predefined list of names.
        """
        logger.info("Preparing the database folder structure.")
        inputs = [
            "events",
            "projections",
            "measures",
            "strategies",
            "scenarios",
            "benefits",
        ]
        for name in inputs:
            (self.root / "input" / name).mkdir(parents=True, exist_ok=True)

        # Prepare static folder structure
        folders = ["templates", "config"]
        for name in folders:
            (self.static_path / name).mkdir(parents=True, exist_ok=True)

    def _check_exists_and_absolute(self, path: str) -> Path:
        """Check if the path is absolute or relative and return a Path object. Raises an error if the path is not valid."""
        if not Path(path).exists():
            raise FileNotFoundError(f"Path {path} does not exist.")

        if Path(path).is_absolute():
            return Path(path)
        else:
            raise ValueError(f"Path {path} is not absolute.")

    def _get_fiat_building_geoms(self) -> gpd.GeoDataFrame:
        """
        Get the building geometries from the FIAT model.

        Returns
        -------
        gpd.GeoDataFrame
            A GeoDataFrame containing the building geometries.
        """
        building_indices = self._get_fiat_building_index()
        buildings = pd.concat(
            [self.fiat_model.exposure.exposure_geoms[i] for i in building_indices],
            ignore_index=True,
        )
        return buildings

    @debug_timer
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
        buildings = self._get_fiat_building_geoms()
        exposure_csv = self.fiat_model.exposure.exposure_db
        if "BF_FID" in exposure_csv.columns:
            logger.warning(
                "Column 'BF_FID' already exists in the exposure columns and will be replaced."
            )
            del exposure_csv["BF_FID"]
        buildings_joined, building_footprints = self.spatial_join(
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
        bf_folder = Path(self.fiat_model.root) / "exposure" / "building_footprints"
        bf_folder.mkdir(parents=True, exist_ok=True)

        # Save the spatial file for future use
        geo_path = bf_folder / "building_footprints.gpkg"
        building_footprints.to_file(geo_path)

        # Save to exposure csv
        exposure_csv = exposure_csv.merge(
            buildings_joined, on=_FIAT_COLUMNS.object_id, how="left"
        )

        # Set model building footprints
        self.fiat_model.building_footprint = building_footprints
        self.fiat_model.exposure.exposure_db = self._clean_suffix_columns(exposure_csv)

        # Save site attributes
        buildings_path = geo_path.relative_to(self.static_path)
        logger.info(
            f"Building footprints saved at {(self.static_path / buildings_path).resolve().as_posix()}"
        )

        return buildings_path

    @debug_timer
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
        clip_footprints : bool, default True
            Whether to clip the building footprints to the hazard area.

        Returns
        -------
        None
        """
        gdf = self._get_fiat_gdf_full()

        crs = gdf.crs
        sfincs_extend = self.sfincs_overland_model.region
        sfincs_extend = sfincs_extend.to_crs(crs)

        # Clip the fiat region
        clipped_region = self.fiat_model.region.to_crs(crs).clip(sfincs_extend)
        self.fiat_model.geoms["region"] = clipped_region

        # Clip the exposure geometries
        gdf = self._clip_gdf(gdf, sfincs_extend, predicate="within")

        # Save exposure dataframe
        del gdf["geometry"]
        self.fiat_model.exposure.exposure_db = gdf.reset_index(drop=True)

        # Make
        self._delete_extra_geometries()

        # Clip the building footprints
        fieldname = "BF_FID"
        if clip_footprints and not self.fiat_model.building_footprint.empty:
            # Get buildings after filtering and their footprint id
            self.fiat_model.building_footprint = self.fiat_model.building_footprint[
                self.fiat_model.building_footprint[fieldname].isin(gdf[fieldname])
            ].reset_index(drop=True)

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

    @staticmethod
    @debug_timer
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
        if field_name in objects.columns:
            layer = layer.rename(columns={field_name: "layer_field"})
            field_name = "layer_field"
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

    def _get_fiat_building_index(self) -> list[int]:
        names = self.config.fiat_buildings_name
        if isinstance(names, str):
            names = [names]
        indices = [
            self.fiat_model.exposure.geom_names.index(name)
            for name in names
            if name in self.fiat_model.exposure.geom_names
        ]
        if indices:
            return indices
        raise ValueError(
            f"None of the specified building geometry names {names} found in FIAT model exposure geom_names."
        )

    def _get_fiat_road_index(self) -> int:
        return self.fiat_model.exposure.geom_names.index(self.config.fiat_roads_name)

    @debug_timer
    def _get_closest_station(self):
        # Get available stations from source
        obs_data = obs.source(self.config.tide_gauge.source)
        obs_data.get_active_stations()
        obs_stations = obs_data.gdf()
        # Calculate distance from SFINCS region to all available stations in degrees
        obs_stations["distance"] = obs_stations.distance(
            self.sfincs_overland_model.region.to_crs(4326).geometry.item()
        )
        # Get the closest station and its distance in meters
        closest_station = obs_stations[
            obs_stations["distance"] == obs_stations["distance"].min()
        ]
        distance = round(
            closest_station.to_crs(self.sfincs_overland_model.region.crs)
            .distance(self.sfincs_overland_model.region.geometry.item())
            .item(),
            0,
        )

        distance = us.UnitfulLength(value=distance, units=us.UnitTypesLength.meters)
        logger.info(
            f"The closest tide gauge from {self.config.tide_gauge.source} is located {distance.transform(self.unit_system.default_length_units)} from the SFINCS domain"
        )
        # Check if user provided max distance
        # TODO make sure units are explicit for max_distance
        if self.config.tide_gauge.max_distance is not None:
            units_new = self.config.tide_gauge.max_distance.units
            distance_new = us.UnitfulLength(
                value=distance.convert(units_new), units=units_new
            )
            if distance_new.value > self.config.tide_gauge.max_distance.value:
                logger.warning(
                    f"This distance is larger than the 'max_distance' value of {self.config.tide_gauge.max_distance.value} {units_new} provided in the config file. The station cannot be used."
                )
                return None

        # get station id
        station_id = closest_station["id"].item()

        return station_id

    @debug_timer
    def _get_station_metadata(self, station_id: str, ref: str = "MLLW"):
        """
        Find the closest tide gauge station to the SFINCS domain and retrieves its metadata.

        Args:
            station_id (str): The ID of the tide gauge station.
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
        # read station metadata
        station_metadata = obs_data.get_meta_data(station_id)
        # TODO check if all stations can be used? Tidal attr?
        # Get water levels by using the ref provided
        datum_name = station_metadata["datums"]["OrthometricDatum"]
        datums = station_metadata["datums"]["datums"]
        names = [datum["name"] for datum in datums]

        ref_value = datums[names.index(ref)]["value"]

        meta = {
            "id": station_id,
            "name": station_metadata["name"],
            "datum": round(datums[names.index(datum_name)]["value"] - ref_value, 3),
            "datum_name": datum_name,
            "msl": round(datums[names.index("MSL")]["value"] - ref_value, 3),
            "mllw": round(datums[names.index("MLLW")]["value"] - ref_value, 3),
            "mhhw": round(datums[names.index("MHHW")]["value"] - ref_value, 3),
            "reference": ref,
            "units": station_metadata["datums"]["units"],
            "lon": station_metadata["lng"],
            "lat": station_metadata["lat"],
        }

        logger.info(
            f"The tide gauge station '{station_metadata['name']}' from {self.config.tide_gauge.source} will be used to download nearshore historical water level time-series."
        )

        logger.info(
            f"The station metadata will be used to fill in the water_level attribute in the site.toml. The reference level will be '{ref}'."
        )

        return meta

    def _get_bin_colors(self):
        """
        Retrieve the bin colors from the bin_colors.toml file.

        Returns
        -------
            dict: A dictionary containing the bin colors.
        """
        templates_path = Path(__file__).parent.resolve().joinpath("templates")
        return read_toml(templates_path.joinpath("output_layers", "bin_colors.toml"))

    def _delete_extra_geometries(self) -> None:
        """
        Remove extra geometries from the exposure_geoms list that do not have a corresponding object_id in the exposure_db DataFrame.

        Returns
        -------
            None
        """
        # Make sure only csv objects have geometries
        for i, geoms in enumerate(self.fiat_model.exposure.exposure_geoms):
            if _FIAT_COLUMNS.object_id not in geoms.columns:
                logger.warning(
                    f"Geometry '{self.fiat_model.exposure.geom_names[i]}' does not have an '{_FIAT_COLUMNS.object_id}' column and will be ignored."
                )
                continue
            keep = geoms[_FIAT_COLUMNS.object_id].isin(
                self.fiat_model.exposure.exposure_db[_FIAT_COLUMNS.object_id]
            )
            geoms = geoms[keep].reset_index(drop=True)
            self.fiat_model.exposure.exposure_geoms[i] = geoms

    def _get_exposure_type(self) -> Literal["OSM", "NSI", None]:
        # Define the allowed types for OSM
        osm_types = ["residential", "commercial", "industrial", "road"]
        nsi_types = ["RES", "COM", "IND", "PUB", "road"]
        unique_types = set(
            self.fiat_model.exposure.exposure_db[
                _FIAT_COLUMNS.primary_object_type
            ].unique()
        )
        if unique_types.issubset(set(osm_types)):
            return "OSM"
        elif unique_types.issubset(set(nsi_types)):
            return "NSI"
        else:
            return None

    def _get_fiat_gdf_full(self) -> gpd.GeoDataFrame:
        """
        Get the full GeoDataFrame of the Fiat model.

        Returns
        -------
            gpd.GeoDataFrame: The full GeoDataFrame of the Fiat model.
        """
        gdf = self.fiat_model.exposure.get_full_gdf(
            self.fiat_model.exposure.exposure_db
        )
        # Keep only unique "object_id" rows, keeping the first occurrence
        gdf = gdf.drop_duplicates(
            subset=_FIAT_COLUMNS.object_id, keep="first"
        ).reset_index(drop=True)

        return gdf

    @staticmethod
    def _clean_suffix_columns(df: pd.DataFrame) -> pd.DataFrame:
        """Detect and resolves duplicate columns with _x/_y suffixes that appear after a pandas merge.

        (e.g., 'Aggregation Label: Census Blockgroup_x' and 'Aggregation Label: Census Blockgroup_y').

        Keeps the first non-null column of each pair and removes redundant ones.
        """
        cols = df.columns.tolist()
        suffix_pairs = {}

        for col in cols:
            if col.endswith("_x"):
                base = col[:-2]
                if f"{base}_y" in df.columns:
                    suffix_pairs[base] = (f"{base}_x", f"{base}_y")

        for base, (col_x, col_y) in suffix_pairs.items():
            # If both columns exist, prefer the one with more non-null values
            x_notna = df[col_x].notna().sum()
            y_notna = df[col_y].notna().sum()
            keep_col = col_x if x_notna >= y_notna else col_y
            df[base] = df[keep_col]

            # Drop the old suffixed versions
            df = df.drop(columns=[col_x, col_y])

        return df


def create_database(config: Union[str, Path, ConfigModel], overwrite=False) -> None:
    """Create a new database from a configuration file or ConfigModel.

    Parameters
    ----------
    config : str, Path, or ConfigModel
        The path to the configuration file (as a string or Path) or a ConfigModel instance.
    overwrite : bool, default False
        Whether to overwrite the existing database if it exists.
    """
    if isinstance(config, (str, Path)):
        config = ConfigModel.read(config)

    DatabaseBuilder(config=config).build(overwrite)


def main():
    while True:
        config_path = Path(
            input(
                "Please provide the path to the database creation configuration toml: \n"
            )
        )
        print(
            "Please select the log verbosity level for the database creation process.\n"
            "From most verbose to least verbose: `DEBUG`, `INFO`, `WARNING`.'n"
        )
        log_level = input("Enter log level: ")
        match log_level:
            case "DEBUG":
                level = logging.DEBUG
            case "INFO":
                level = logging.INFO
            case "WARNING":
                level = logging.WARNING
            case _:
                print(
                    f"Log level `{log_level}` not recognized. Defaulting to INFO. Please choose from: `DEBUG`, `INFO`, `WARNING`."
                )
                log_level = "INFO"
                level = logging.INFO

        FloodAdaptLogging(level=level)

        try:
            config = ConfigModel.read(config_path)
            dbs = DatabaseBuilder(config)
            dbs.build()
        except Exception as e:
            print(e)
        quit = input("Do you want to quit? (y/n)")
        if quit == "y":
            exit()


if __name__ == "__main__":
    main()
