from pathlib import Path

import tomli_w
from pydantic import BaseModel

from flood_adapt import unit_system as us
from flood_adapt.misc.config import Settings
from flood_adapt.object_model.hazard.interface.forcing import Scstype
from flood_adapt.object_model.hazard.interface.tide_gauge import (
    TideGaugeModel,
    TideGaugeSource,
)
from flood_adapt.object_model.interface.config.fiat import (
    AggregationModel,
    BenefitsModel,
    EquityModel,
    FiatConfigModel,
    FiatModel,
    RiskModel,
)
from flood_adapt.object_model.interface.config.gui import (
    GuiModel,
    GuiUnitModel,
    MapboxLayersModel,
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
    SlrScenariosModel,
    WaterlevelReferenceModel,
)
from flood_adapt.object_model.interface.config.site import SiteConfigModel, SiteModel

DATA_DIR = Path(__file__).parent


def update_database_static(database_path: Path):
    """Create the config in the database.

    Possibly update the static data in the database.
    """
    config_dir = database_path / "static" / "config"
    config_dir.mkdir(parents=True, exist_ok=True)

    write_fiat_config(config_dir)
    write_gui_config(config_dir)

    write_sfincs_config(config_dir)
    write_sfincs_without_river_config(config_dir)

    # site = get_site_config()
    # site_no_river = get_site_without_river_config()

    # update_static_data(database_path)


def _write_config(config: BaseModel, file_path: Path):
    with open(file_path, "wb") as f:
        tomli_w.dump(config.model_dump(), f)


def write_fiat_config(config_dir: Path) -> FiatModel:
    aggregations = [
        AggregationModel(
            name="aggr_lvl_1",
            file="templates/fiat/aggregation_areas/aggr_lvl_1.geojson",
            field_name="name",
        ),
        AggregationModel(
            name="aggr_lvl_2",
            file="templates/fiat/aggregation_areas/aggr_lvl_2.geojson",
            field_name="name",
            equity=EquityModel(
                census_data="templates/fiat/equity/census_data_aggr_lvl_2.csv",
                percapitaincome_label="PerCapitaIncome",
                totalpopulation_label="TotalPopulation",
            ),
        ),
    ]

    config = FiatConfigModel(
        exposure_crs="EPSG:4326",
        floodmap_type=FloodmapType.water_level,
        non_building_names=["roads"],
        damage_unit="$",
        building_footprints="templates/fiat/footprints/Buildings.shp",
        roads_file_name="roads.gpkg",
        new_development_file_name="new_dev.gpkg",
        save_simulation=True,
        infographics=True,
        aggregation=aggregations,
    )

    fiat = FiatModel(
        risk=RiskModel(return_periods=[1, 2, 5, 10, 25, 50, 100]),
        config=config,
        benefits=BenefitsModel(
            current_year=2023,
            current_projection="current",
            baseline_strategy="no_measures",
            event_set="test_set",
        ),
    )
    _write_config(fiat, config_dir / "fiat.toml")

    return fiat


def write_gui_config(config_dir: Path):
    units = GuiUnitModel(
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
        svi_colors=["#FFFFFF", "#FEE9CE", "#FDBB84", "#FC844E", "#E03720", "#860000"],
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

    gui = GuiModel(
        units=units,
        default_tide_harmonic_amplitude=us.UnitfulLength(
            value=3.0, units=us.UnitTypesLength.feet
        ),
        mapbox_layers=mapbox_layers,
        visualization_layers=visualization_layers,
    )

    _write_config(gui, config_dir / "gui.toml")


def _get_sfincs_config() -> SfincsModel:
    waterlevel_reference = WaterlevelReferenceModel(
        reference="MLLW",
        datums={
            "MLLW": DatumModel(
                name="MLLW",
                height=us.UnitfulLength(value=0.0, units=us.UnitTypesLength.meters),
            ),
            "MSL": DatumModel(
                name="MSL",
                height=us.UnitfulLength(value=0.89, units=us.UnitTypesLength.meters),
            ),
            "NAVD88": DatumModel(
                name="NAVD88",
                height=us.UnitfulLength(value=0.957, units=us.UnitTypesLength.meters),
            ),
            "MHHW": DatumModel(
                name="MHHW",
                height=us.UnitfulLength(value=1.757, units=us.UnitTypesLength.meters),
            ),
        },
    )

    config = SfincsConfigModel(
        csname="WGS 84 / UTM zone 17N",
        cstype=Cstype.projected,
        offshore_model=FloodModel(
            name="offshore",
            reference="MSL",
        ),
        overland_model=FloodModel(
            name="overland",
            reference="NAVD88",
        ),
        floodmap_units=us.UnitTypesLength.feet,
        save_simulation=False,
    )

    tide_gauge = TideGaugeModel(
        name=8665530,
        reference="MSL",
        source=TideGaugeSource.noaa_coops,
        description="Charleston Cooper River Entrance",
        ID=8665530,
        lat=32.78,
        lon=-79.9233,
    )

    rivers = [
        RiverModel(
            name="cooper",
            x_coordinate=595546.3,
            y_coordinate=3675590.6,
            mean_discharge=us.UnitfulDischarge(
                value=5000.0, units=us.UnitTypesDischarge.cfs
            ),
        )
    ]

    obs_points = [
        ObsPointModel(
            name="ashley_river",
            description="Ashley River - James Island Expy",
            lat=32.7765,
            lon=-79.9543,
        ),
        ObsPointModel(
            name=8665530,
            description="Charleston Cooper River Entrance",
            ID=8665530,
            lat=32.78,
            lon=-79.9233,
        ),
    ]

    sfincs = SfincsModel(
        config=config,
        water_level=waterlevel_reference,
        slr=SlrModel(
            scenarios=SlrScenariosModel(relative_to_year=2020, file="slr/slr.csv"),
        ),
        dem=DemModel(filename="charleston_14m.tif", units=us.UnitTypesLength.meters),
        scs=SCSModel(file="scs_rainfall.csv", type=Scstype.type3),
        cyclone_track_database=CycloneTrackDatabaseModel(file="IBTrACS.NA.v04r00.nc"),
        tide_gauge=tide_gauge,
        river=rivers,
        obs_point=obs_points,
    )
    return sfincs


def write_sfincs_config(config_dir: Path):
    sfincs = _get_sfincs_config()
    _write_config(sfincs, config_dir / "sfincs.toml")


def write_sfincs_without_river_config(config_dir: Path):
    sfincs = _get_sfincs_config()
    sfincs.river = None
    _write_config(sfincs, config_dir / "sfincs.toml")


def write_site_config():
    SiteConfigModel(
        name="Charleston",
        description="Charleston, SC",
        lat=32.7765,
        lon=-79.9311,
        components={
            "sfincs": {"config_path": "sfincs.toml"},
            "gui": {"config_path": "gui.toml"},
            "fiat": {"config_path": "fiat.toml"},
        },
    )

    SiteModel()


def get_site_without_river_config():
    raise NotImplementedError


def update_static_data():
    raise NotImplementedError


if __name__ == "__main__":
    settings = Settings(
        DATABASE_ROOT=Path(__file__).parents[3] / "Database",
        DATABASE_NAME="charleston_test",
    )

    update_database_static(settings.database_path)
