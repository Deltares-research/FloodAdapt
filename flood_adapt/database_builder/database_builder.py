import datetime
import os
import shutil
from enum import Enum
from pathlib import Path
from typing import Optional, Union
from urllib.request import urlretrieve

import geopandas as gpd
import numpy as np
import pandas as pd
import tomli
from hydromt_fiat import FiatModel as HydromtFiatModel
from hydromt_fiat.data_apis.open_street_maps import get_buildings_from_osm
from hydromt_sfincs import SfincsModel as HydromtSfincsModel
from pydantic import BaseModel, Field
from shapely import Polygon

from flood_adapt import FloodAdaptLogging
from flood_adapt import unit_system as us
from flood_adapt.adapter.fiat_adapter import _FIAT_COLUMNS
from flood_adapt.misc.config import Settings
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
    SlrModel,
    WaterlevelReferenceModel,
)
from flood_adapt.object_model.interface.config.site import Site, SiteModel


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
    ref: DatumModel
    description: str = ""
    id: Optional[int] = None
    file: Optional[str] = None
    location: Optional[Point] = None
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

    # General
    name: str = Field(..., min_length=1, pattern='^[^<>:"/\\\\|?* ]*$')
    description: str = ""
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
    svi: Optional[SviModel] = None
    road_width: Optional[float] = 5
    risk: list[int] = Field(default_factory=list)

    # SFINCS
    sfincs: str
    sfincs_offshore: Optional[str] = None
    main_reference: DatumModel = DatumModel(
        name="MSL", height=us.UnitfulLength(value=0, units=us.UnitTypesLength.meters)
    )
    sfincs_overland_reference: Optional[DatumModel] = None
    sfincs_offshore_reference: Optional[DatumModel] = None

    slr: Optional[SlrModel] = None
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
        return ConfigModel.model_validate(toml)


class DatabaseBuilder:
    logger = FloodAdaptLogging.getLogger("DatabaseBuilder")

    def __init__(self, config_path: Path):
        self.root = config_path.parent
        self.config = ConfigModel.read(config_path)

        # Read the templates
        self.fiat_model = self.read_template_fiat_model()
        self.sfincs_overland_model = self.read_template_sfincs_overland_model()
        self.sfincs_offshore_model = self.read_template_sfincs_offshore_model()

        # Read info that needs to be used to create other models
        self.unit_system = self.create_default_units()

        # Read info that needs to be updated with other model info
        self.water_level_references = self.create_water_level_references()

        self.build()

    @property
    def static_path(self) -> Path:
        return self.root / "static"

    def build(self):
        self.make_folder_structure()
        site_model = self.create_site_config()

        site = Site(site_config=site_model)
        site.save(self.static_path / "config" / "site.toml")

    ### TEMPLATE READERS ###
    def read_template_fiat_model(self) -> HydromtFiatModel:
        fiat_template = self._check_exists_and_make_absolute(self.config.fiat)

        fiat_model = HydromtFiatModel(root=str(fiat_template), mode="r+")
        fiat_model.read()
        return fiat_model

    def read_template_sfincs_overland_model(self) -> HydromtSfincsModel:
        sfincs_template = self._check_exists_and_make_absolute(self.config.sfincs)
        model = HydromtSfincsModel(root=str(sfincs_template), mode="r+")
        model.read()

        if model.crs is None:
            raise ValueError("CRS is not defined in the SFINCS model.")

        return model

    def read_template_sfincs_offshore_model(self) -> Optional[HydromtSfincsModel]:
        if self.config.sfincs_offshore is None:
            return None
        return HydromtSfincsModel(root=self.config.sfincs_offshore, mode="r+")

    ### FIAT ###
    def create_fiat_model(self) -> FiatModel:
        fiat = FiatModel(
            risk=self.create_risk_model(),
            config=self.create_fiat_config(),
            benefits=self.create_benefit_config(),
        )
        return fiat

    def create_risk_model(self) -> RiskModel:
        return RiskModel(return_periods=self.config.risk)

    def create_benefit_config(self) -> BenefitsModel:
        return BenefitsModel(
            current_year=datetime.datetime.now().year,
            current_projection="current",
            baseline_strategy="no_measures",
            event_set="test_set",
        )

    def create_fiat_config(self) -> FiatConfigModel:
        shutil.copytree(self.fiat_model.root, self.static_path / "templates" / "fiat")
        self.fiat_model = HydromtFiatModel(
            str(self.static_path / "templates" / "fiat"), mode="w+"
        )

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

        roads_gpkg = self.create_roads()
        non_building_names = []
        if roads_gpkg is not None:
            non_building_names.append("road")

        footprints = self.create_footprints()
        if footprints is not None:
            footprints = footprints.as_posix()

        config = FiatConfigModel(
            exposure_crs=self.fiat_model.exposure.crs,
            floodmap_type=self.read_floodmap_type(),
            bfe=self.create_bfe(),
            non_building_names=non_building_names,
            damage_unit=self.read_damage_unit(),
            building_footprints=footprints,
            roads_file_name=roads_gpkg,
            new_development_file_name=self.create_new_developments(),  # TODO
            save_simulation=True,  # TODO
            infographics=True,  # TODO
            aggregation=self.create_aggregation_areas(),
            svi=self.create_svi(),
        )

        return config

    def read_damage_unit(self) -> str:
        if self.fiat_model.exposure is None:
            raise ValueError("No exposure data found in the FIAT model.")

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

        roads_ind = self.fiat_model.exposure.geom_names.index(
            self.config.fiat_roads_name
        )
        roads = self.fiat_model.exposure.exposure_geoms[roads_ind]
        roads_geom_filename = self.fiat_model.config["exposure"]["geom"][
            f"file{roads_ind+1}"
        ]
        roads_path = Path(self.fiat_model.root) / roads_geom_filename

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

        return f"{self.config.fiat_roads_name}.gpkg"

    def create_new_developments(self) -> Optional[str]:
        return None  # TODO

    def create_footprints(self) -> Optional[Path]:
        if isinstance(self.config.building_footprints, SpatialJoinModel):
            building_footprints_file = self._check_exists_and_make_absolute(
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
            return Path(path).relative_to(self.static_path)

        # First check if it is spatially joined and/or exists already
        check_col = "BF_FID" in self.fiat_model.exposure.exposure_db.columns
        add_attrs = self.fiat_model.spatial_joins["additional_attributes"]
        fiat_path = self.static_path / "templates" / "fiat"

        if add_attrs and "BF_FID" in [attr["name"] for attr in add_attrs]:
            ind = [attr["name"] for attr in add_attrs].index("BF_FID")
            footprints = add_attrs[ind]
            footprints_path = fiat_path / footprints["file"]

            if footprints_path.exists():
                if not check_col:
                    self.logger.error(
                        f"Exposure csv is missing the 'BF_FID' column to connect to the footprints located at {footprints_path}."
                    )
                    raise NotImplementedError

                self.logger.info(
                    f"Using the building footprints located at {footprints_path}."
                )
                return footprints_path.relative_to(self.static_path)

        # Then check if geometries are already footprints
        if isinstance(
            self.fiat_model.exposure.exposure_geoms[
                self._get_fiat_building_index()
            ].geometry.iloc[0],
            Polygon,
        ):
            _footprints_found = True
            # TODO @panos what to return here?

        # Other methods
        if self.config.building_footprints == "OSM":
            self.logger.info(
                "Building footprint data will be downloaded from Open Street Maps."
            )
            region_path = Path(self.fiat_model.root) / "geoms" / "region.geojson"
            if not region_path.exists():
                self.logger.error("No region file found in the FIAT model.")
            region = gpd.read_file(region_path).to_crs(4326)
            polygon = Polygon(region.boundary.to_numpy()[0])
            footprints = get_buildings_from_osm(polygon)
            footprints["BF_FID"] = np.arange(1, len(footprints) + 1)
            footprints = footprints[["BF_FID", "geometry"]]
            path = self._join_building_footprints(footprints, "BF_FID")
            return Path(path).relative_to(self.static_path)

        # Getting here means no footprints were found
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
        bfe_file = self._check_exists_and_make_absolute(self.config.bfe.file)

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
        # If there are no aggregation areas make a schematic one from the region file
        # TODO make aggregation areas not mandatory
        # TODO can we use Hydromt-FIAT
        aggregation_areas = []

        # read the aggregation areas from the config
        if self.config.aggregation_areas:
            build_ind = self._get_fiat_building_index()
            for aggr in self.config.aggregation_areas:
                # Add column in FIAT
                aggr_name = Path(aggr.file).stem
                exposure_csv = self.fiat_model.exposure.exposure_db
                buildings_joined, aggr_areas = self.spatial_join(
                    self.fiat_model.exposure.exposure_geoms[build_ind],
                    self._check_exists_and_make_absolute(aggr.file),
                    aggr.field_name,
                    rename=_FIAT_COLUMNS.aggregation_label.format(name=aggr_name),
                )
                aggr_path = (
                    Path(self.fiat_model.root)
                    / "exposure"
                    / "aggregation_areas"
                    / f"{Path(aggr.file).stem}.gpkg"
                )
                aggr_areas.to_file(aggr_path)
                exposure_csv = exposure_csv.merge(
                    buildings_joined, on=_FIAT_COLUMNS.object_id, how="left"
                )
                self.fiat_model.exposure.exposure_db = exposure_csv
                aggregation_areas.append(
                    AggregationModel(
                        name=aggr_name,
                        file=aggr_path.relative_to(self.fiat_model.root),
                        field_name=_FIAT_COLUMNS.aggregation_label.format(
                            name=aggr_name
                        ),
                        equity=None,
                    )
                )
            return aggregation_areas

        # Use region file as a mock aggregation area
        if not self.fiat_model.spatial_joins["aggregation_areas"]:
            exposure_csv = self.fiat_model.exposure.exposure_db
            region_path = Path(self.fiat_model.root) / "geoms" / "region.geojson"
            if not region_path.exists():
                msg = "No aggregation areas were available in the FIAT model and no region geometry file is available. FloodAdapt needs at least one!"
                self.logger.error(msg)
                raise ValueError(msg)

            region = gpd.read_file(region_path)
            region = region.explode().reset_index()
            region["aggr_id"] = ["region_" + str(i) for i in np.arange(len(region)) + 1]
            aggregation_path = (
                Path(self.fiat_model.root) / "aggregation_areas" / "region.geojson"
            )
            aggregation_path.parent.mkdir(parents=True, exist_ok=True)
            region.to_file(aggregation_path)
            aggregation_areas.append(
                AggregationModel(
                    name="region",
                    file=str(aggregation_path.relative_to(self.static_path).as_posix()),
                    field_name="aggr_id",
                )
            )

            # Add column in FIAT
            buildings_joined, _ = self.spatial_join(
                self.fiat_model.exposure.exposure_geoms[
                    self._get_fiat_building_index()
                ],
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
            return aggregation_areas

        # read the aggregation areas from the FIAT model
        for aggr_0 in self.fiat_model.spatial_joins["aggregation_areas"]:
            if aggr_0["equity"] is not None:
                equity_config = EquityModel(
                    census_data=str(
                        (
                            self.static_path
                            / "templates"
                            / "fiat"
                            / aggr_0["equity"]["census_data"]
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
                    self.static_path
                    / "templates"
                    / "fiat"
                    / aggr_0["file"].relative_to(self.static_path).as_posix()
                ),
                field_name=aggr_0["field_name"],
                equity=equity_config,
            )
            aggregation_areas.append(aggr)
            self.logger.info(
                f"The aggregation types {[aggr['name'] for aggr in self.fiat_model.spatial_joins['aggregation_areas']]} from the FIAT model are going to be used."
            )
        return aggregation_areas

    def create_svi(self) -> Optional[SVIModel]:
        if self.config.svi:
            svi_file = self._check_exists_and_make_absolute(self.config.svi.file)
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
                geom=str(Path(svi_path.relative_to(self.static_path)).as_posix()),
                field_name="SVI",
            )
        elif "SVI" in self.fiat_model.exposure.exposure_db.columns:
            self.logger.info("'SVI' column present in the FIAT exposure csv.")
            add_attrs = self.fiat_model.spatial_joins["additional_attributes"]
            if "SVI" in [attr["name"] for attr in add_attrs]:
                ind = [attr["name"] for attr in add_attrs].index("SVI")
                svi = add_attrs[ind]
                svi_path = self.static_path / "templates" / "fiat" / svi["file"]
                self.logger.info(
                    f"An SVI map can be shown in FloodAdapt GUI using '{svi['field_name']}' column from {svi['file']}"
                )
                # Save site attributes
                return SVIModel(
                    geom=str(Path(svi_path.relative_to(self.static_path)).as_posix()),
                    field_name=svi["field_name"],
                )
            else:
                self.logger.warning("No SVI map found!")
                return None
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
            slr=self.create_slr(),
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

        name = f"IBTrACS.{basin}.v04r01.nc"
        url = f"https://www.ncei.noaa.gov/data/international-best-track-archive-for-climate-stewardship-ibtracs/v04r01/access/netcdf/{name}"
        self.logger.info(f"Downloading cyclone track database from {url}")
        fn = Path(self.root) / "static" / "cyclone_track_database" / name
        fn.parent.mkdir(parents=True, exist_ok=True)

        try:
            urlretrieve(url, fn)
        except Exception as e:
            print(e)
            self.logger.error(f"Could not retrieve cyclone track database from {url}")
            return None

        return CycloneTrackDatabaseModel(file=name)

    def create_scs_model(self) -> Optional[SCSModel]:
        if self.config.scs is None:
            return None
        scs_file = self._check_exists_and_make_absolute(self.config.scs.file)
        db_scs_file = self.static_path / "scs" / scs_file.name
        db_scs_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(scs_file, db_scs_file)

        return SCSModel(file=scs_file.name, type=self.config.scs.type)

    def create_dem_model(self) -> DemModel:
        # check subgrid
        subgrid_sfincs = (
            Path(self.sfincs_overland_model.root) / "subgrid" / "dep_subgrid.tif"
        )
        if not subgrid_sfincs.exists():
            raise FileNotFoundError(
                f"A subgrid depth geotiff file should be available at {subgrid_sfincs}."
            )
        fa_subgrid_path = self.static_path / "dem" / subgrid_sfincs.name
        fa_subgrid_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(subgrid_sfincs, fa_subgrid_path)

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
                datasets_dep=[{"elevtn": subgrid_sfincs}],
                zoom_range=[0, 13],
                fmt="png",
            )
            self.logger.info(
                f"Tiles were created using the {subgrid_sfincs} as the elevation map."
            )

        return DemModel(
            filename=subgrid_sfincs.name, units=us.UnitTypesLength.meters
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

    def create_slr(self) -> Optional[SlrModel]:
        if self.config.slr is None:
            return None

        self.config.slr.file = str(
            self._check_exists_and_make_absolute(self.config.slr.file)
        )
        slr_path = self.static_path / "slr"
        slr_path.mkdir()
        new_file = slr_path / Path(self.config.slr.file).name
        shutil.copyfile(self.config.slr.file, new_file)

        return SlrModel(
            file=new_file.relative_to(self.static_path).as_posix(),
            relative_to_year=self.config.slr.relative_to_year,
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

            river = RiverModel(
                name=f"river_{idx}",
                x_coordinate=row.x,
                y_coordinate=row.y,
                mean_discharge=us.UnitfulDischarge(
                    value=discharge, units=self.unit_system.default_discharge_units
                ),
            )
            rivers.append(river)

        return rivers

    def create_tide_gauge(self) -> Optional[TideGaugeModel]:
        if self.config.tide_gauge is None:
            self.logger.warning(
                "Tide gauge information not provided. Historical nearshore gauged events will not be available in FloodAdapt!"
            )
            self.logger.warning(
                "No water level references were found. It is assumed that MSL is equal to the datum used in the SFINCS overland model. You can provide these values with the tide_gauge.ref attribute in the site.toml."
            )
            return None

        if self.config.tide_gauge.source == TideGaugeSource.file:
            if self.config.tide_gauge.file is None:
                # TODO Should probably raise an error here since it doesnt make sense to have this source without a file?
                self.logger.warning(
                    "Tide gauge file not provided. Historical nearshore gauged events will not be available in FloodAdapt!"
                )
                return None

            tide_gauge_file = self._check_exists_and_make_absolute(
                self.config.tide_gauge.file
            )
            db_file_path = Path(self.static_path / "tide_gauges") / tide_gauge_file.name

            db_file_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(self.config.tide_gauge.file, db_file_path)

            rel_db_path = Path(db_file_path.relative_to(self.static_path))
            tide_gauge = TideGaugeModel(
                reference=self.config.tide_gauge.ref.name,
                description="observations from file stored in database",
                source=TideGaugeSource.file,
                file=rel_db_path,
                units=us.UnitTypesLength.meters,
            )
            self.water_level_references.datums.append(self.config.tide_gauge.ref)
            return tide_gauge

        elif self.config.tide_gauge.source == TideGaugeSource.noaa_coops:
            if (self.config.tide_gauge.id is None) or (
                self.config.tide_gauge.location is None
            ):
                # TODO Should probably raise an error here since it doesnt make sense to have this source without an ID and location?
                self.logger.warning(
                    "Tide gauge ID and/or location not provided. Historical nearshore gauged events will not be available in FloodAdapt!"
                )
                return None

            tide_gauge = TideGaugeModel(
                name=str(self.config.tide_gauge.id),
                reference=self.config.tide_gauge.ref.name,
                source=TideGaugeSource.noaa_coops,
                description=self.config.tide_gauge.description,
                ID=self.config.tide_gauge.id,
                lat=self.config.tide_gauge.location.lat,
                lon=self.config.tide_gauge.location.lon,
            )
            self.water_level_references.datums.append(self.config.tide_gauge.ref)
            return tide_gauge
        else:
            self.logger.warning(
                f"Tide gauge source not recognized: {self.config.tide_gauge.source}. Historical nearshore gauged events will not be available in FloodAdapt!"
            )
            return None

    def create_water_level_references(self) -> WaterlevelReferenceModel:
        water_level_config = WaterlevelReferenceModel(
            reference=self.config.main_reference.name,
            datums=[self.config.main_reference],
        )

        return water_level_config

    def create_offshore_model(self) -> Optional[FloodModel]:
        if self.sfincs_offshore_model is None:
            return None

        sfincs_offshore_path = self.static_path / "templates" / "offshore"
        shutil.copytree(self.sfincs_offshore_model.root, sfincs_offshore_path)

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
        obs_geo.to_csv(
            sfincs_offshore_path / "sfincs.obs",
            sep="\t",
            index=False,
            header=False,
        )
        self.logger.info(
            "Output points of the offshore SFINCS model were reconfigured to the boundary points of the overland SFINCS model."
        )

        if self.config.sfincs_offshore_reference is None:
            ref = self.config.main_reference
        else:
            ref = self.config.sfincs_offshore_reference
            self.water_level_references.datums.append(ref)

        return FloodModel(
            name="offshore",
            reference=ref.name,
        )

    def create_overland_model(self) -> FloodModel:
        sfincs_overland_path = self.static_path / "templates" / "overland"
        shutil.copytree(self.sfincs_overland_model.root, sfincs_overland_path)

        if self.config.sfincs_overland_reference is None:
            ref = self.config.main_reference
        else:
            ref = self.config.sfincs_overland_reference
            self.water_level_references.datums.append(ref)

        return FloodModel(
            name="overland",
            reference=ref.name,
        )

    ### SITE ###
    def create_site_config(self) -> SiteModel:
        fiat = self.create_fiat_model()
        sfincs = self.create_sfincs_config()
        gui = self.create_gui_config()
        lat, lon = self.read_location()

        config = SiteModel(
            name=self.config.name,
            description=self.config.description,
            lat=lat,
            lon=lon,
            fiat=fiat,
            gui=gui,
            sfincs=sfincs,
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
            mapbox_layers=self.create_mapbox_layers_config(),
            visualization_layers=self.create_visualization_layers(),
        )

        return gui

    def create_default_units(self) -> GuiUnitModel:
        return GuiUnitModel(
            default_length_units=us.UnitTypesLength.feet,
            default_distance_units=us.UnitTypesLength.miles,
            default_area_units=us.UnitTypesArea.sf,
            default_volume_units=us.UnitTypesVolume.cf,
            default_velocity_units=us.UnitTypesVelocity.knots,
            default_direction_units=us.UnitTypesDirection.degrees,
            default_discharge_units=us.UnitTypesDischarge.cfs,
            default_intensity_units=us.UnitTypesIntensity.inch_hr,
            default_cumulative_units=us.UnitTypesLength.inch,
        )

    def create_visualization_layers(self) -> VisualizationLayersModel:
        visualization_layers = VisualizationLayersModel(
            default_bin_number=4,
            default_colors=["#FFFFFF", "#FEE9CE", "#E03720", "#860000"],
            layer_names=[],
            layer_long_names=[],
            layer_paths=[],
            field_names=[],
            bins=[],
            colors=[],
        )

        return visualization_layers

    def create_mapbox_layers_config(self) -> MapboxLayersModel:
        mapbox_layers = MapboxLayersModel(
            flood_map_depth_min=0.328,
            flood_map_zbmax=3.28,
            flood_map_bins=[1, 3, 5],
            flood_map_colors=["#BED2FF", "#B4D79E", "#1F80B8", "#081D58"],
            aggregation_dmg_bins=[0.00001, 1000000, 2500000, 5000000, 10000000],
            aggregation_dmg_colors=[
                "#FFFFFF",
                "#FEE9CE",
                "#FDBB84",
                "#FC844E",
                "#E03720",
                "#860000",
            ],
            footprints_dmg_bins=[0.00001, 10, 20, 40, 60],
            footprints_dmg_colors=[
                "#FFFFFF",
                "#FEE9CE",
                "#FDBB84",
                "#FC844E",
                "#E03720",
                "#860000",
            ],
            svi_bins=[0.05, 0.2, 0.4, 0.6, 0.8],
            svi_colors=[
                "#FFFFFF",
                "#FEE9CE",
                "#FDBB84",
                "#FC844E",
                "#E03720",
                "#860000",
            ],
            benefits_bins=[0, 0.01, 1000000, 10000000, 50000000],
            benefits_colors=[
                "#FF7D7D",
                "#FFFFFF",
                "#DCEDC8",
                "#AED581",
                "#7CB342",
                "#33691E",
            ],
        )

        return mapbox_layers

    def create_hazard_plotting_config(self) -> PlottingModel:
        plotting = PlottingModel(
            synthetic_tide=SyntheticTideModel(
                harmonic_amplitude=us.UnitfulLength(
                    value=3.0, units=us.UnitTypesLength.feet
                ),
                datum="MSL",
            ),
            excluded_datums=["NAVD88"],
        )

        return plotting

    ### HELPER FUNCTIONS ###
    def make_folder_structure(self):
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
        folders = ["templates"]
        for name in folders:
            (self.static_path / name).mkdir()

    def _check_exists_and_make_absolute(self, path: str) -> Path:
        """Check if the path is absolute or relative and return a Path object. Raises an error if the path is not valid."""
        if not Path(path).exists():
            raise FileNotFoundError(f"Path {path} does not exist.")

        if Path(path).is_absolute():
            return Path(path)
        return self.root / path

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
        bf_folder.mkdir()

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

        return geo_path

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
        )

        if road_inds.any():
            # Clip roads
            gdf_roads = gdf[road_inds]
            gdf_roads = self._clip_gdf(gdf_roads, clipped_region, predicate="within")

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

        # Write fiat model
        self.fiat_model.write()

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


if __name__ == "__main__":
    settings = Settings(
        DATABASE_ROOT=Path(__file__).parents[3] / "Database",
        DATABASE_NAME="charleston_test",
    )
