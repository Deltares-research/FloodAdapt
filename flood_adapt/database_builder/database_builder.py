import datetime
import math
import os
import shutil
import warnings
from enum import Enum
from pathlib import Path
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
from hydromt_fiat import FiatModel as HydromtFiatModel
from hydromt_fiat.data_apis.open_street_maps import get_buildings_from_osm
from hydromt_sfincs import SfincsModel as HydromtSfincsModel
from pydantic import BaseModel, Field
from shapely import MultiLineString, MultiPolygon, Polygon

from flood_adapt.adapter.fiat_adapter import _FIAT_COLUMNS
from flood_adapt.config.fiat import (
    AggregationModel,
    BenefitsModel,
    BFEModel,
    EquityModel,
    FiatConfigModel,
    FiatModel,
    RiskModel,
    SVIModel,
)
from flood_adapt.config.gui import (
    AggregationDmgLayer,
    BenefitsLayer,
    FloodMapLayer,
    FootprintsDmgLayer,
    GuiModel,
    GuiUnitModel,
    OutputLayers,
    PlottingModel,
    SyntheticTideModel,
    VisualizationLayers,
)
from flood_adapt.config.sfincs import (
    Cstype,
    CycloneTrackDatabaseModel,
    DatumModel,
    DemModel,
    FloodmapType,
    FloodModel,
    ObsPointModel,
    RiverModel,
    SCSModel,
    SfincsConfigModel,
    SfincsModel,
    SlrScenariosModel,
    WaterlevelReferenceModel,
)
from flood_adapt.config.site import (
    Site,
    StandardObjectModel,
)
from flood_adapt.dbs_classes.database import Database
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
    return path.as_posix()


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


class SviConfigModel(SpatialJoinModel):
    """
    Represents a model for the Social Vulnerability Index (SVI).

    Attributes
    ----------
        threshold (float): The threshold value for the SVI model to specify vulnerability.
    """

    threshold: float


class Point(BaseModel):
    lat: float
    lon: float


class TideGaugeConfigModel(BaseModel):
    """
    Represents a tide gauge model.

    Attributes
    ----------
        source (str): The source of the tide gauge data.
        file (Optional[str]): The file associated with the tide gauge data (default: None).
        max_distance (Optional[float]): The maximum distance (default: None).
        ref (str): The reference name. Should be defined in the water level references.
    """

    source: TideGaugeSource
    description: str = ""
    ref: Optional[str] = None
    id: Optional[int] = None
    lon: Optional[float] = None
    lat: Optional[float] = None
    file: Optional[str] = None
    max_distance: Optional[us.UnitfulLength] = None


class SviModel(SpatialJoinModel):
    """
    Represents a model for the Social Vulnerability Index (SVI).

    Attributes
    ----------
        threshold (float): The threshold value for the SVI model to specify vulnerability.
    """

    threshold: float


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
    slr_scenarios : Optional[SlrModelDef], default SlrModelDef()
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

    # General
    name: str = Field(..., min_length=1, pattern='^[^<>:"/\\\\|?* ]*$')
    description: Optional[str] = None
    database_path: Optional[str] = None
    unit_system: UnitSystems
    gui: GuiConfigModel
    infographics: Optional[bool] = True

    # FIAT
    fiat: str
    aggregation_areas: Optional[list[SpatialJoinModel]] = None
    building_footprints: Optional[SpatialJoinModel | FootprintsOptions] = (
        FootprintsOptions.OSM
    )
    fiat_buildings_name: Optional[str] = "buildings"
    fiat_roads_name: Optional[str] = "roads"
    bfe: Optional[SpatialJoinModel] = None
    svi: Optional[SviConfigModel] = None
    road_width: Optional[float] = 5
    return_periods: list[int] = Field(default_factory=list)

    # SFINCS
    references: WaterlevelReferenceModel = WaterlevelReferenceModel(
        reference="MSL",
        datums=[
            DatumModel(
                name="MSL",
                height=us.UnitfulLength(value=0.0, units=us.UnitTypesLength.meters),
            ),
        ],
    )

    sfincs_overland: FloodModel
    sfincs_offshore: Optional[FloodModel] = None
    dem: Optional[DemModel] = None

    excluded_datums: list[str] = Field(default_factory=list)

    slr_scenarios: Optional[SlrScenariosModel] = None
    scs: Optional[SCSModel] = None
    tide_gauge: Optional[TideGaugeConfigModel] = None
    cyclones: Optional[bool] = True
    cyclone_basin: Optional[Basins] = None
    obs_point: Optional[list[ObsPointModel]] = None
    probabilistic_set: Optional[str] = None

    @staticmethod
    def read(toml_path: Path) -> "ConfigModel":
        """
        Read a configuration file and returns the validated attributes.

        Args:
            config (str): The path to the configuration file.

        Returns
        -------
            ConfigModel: The validated attributes from the configuration file.
        """
        with open(toml_path, mode="rb") as fp:
            toml = tomli.load(fp)
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


class DatabaseBuilder:
    logger = FloodAdaptLogging.getLogger("DatabaseBuilder")

    _has_roads: bool = False
    _aggregation_areas: Optional[list] = None
    _probabilistic_set_name: Optional[str] = None

    def __init__(self, config: ConfigModel, overwrite: bool = True):
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

        # Read info that needs to be updated with other model info
        self.water_level_references = self.config.references

    @property
    def static_path(self) -> Path:
        return self.root / "static"

    def build(self, overwrite: bool = False) -> None:
        # Check if database already exists
        if self.root.exists() and not overwrite:
            raise ValueError(
                f"There is already a Database folder in '{self.root.as_posix()}'."
            )
        if self.root.exists() and overwrite:
            shutil.rmtree(self.root)
            warnings.warn(
                f"There is already a Database folder in '{self.root.as_posix()}, which will be overwritten'."
            )
        # Create database folder
        self.root.mkdir(parents=True)

        with FloodAdaptLogging.to_file(
            file_path=self.root.joinpath("database_builder.log")
        ):
            self.logger.info(
                f"Creating a FloodAdapt database in '{self.root.as_posix()}'"
            )

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
            self.logger.info("FloodAdapt database creation finished!")

    def setup(self) -> None:
        # Create the models
        self.make_folder_structure()

        # Read user models and copy to templates
        self.read_template_fiat_model()
        self.read_template_sfincs_overland_model()
        self.read_template_sfincs_offshore_model()

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

    def create_standard_objects(self):
        with modified_environ(
            DATABASE_ROOT=str(self.root.parent),
            DATABASE_NAME=self.root.name,
        ):
            self.logger.info(
                "Creating `no measures` strategy and `current` projection."
            )
            # Create database instance
            db = Database(self.root.parent, self.config.name)
            # Create no measures strategy
            strategy = Strategy(
                name=self._no_measures_strategy_name,
                measures=[],
            )
            db.strategies.save(strategy)
            # Create current projection
            projection = Projection(
                name=self._current_projection_name,
                physical_projection=PhysicalProjection(),
                socio_economic_change=SocioEconomicChange(),
            )
            db.projections.save(projection)
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

    ### TEMPLATE READERS ###
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
    def create_fiat_model(self) -> FiatModel:
        fiat = FiatModel(
            config=self.create_fiat_config(),
            benefits=self.create_benefit_config(),
            risk=self.create_risk_model(),
        )
        return fiat

    def create_risk_model(self) -> Optional[RiskModel]:
        # Check if return periods are provided
        if not self.config.return_periods:
            if self._probabilistic_set_name:
                risk = RiskModel()
                self.logger.warning(
                    f"No return periods provided, but a probabilistic set is available. Using default return periods {risk.return_periods}."
                )
                return risk
            else:
                self.logger.warning(
                    "No return periods provided and no probabilistic set available. Risk calculations will not be performed."
                )
                return None
        else:
            risk = RiskModel(return_periods=self.config.return_periods)
        return risk

    def create_benefit_config(self) -> Optional[BenefitsModel]:
        if self._probabilistic_set_name is None:
            self.logger.warning(
                "No probabilistic set found in the config, benefits will not be available."
            )
            return None
        return BenefitsModel(
            current_year=datetime.datetime.now().year,
            current_projection="current",
            baseline_strategy="no_measures",
            event_set=self._probabilistic_set_name,
        )

    def create_fiat_config(self) -> FiatConfigModel:
        # Make sure only csv objects have geometries
        for i, geoms in enumerate(self.fiat_model.exposure.exposure_geoms):
            keep = geoms[_FIAT_COLUMNS.object_id].isin(
                self.fiat_model.exposure.exposure_db[_FIAT_COLUMNS.object_id]
            )
            geoms = geoms[keep].reset_index(drop=True)
            self.fiat_model.exposure.exposure_geoms[i] = geoms

        footprints = self.create_footprints()
        if footprints is not None:
            footprints = footprints.as_posix()

        # Clip hazard and reset buildings # TODO use hydromt-FIAT instead
        if not self.fiat_model.region.empty:
            self._clip_hazard_extend()

        # Store result for possible future use in create_infographics
        self._aggregation_areas = self.create_aggregation_areas()

        roads_gpkg = self.create_roads()
        non_building_names = []
        if roads_gpkg is not None:
            non_building_names.append("road")

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
        # Update FIAT model with the new config
        self.fiat_model.write()

        return config

    def update_fiat_elevation(self):
        """
        Update the ground elevations of FIAT objects based on the SFINCS ground elevation map.

        This method reads the DEM file and the exposure CSV file, and updates the ground elevations
        of the FIAT objects (roads and buildings) based on the nearest elevation values from the DEM.
        """
        dem_file = self._dem_path
        # TODO resolve issue with double geometries in hydromt-FIAT and use update_ground_elevation method instead
        # self.fiat_model.update_ground_elevation(dem_file, grnd_elev_unit="meters")
        self.logger.info(
            "Updating FIAT objects ground elevations from SFINCS ground elevation map."
        )
        SFINCS_units = us.UnitfulLength(
            value=1.0, units=us.UnitTypesLength.meters
        )  # SFINCS is always in meters
        FIAT_units = self.unit_system.default_length_units
        conversion_factor = SFINCS_units.convert(FIAT_units)

        if not math.isclose(conversion_factor, 1):
            self.logger.info(
                f"Ground elevation for FIAT objects is in '{FIAT_units}', while SFINCS ground elevation is in 'meters'. Values in the exposure csv will be converted by a factor of {conversion_factor}"
            )

        exposure = self.fiat_model.exposure.exposure_db
        dem = rxr.open_rasterio(dem_file)
        # TODO make sure only fiat_model object changes take place!
        if self.config.fiat_roads_name in self.fiat_model.exposure.geom_names:
            roads = self.fiat_model.exposure.exposure_geoms[
                self._get_fiat_road_index()
            ].to_crs(dem.spatial_ref.crs_wkt)
            roads["centroid"] = roads.geometry.centroid  # get centroids

            x_points = xr.DataArray(roads["centroid"].x, dims="points")
            y_points = xr.DataArray(roads["centroid"].y, dims="points")
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
            self.fiat_model.exposure.exposure_db = exposure

        buildings = self.fiat_model.exposure.exposure_geoms[
            self._get_fiat_building_index()
        ].to_crs(dem.spatial_ref.crs_wkt)
        buildings["geometry"] = buildings.geometry.centroid
        x_points = xr.DataArray(buildings["geometry"].x, dims="points")
        y_points = xr.DataArray(buildings["geometry"].y, dims="points")
        buildings["elev"] = (
            dem.sel(x=x_points, y=y_points, band=1, method="nearest").to_numpy()
            * conversion_factor
        )
        exposure = exposure.merge(
            buildings[[_FIAT_COLUMNS.object_id, "elev"]],
            on=_FIAT_COLUMNS.object_id,
            how="left",
        )
        exposure.loc[
            exposure[_FIAT_COLUMNS.primary_object_type] != "road",
            _FIAT_COLUMNS.ground_elevation,
        ] = exposure.loc[exposure[_FIAT_COLUMNS.primary_object_type] != "road", "elev"]
        del exposure["elev"]

    def read_damage_unit(self) -> str:
        if self.fiat_model.exposure.damage_unit is not None:
            return self.fiat_model.exposure.damage_unit
        else:
            self.logger.warning(
                "Delft-FIAT model was missing damage units so '$' was assumed."
            )
            return "$"

    def read_floodmap_type(self) -> FloodmapType:
        # If there is at least on object that uses the area method, use water depths for FA calcs
        if (
            self.fiat_model.exposure.exposure_db[_FIAT_COLUMNS.extraction_method]
            == "area"
        ).any():
            return FloodmapType.water_depth
        else:
            return FloodmapType.water_level

    def create_roads(self) -> Optional[str]:
        # Make sure that FIAT roads are polygons
        if self.config.fiat_roads_name not in self.fiat_model.exposure.geom_names:
            self.logger.warning(
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
            self.fiat_model.exposure.exposure_geoms[self._get_fiat_road_index()] = roads
            self.logger.info(
                f"FIAT road objects transformed from lines to polygons assuming a road width of {self.config.road_width} meters."
            )

        self._has_roads = True
        return f"{self.config.fiat_roads_name}.gpkg"

    def create_new_developments(self) -> Optional[str]:
        return "new_development_area.gpkg"

    def create_footprints(self) -> Optional[Path]:
        if isinstance(self.config.building_footprints, SpatialJoinModel):
            # Use the provided building footprints
            building_footprints_file = self._check_exists_and_absolute(
                self.config.building_footprints.file
            )

            self.logger.info(
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
            self.logger.info(
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
            self.fiat_model.exposure.exposure_geoms[
                self._get_fiat_building_index()
            ].geometry.iloc[0],
            (Polygon, MultiPolygon),
        ):
            self.logger.info(
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

            self.logger.info(
                f"Using the building footprints located at {footprints_path}."
            )
            return footprints_path.relative_to(self.static_path)

        # Other methods
        else:
            self.logger.warning(
                "No building footprints are available. Buildings will be plotted with a default shape in FloodAdapt."
            )
            return None

    def create_bfe(self) -> Optional[BFEModel]:
        if self.config.bfe is None:
            self.logger.warning(
                "No base flood elevation provided. Elevating building relative to base flood elevation will not be possible in FloodAdapt."
            )
            return None

        # TODO can we use hydromt-FIAT?
        bfe_file = self._check_exists_and_absolute(self.config.bfe.file)

        self.logger.info(
            f"Using map from {Path(bfe_file).as_posix()} as base flood elevation."
        )

        # Spatially join buildings and map
        buildings_joined, bfe = self.spatial_join(
            self.fiat_model.exposure.exposure_geoms[self._get_fiat_building_index()],
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

        # Save attributes
        return BFEModel(
            geom=fa_bfe_file.relative_to(self.static_path).as_posix(),
            table=csv_path.relative_to(self.static_path).as_posix(),
            field_name=self.config.bfe.field_name,
        )

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

                self.logger.info(
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
                    raise ValueError(
                        f"Aggregation area '{aggr_name}' already exists in the FIAT model."
                    )
                # Do spatial join of FIAT objects and aggregation areas
                exposure_csv = self.fiat_model.exposure.exposure_db
                buildings_joined, aggr_areas = self.spatial_join(
                    objects=self.fiat_model.exposure.exposure_geoms[
                        self._get_fiat_building_index()
                    ],
                    layer=str(self._check_exists_and_absolute(aggr.file)),
                    field_name=aggr.field_name,
                    rename=_FIAT_COLUMNS.aggregation_label.format(name=aggr_name),
                )
                aggr_path = Path(self.fiat_model.root).joinpath(
                    "exposure", "aggregation_areas", f"{Path(aggr.file).stem}.gpkg"
                )
                aggr_path.parent.mkdir(parents=True, exist_ok=True)
                aggr_areas.to_file(aggr_path)
                exposure_csv = exposure_csv.merge(
                    buildings_joined, on=_FIAT_COLUMNS.object_id, how="left"
                )
                self.fiat_model.exposure.exposure_db = exposure_csv
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
            buildings_joined, _ = self.spatial_join(
                objects=self.fiat_model.exposure.exposure_geoms[
                    self._get_fiat_building_index()
                ],
                layer=region,
                field_name="aggr_id",
                rename=_FIAT_COLUMNS.aggregation_label.format(name="region"),
            )
            exposure_csv = exposure_csv.merge(
                buildings_joined, on=_FIAT_COLUMNS.object_id, how="left"
            )
            self.fiat_model.exposure.exposure_db = exposure_csv
            self.logger.warning(
                "No aggregation areas were available in the FIAT model and none were provided in the config file. The region file will be used as a mock aggregation area."
            )
        return aggregation_areas

    def create_svi(self) -> Optional[SVIModel]:
        if self.config.svi:
            svi_file = self._check_exists_and_absolute(self.config.svi.file)
            exposure_csv = self.fiat_model.exposure.exposure_db
            buildings_joined, svi = self.spatial_join(
                self.fiat_model.exposure.exposure_geoms[
                    self._get_fiat_building_index()
                ],
                svi_file,
                self.config.svi.field_name,
                rename="SVI",
                filter=True,
            )
            # Add column to exposure
            if "SVI" in exposure_csv.columns:
                self.logger.info(
                    f"'SVI' column in the FIAT exposure csv will be replaced by {svi_file.as_posix()}."
                )
                del exposure_csv["SVI"]
            else:
                self.logger.info(
                    f"'SVI' column in the FIAT exposure csv will be filled by {svi_file.as_posix()}."
                )
            exposure_csv = exposure_csv.merge(
                buildings_joined, on=_FIAT_COLUMNS.object_id, how="left"
            )
            self.fiat_model.exposure.exposure_db = exposure_csv

            # Save the spatial file for future use
            svi_path = self.static_path / "templates" / "fiat" / "svi" / "svi.gpkg"
            svi_path.parent.mkdir(parents=True, exist_ok=True)
            svi.to_file(svi_path)
            self.logger.info(
                f"An SVI map can be shown in FloodAdapt GUI using '{self.config.svi.field_name}' column from {svi_file.as_posix()}"
            )

            return SVIModel(
                geom=Path(svi_path.relative_to(self.static_path)).as_posix(),
                field_name="SVI",
            )
        elif "SVI" in self.fiat_model.exposure.exposure_db.columns:
            self.logger.info(
                "'SVI' column present in the FIAT exposure csv. Vulnerability type infometrics can be produced."
            )
            add_attrs = self.fiat_model.spatial_joins["additional_attributes"]
            if "SVI" not in [attr["name"] for attr in add_attrs]:
                self.logger.warning(
                    "No SVI map found to display in the FloodAdapt GUI!"
                )

            ind = [attr["name"] for attr in add_attrs].index("SVI")
            svi = add_attrs[ind]
            svi_path = self.static_path / "templates" / "fiat" / svi["file"]
            self.logger.info(
                f"An SVI map can be shown in FloodAdapt GUI using '{svi['field_name']}' column from {svi['file']}"
            )
            # Save site attributes
            return SVIModel(
                geom=Path(svi_path.relative_to(self.static_path)).as_posix(),
                field_name=svi["field_name"],
            )

        else:
            self.logger.warning(
                "'SVI' column not present in the FIAT exposure csv. Vulnerability type infometrics cannot be produced."
            )
            return None

    ### SFINCS ###
    def create_sfincs_config(self) -> SfincsModel:
        # call these functions before others to make sure water level references are updated
        config = self.create_sfincs_model_config()
        tide_gauge = self.create_tide_gauge()

        sfincs = SfincsModel(
            config=config,
            water_level=self.water_level_references,
            slr_scenarios=self.create_slr(),
            dem=self.create_dem_model(),
            scs=self.create_scs_model(),
            cyclone_track_database=self.create_cyclone_track_database(),
            tide_gauge=tide_gauge,
            river=self.create_rivers(),
            obs_point=self.create_observation_points(),
        )

        return sfincs

    def create_cyclone_track_database(self) -> Optional[CycloneTrackDatabaseModel]:
        if not self.config.cyclones or not self.config.sfincs_offshore:
            self.logger.warning("No cyclones will be available in the database.")
            return None

        if self.config.cyclone_basin:
            basin = self.config.cyclone_basin
        else:
            basin = "ALL"

        name = f"IBTrACS.{basin.value}.v04r01.nc"
        url = f"https://www.ncei.noaa.gov/data/international-best-track-archive-for-climate-stewardship-ibtracs/v04r01/access/netcdf/{name}"
        self.logger.info(f"Downloading cyclone track database from {url}")
        fn = Path(self.root) / "static" / "cyclone_track_database" / name
        fn.parent.mkdir(parents=True, exist_ok=True)

        try:
            urlretrieve(url, fn)
        except Exception:
            raise RuntimeError(f"Could not retrieve cyclone track database from {url}")

        return CycloneTrackDatabaseModel(file=name)

    def create_scs_model(self) -> Optional[SCSModel]:
        if self.config.scs is None:
            return None
        scs_file = self._check_exists_and_absolute(self.config.scs.file)
        db_scs_file = self.static_path / "scs" / scs_file.name
        db_scs_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(scs_file, db_scs_file)

        return SCSModel(file=scs_file.name, type=self.config.scs.type)

    def create_dem_model(self) -> DemModel:
        if self.config.dem:
            subgrid_sfincs = Path(self.config.dem.filename)
        else:
            self.logger.warning(
                "No subgrid depth geotiff file provided in the config file. Using the one from the SFINCS model."
            )
            subgrid_sfincs = (
                Path(self.sfincs_overland_model.root) / "subgrid" / "dep_subgrid.tif"
            )

        dem_file = self._check_exists_and_absolute(subgrid_sfincs)
        fa_subgrid_path = self.static_path / "dem" / dem_file.name
        fa_subgrid_path.parent.mkdir(parents=True, exist_ok=True)

        # Check tiles
        tiles_sfincs = Path(self.sfincs_overland_model.root) / "tiles"
        fa_tiles_path = self.static_path / "dem" / "tiles"
        if tiles_sfincs.exists():
            shutil.move(tiles_sfincs, fa_tiles_path)
            if (fa_tiles_path / "index").exists():
                os.rename(fa_tiles_path / "index", fa_tiles_path / "indices")
            self.logger.info(
                "Tiles were already available in the SFINCS model and will directly be used in FloodAdapt."
            )
        else:
            # Make tiles
            fa_tiles_path.mkdir(parents=True)
            self.sfincs_overland_model.setup_tiles(
                path=fa_tiles_path,
                datasets_dep=[{"elevtn": dem_file}],
                zoom_range=[0, 13],
                fmt="png",
            )
            self.logger.info(
                f"Tiles were created using the {subgrid_sfincs.as_posix()} as the elevation map."
            )

        shutil.copy2(dem_file, fa_subgrid_path)
        self._dem_path = fa_subgrid_path
        return DemModel(
            filename=fa_subgrid_path.name, units=us.UnitTypesLength.meters
        )  # always in meters

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

    def create_observation_points(self) -> list[ObsPointModel]:
        if self.config.obs_point is None:
            return []

        self.logger.info("Observation points were provided in the config file.")
        return self.config.obs_point

    def create_rivers(self) -> list[RiverModel]:
        src_file = Path(self.sfincs_overland_model.root) / "sfincs.src"
        if not src_file.exists():
            self.logger.warning("No rivers found in the SFINCS model.")
            return []

        df = pd.read_csv(src_file, delim_whitespace=True, header=None, names=["x", "y"])
        river_locs = gpd.GeoDataFrame(
            df,
            geometry=gpd.points_from_xy(df.x, df.y),
            crs=self.sfincs_overland_model.crs,
        )
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
                self.logger.warning(
                    f"No river discharge conditions were found in the SFINCS model for river {idx}. A default value of 0 will be used."
                )

            river = RiverModel(
                name=f"river_{idx}",
                x_coordinate=row.x,
                y_coordinate=row.y,
                mean_discharge=us.UnitfulDischarge(
                    value=discharge, units=self.unit_system.default_discharge_units
                ),
            )
            rivers.append(river)

        self.logger.info(
            f"{len(river_locs)} river(s) were identified from the SFINCS model and will be available in FloodAdapt for discharge input."
        )

        return rivers

    def create_tide_gauge(self) -> Optional[TideGauge]:
        if self.config.tide_gauge is None:
            self.logger.warning(
                "Tide gauge information not provided. Historical events will not have an option to use gauged data in FloodAdapt!"
            )
            self.logger.warning(
                "No water level references were found. It is assumed that MSL is equal to the datum used in the SFINCS overland model. You can provide these values with the tide_gauge.ref attribute in the site.toml."
            )
            return None

        if self.config.tide_gauge.source == TideGaugeSource.file:
            if self.config.tide_gauge.file is None:
                raise ValueError(
                    "Tide gauge file needs to be provided when 'file' is selected as the source."
                )
            if self.config.tide_gauge.ref is None:
                self.logger.warning(
                    "Tide gauge reference not provided. MSL is assumed as the reference of the water levels in the file."
                )
                self.config.tide_gauge.ref = "MSL"

            tide_gauge_file = self._check_exists_and_absolute(
                self.config.tide_gauge.file
            )
            db_file_path = Path(self.static_path / "tide_gauges") / tide_gauge_file.name

            db_file_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(self.config.tide_gauge.file, db_file_path)

            rel_db_path = Path(db_file_path.relative_to(self.static_path))
            self.logger.warning(
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

            self.water_level_references.reference = (
                ref  # update the water level reference
            )

            if self.config.tide_gauge.id is None:
                station_id = self._get_closest_station()
                self.logger.info(
                    "The closest NOAA tide gauge station to the site will be searched."
                )
            else:
                station_id = self.config.tide_gauge.id
                self.logger.info(
                    f"The NOAA tide gauge station with the provided ID {station_id} will be used."
                )
            station = self._get_station_metadata(station_id=station_id, ref=ref)
            if station is not None:
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

                local_datum = DatumModel(
                    name=station["datum_name"],
                    height=us.UnitfulLength(
                        value=station["datum"], units=station["units"]
                    ).transform(self.unit_system.default_length_units),
                )
                self.water_level_references.datums.append(local_datum)

                msl = DatumModel(
                    name="MSL",
                    height=us.UnitfulLength(
                        value=station["msl"], units=station["units"]
                    ).transform(self.unit_system.default_length_units),
                )
                #  Check if MSL is already there and if yes replace it
                existing_msl = next(
                    (
                        datum
                        for datum in self.water_level_references.datums
                        if datum.name == "MSL"
                    ),
                    None,
                )
                if existing_msl:
                    self.water_level_references.datums.remove(existing_msl)
                self.water_level_references.datums.append(msl)

                for name in ["MLLW", "MHHW"]:
                    height = us.UnitfulLength(
                        value=station[name.lower()], units=station["units"]
                    ).transform(self.unit_system.default_length_units)

                    wl_info = DatumModel(
                        name=name,
                        height=height,
                    )
                    self.water_level_references.datums.append(wl_info)
            return tide_gauge
        else:
            self.logger.warning(
                f"Tide gauge source not recognized: {self.config.tide_gauge.source}. Historical events will not have an option to use gauged data in FloodAdapt!"
            )
            return None

    def create_offshore_model(self) -> Optional[FloodModel]:
        if self.sfincs_offshore_model is None:
            return None
        # Connect boundary points of overland to output points of offshore
        fn = Path(self.sfincs_overland_model.root) / "sfincs.bnd"
        bnd = pd.read_csv(fn, sep=" ", lineterminator="\n", header=None)
        bnd = bnd.rename(columns={0: "x", 1: "y"})
        bnd_geo = gpd.GeoDataFrame(
            bnd,
            geometry=gpd.points_from_xy(bnd.x, bnd.y),
            crs=self.sfincs_overland_model.config["epsg"],
        )
        obs_geo = bnd_geo.to_crs(4326)
        obs_geo["x"] = obs_geo.geometry.x
        obs_geo["y"] = obs_geo.geometry.y
        del obs_geo["geometry"]
        obs_geo["name"] = [f"bnd_pt{num:02d}" for num in range(1, len(obs_geo) + 1)]
        fn_off = Path(self.sfincs_offshore_model.root) / "sfincs.obs"
        obs_geo.to_csv(
            fn_off,
            sep="\t",
            index=False,
            header=False,
        )
        self.logger.info(
            "Output points of the offshore SFINCS model were reconfigured to the boundary points of the overland SFINCS model."
        )

        return FloodModel(
            name="offshore",
            reference=self.config.sfincs_offshore.reference,
            vertical_offset=self.config.sfincs_offshore.vertical_offset,
        )

    def create_overland_model(self) -> FloodModel:
        return FloodModel(
            name="overland",
            reference=self.config.sfincs_overland.reference,
        )

    ### SITE ###
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

        config = Site(
            name=self.config.name,
            description=description,
            lat=lat,
            lon=lon,
            fiat=fiat,
            gui=gui,
            sfincs=sfincs,
            standard_objects=std_objs,
        )
        return config

    def read_location(self) -> tuple[float, float]:
        # Get center of area of interest
        if not self.fiat_model.region.empty:
            center = self.fiat_model.region.dissolve().centroid.to_crs(4326)[0]
        else:
            center = (
                self.fiat_model.exposure.exposure_geoms[self._get_fiat_building_index()]
                .dissolve()
                .centroid.to_crs(4326)[0]
            )
        return center.x, center.y

    def create_gui_config(self) -> GuiModel:
        gui = GuiModel(
            units=self.unit_system,
            plotting=self.create_hazard_plotting_config(),
            output_layers=self.create_output_layers_config(),
            visualization_layers=self.create_visualization_layers(),
        )

        return gui

    def create_default_units(self) -> GuiUnitModel:
        if self.config.unit_system == UnitSystems.imperial:
            return GuiUnitModel.imperial()
        elif self.config.unit_system == UnitSystems.metric:
            return GuiUnitModel.metric()
        else:
            raise ValueError(
                f"Unit system {self.config.unit_system} not recognized. Please choose 'imperial' or 'metric'."
            )

    def create_visualization_layers(self) -> VisualizationLayers:
        visualization_layers = VisualizationLayers()
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

        output_layers = OutputLayers(
            floodmap=FloodMapLayer(
                bins=[0.2 * fd_max, 0.6 * fd_max, fd_max],
                colors=["#D7ECFB", "#8ABDDD", "#1C73A4", "#081D58"],
                zbmax=-9999,
                depth_min=0.0,
            ),
            aggregation_dmg=AggregationDmgLayer(
                bins=[0.00001, 0.1 * ad_max, 0.25 * ad_max, 0.5 * ad_max, ad_max],
                colors=[
                    "#FFFFFF",
                    "#FEE9CE",
                    "#FDBB84",
                    "#FC844E",
                    "#E03720",
                    "#860000",
                ],
            ),
            footprints_dmg=FootprintsDmgLayer(
                bins=[0.00001, 0.06 * ftd_max, 0.2 * ftd_max, 0.4 * ftd_max, ftd_max],
                colors=[
                    "#FFFFFF",
                    "#FEE9CE",
                    "#FDBB84",
                    "#FC844E",
                    "#E03720",
                    "#860000",
                ],
            ),
            benefits=benefits_layer,
        )
        return output_layers

    def create_hazard_plotting_config(self) -> PlottingModel:
        datum_names = [datum.name for datum in self.water_level_references.datums]
        if "MHHW" in datum_names:
            amplitude = (
                self.water_level_references.get_datum("MHHW").height
                - self.water_level_references.get_datum("MSL").height
            )
            self.logger.info(
                f"The default tidal amplitude in the GUI will be {amplitude.transform(self.unit_system.default_length_units)}, calculated as the difference between MHHW and MSL from the tide gauge data."
            )
        else:
            amplitude = us.UnitfulLength(
                value=0.0, units=self.unit_system.default_length_units
            )
            self.logger.warning(
                "The default tidal amplitude in the GUI will be 0.0, since no tide-gauge water levels are available. You can change this in the site.toml with the 'gui.tide_harmonic_amplitude' attribute."
            )

        ref = "MSL"
        if ref not in datum_names:
            self.logger.warning(
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

    def create_infometrics(self):
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
            shutil.copy2(file, path_im)

        self._create_optional_infometrics(templates_path, path_im)

        files = list(path_im.glob("*metrics_config*.toml"))
        # Update aggregation areas in metrics config
        for file in files:
            file = path_im.joinpath(file)
            with open(file, "rb") as f:
                attrs = tomli.load(f)

            # add aggration levels
            if self._aggregation_areas is None:
                self._aggregation_areas = self.create_aggregation_areas()
            attrs["aggregateBy"] = [aggr.name for aggr in self._aggregation_areas]

            # take out road metrics if needed
            if not self._has_roads:
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
                        "$", self.read_damage_unit()
                    )

            # replace the SVI threshold if needed
            if self.config.svi:
                for i, query in enumerate(attrs["queries"]):
                    query["filter"] = query["filter"].replace(
                        "SVI_threshold", str(self.config.svi.threshold)
                    )

            with open(file, "wb") as f:
                tomli_w.dump(attrs, f)

    def _create_optional_infometrics(self, templates_path: Path, path_im: Path):
        # If infographics are going to be created in FA, get template metric configurations
        if not self.config.infographics:
            return

        # Check what type of infographics should be used
        if self.config.unit_system == UnitSystems.imperial:
            metrics_folder_name = "US_NSI"
            self.logger.info(
                "Default NSI infometrics and infographics will be created."
            )
        elif self.config.unit_system == UnitSystems.metric:
            metrics_folder_name = "OSM"
            self.logger.info(
                "Default OSM infometrics and infographics will be created."
            )
        else:
            raise ValueError(
                f"Unit system {self.config.unit_system} is not recognized. Please choose 'imperial' or 'metric'."
            )

        if self.config.svi is not None:
            svi_folder_name = "with_SVI"
        else:
            svi_folder_name = "without_SVI"

        # Copy metrics config for infographics
        path_0 = templates_path.joinpath(
            "infometrics", metrics_folder_name, svi_folder_name
        )
        for file in path_0.glob("*.toml"):
            shutil.copy2(file, path_im)

        # Copy additional risk config
        file = templates_path.joinpath(
            "infometrics",
            metrics_folder_name,
            "metrics_additional_risk_configs.toml",
        )
        shutil.copy2(file, path_im)

        # Copy infographics config
        path_ig_temp = templates_path.joinpath("infographics", metrics_folder_name)
        path_ig = self.root.joinpath("static", "templates", "infographics")
        path_ig.mkdir()
        files_ig = ["styles.css", "config_charts.toml"]

        if self.config.svi is not None:
            files_ig.append("config_risk_charts.toml")
            files_ig.append("config_people.toml")

        if self._has_roads:
            files_ig.append("config_roads.toml")

        for file in files_ig:
            shutil.copy2(path_ig_temp.joinpath(file), path_ig.joinpath(file))

        # Copy images
        path_0 = templates_path.joinpath("infographics", "images")
        path_1 = self.root.joinpath("static", "templates", "infographics", "images")
        shutil.copytree(path_0, path_1)

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

    def add_probabilistic_set(self):
        # Copy prob set if given
        if self.config.probabilistic_set:
            self.logger.info(
                f"Probabilistic event set imported from {self.config.probabilistic_set}"
            )
            prob_event_name = Path(self.config.probabilistic_set).name
            path_db = self.root.joinpath("input", "events", prob_event_name)
            shutil.copytree(self.config.probabilistic_set, path_db)
            self._probabilistic_set_name = prob_event_name
        else:
            self.logger.warning(
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
        self.logger.info("Preparing the database folder structure.")
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
        buildings = self.fiat_model.exposure.exposure_geoms[
            self._get_fiat_building_index()
        ]
        exposure_csv = self.fiat_model.exposure.exposure_db
        if "BF_FID" in exposure_csv.columns:
            self.logger.warning(
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
        self.fiat_model.exposure.exposure_db = exposure_csv

        # Save site attributes
        buildings_path = geo_path.relative_to(self.static_path)
        self.logger.info(
            f"Building footprints saved at {(self.static_path / buildings_path).resolve().as_posix()}"
        )

        return buildings_path

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
        sfincs_extend = self.sfincs_overland_model.region
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
        self.fiat_model.exposure.exposure_db = gdf.reset_index(drop=True)

        # Clip the building footprints
        fieldname = "BF_FID"
        if clip_footprints and not self.fiat_model.building_footprint.empty:
            # Get buildings after filtering and their footprint id
            self.fiat_model.building_footprint = self.fiat_model.building_footprint[
                self.fiat_model.building_footprint[fieldname].isin(
                    gdf_buildings[fieldname]
                )
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

    def _get_fiat_building_index(self) -> int:
        return self.fiat_model.exposure.geom_names.index(
            self.config.fiat_buildings_name
        )

    def _get_fiat_road_index(self) -> int:
        return self.fiat_model.exposure.geom_names.index(self.config.fiat_roads_name)

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
        self.logger.info(
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
                self.logger.warning(
                    f"This distance is larger than the 'max_distance' value of {self.config.tide_gauge.max_distance.value} {units_new} provided in the config file. The station cannot be used."
                )
                return None

        # get station id
        station_id = closest_station["id"].item()

        return station_id

    def _get_station_metadata(self, station_id: str, ref: str = "MLLW"):
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

        self.logger.info(
            f"The tide gauge station '{station_metadata['name']}' from {self.config.tide_gauge.source} will be used to download nearshore historical water level time-series."
        )

        self.logger.info(
            f"The station metadata will be used to fill in the water_level attribute in the site.toml. The reference level will be {ref}."
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
        with open(
            templates_path.joinpath("output_layers", "bin_colors.toml"), "rb"
        ) as f:
            bin_colors = tomli.load(f)
        return bin_colors


if __name__ == "__main__":
    while True:
        config_path = Path(
            input(
                "Please provide the path to the database creation configuration toml: \n"
            )
        )
        try:
            config = ConfigModel.read(config_path)
            dbs = DatabaseBuilder(config)
            dbs.build()
        except Exception as e:
            print(e)
        quit = input("Do you want to quit? (y/n)")
        if quit == "y":
            exit()
