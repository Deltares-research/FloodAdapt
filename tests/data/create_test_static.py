from argparse import ArgumentParser
from pathlib import Path
from typing import Optional

from flood_adapt.config.fiat import (
    FiatConfigModel,
    FiatModel,
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
from flood_adapt.config.hazard import (
    Cstype,
    CycloneTrackDatabaseModel,
    DatumModel,
    DemModel,
    FloodModel,
    ObsPointModel,
    RiverModel,
    SCSModel,
    Scstype,
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
from flood_adapt.config.settings import Settings
from flood_adapt.config.sfincs import (
    SfincsConfigModel,
    SfincsModel,
)
from flood_adapt.config.site import Site, StandardObjectModel
from flood_adapt.objects.forcing import unit_system as us
from flood_adapt.objects.forcing.tide_gauge import (
    TideGauge,
    TideGaugeSource,
)

DATA_DIR = Path(__file__).parent


def update_database_static(database_path: Path):
    """Create the config in the database.

    Possibly update the static data in the database.
    """
    config_dir = database_path / "static" / "config"
    config_dir.mkdir(parents=True, exist_ok=True)

    # default config
    sfincs = create_sfincs_config(database_path=database_path, quadtree=False)
    site = create_site_config(
        database_path=database_path, sfincs=sfincs, quadtree=False
    )
    site.save(config_dir / "site.toml")

    # site without river
    sfincs.river = None
    sfincs.config.overland_model.name = "overland_0_rivers"  # this model has template the .src file deleted, and the sfincs.inp updated accordingly
    no_river = create_site_config(
        database_path=database_path, sfincs=sfincs, quadtree=False
    )
    no_river.save(
        filepath=config_dir / "site_without_river.toml",
        sfincs="sfincs_without_river.toml",
    )

    # quadtree config
    qt_site = create_site_config(database_path=database_path, quadtree=True)
    qt_site.save(
        filepath=config_dir / "site_quadtree.toml",
        sfincs="sfincs_quadtree.toml",
    )


def create_fiat_config() -> FiatModel:
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

    bfe = BFEModel(
        geom="bfe/bfe.geojson",
        table="bfe/bfe.csv",
        field_name="bfe",
    )

    config = FiatConfigModel(
        exposure_crs="EPSG:4326",
        floodmap_type=FloodmapType.water_level,
        bfe=bfe,
        svi=SVIModel(
            geom="templates/fiat/svi/CDC_svi_2020.gpkg",
            field_name="SVI",
        ),
        non_building_names=["road"],
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
    return fiat


def create_gui_config(database_path: Path) -> GuiModel:
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

    output_layers = OutputLayers(
        floodmap=FloodMapLayer(
            bins=[1, 3, 5],
            colors=["#BED2FF", "#B4D79E", "#1F80B8", "#081D58"],
            zbmax=3.28,
            depth_min=0.328,
        ),
        aggregation_dmg=AggregationDmgLayer(
            bins=[0.00001, 1000000, 2500000, 5000000, 10000000],
            colors=["#FFFFFF", "#FEE9CE", "#FDBB84", "#FC844E", "#E03720", "#860000"],
        ),
        footprints_dmg=FootprintsDmgLayer(
            bins=[0.00001, 10, 20, 40, 60],
            colors=["#FFFFFF", "#FEE9CE", "#FDBB84", "#FC844E", "#E03720", "#860000"],
        ),
        benefits=BenefitsLayer(
            bins=[0, 0.01, 1000000, 10000000, 50000000],
            colors=[
                "#FF7D7D",
                "#FFFFFF",
                "#DCEDC8",
                "#AED581",
                "#7CB342",
                "#33691E",
            ],
            threshold=0.0,
        ),
    )

    visualization_layers = VisualizationLayers()
    visualization_layers.add_layer(
        bins=[0, 0.1, 0.2, 0.3, 0.4],
        colors=["#FFFFFF", "#FEE9CE", "#FDBB84", "#FC844E", "#E03720", "#860000"],
        name="svi",
        long_name="Social Vulnerability Index",
        path=str(database_path / "static" / "templates/fiat/svi/CDC_svi_2020.gpkg"),
        field_name="SVI",
        database_path=database_path,
    )

    plotting = PlottingModel(
        synthetic_tide=SyntheticTideModel(
            harmonic_amplitude=us.UnitfulLength(
                value=3.0, units=us.UnitTypesLength.feet
            ),
            datum="MSL",
        ),
        excluded_datums=["NAVD88"],
    )

    gui = GuiModel(
        units=units,
        plotting=plotting,
        output_layers=output_layers,
        visualization_layers=visualization_layers,
    )

    return gui


def create_sfincs_config(database_path: Path, quadtree: bool) -> SfincsModel:
    waterlevel_reference = WaterlevelReferenceModel(
        reference="MLLW",
        datums=[
            DatumModel(
                name="MLLW",
                height=us.UnitfulLength(value=0.0, units=us.UnitTypesLength.meters),
            ),
            DatumModel(
                name="MSL",
                height=us.UnitfulLength(value=0.89, units=us.UnitTypesLength.meters),
            ),
            DatumModel(
                name="NAVD88",
                height=us.UnitfulLength(value=0.957, units=us.UnitTypesLength.meters),
            ),
            DatumModel(
                name="MHHW",
                height=us.UnitfulLength(value=1.757, units=us.UnitTypesLength.meters),
            ),
        ],
    )
    overland_regular = database_path / "static" / "templates" / "overland"
    overland_quadtree = database_path / "static" / "templates" / "overland_qt"
    if not overland_regular.exists():
        raise FileNotFoundError(
            f"Overland regular model folder not found: {overland_regular}"
        )
    if not overland_quadtree.exists():
        raise FileNotFoundError(
            f"Overland quadtree model folder not found: {overland_quadtree}"
        )

    config = SfincsConfigModel(
        csname="WGS 84 / UTM zone 17N",
        cstype=Cstype.projected,
        offshore_model=FloodModel(
            name="offshore",
            reference="MSL",
            vertical_offset=us.UnitfulLength(value=0.6, units=us.UnitTypesLength.feet),
        ),
        overland_model=FloodModel(
            name=overland_regular.name if not quadtree else overland_quadtree.name,
            reference="NAVD88",
        ),
        floodmap_units=us.UnitTypesLength.feet,
        save_simulation=False,
    )

    tide_gauge = TideGauge(
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
        slr_scenarios=SlrScenariosModel(relative_to_year=2020, file="slr/slr.csv"),
        dem=create_dem_model(database_path),
        scs=SCSModel(file="scs_rainfall.csv", type=Scstype.type3),
        cyclone_track_database=CycloneTrackDatabaseModel(file="IBTrACS.NA.v04r00.nc"),
        tide_gauge=tide_gauge,
        river=rivers,
        obs_point=obs_points,
    )
    return sfincs


def create_dem_model(database_path: Path) -> DemModel:
    dem_path = database_path / "static" / "dem" / "dep_subgrid.tif"
    index_path = database_path / "static" / "dem" / "index.tif"
    assert dem_path.exists(), f"DEM file for quadtree model not found: {dem_path}"
    assert (
        index_path.exists()
    ), f"DEM index file for quadtree model not found: {index_path}"
    return DemModel(
        filename=dem_path.name,
        units=us.UnitTypesLength.meters,
        index_filename=index_path.name,
    )


def create_standard_objects() -> StandardObjectModel:
    return StandardObjectModel(
        events=["test_set"],
        strategies=["no_measures"],
        projections=["current"],
    )


def create_site_config(
    database_path: Path,
    fiat: Optional[FiatModel] = None,
    gui: Optional[GuiModel] = None,
    sfincs: Optional[SfincsModel] = None,
    quadtree: bool = True,
) -> Site:
    fiat = fiat or create_fiat_config()
    gui = gui or create_gui_config(database_path)
    sfincs = sfincs or create_sfincs_config(
        database_path=database_path, quadtree=quadtree
    )

    config = Site(
        name="Charleston",
        description="Charleston, SC",
        lat=32.7765,
        lon=-79.9311,
        standard_objects=create_standard_objects(),
        fiat=fiat,
        gui=gui,
        sfincs=sfincs,
        is_coastal=True,
    )
    return config


def update_static_data():
    raise NotImplementedError


if __name__ == "__main__":
    parser = ArgumentParser(description="Create the static data for the database.")
    parser.add_argument(
        "-d",
        "--database_root",
        type=Path,
        default=Path(__file__).parents[3] / "Database",
        help="Path to the database root folder.",
    )
    parser.add_argument(
        "-n",
        "--database_name",
        type=str,
        default="charleston_test",
        help="Name of the database.",
    )
    args = parser.parse_args()

    settings = Settings(
        DATABASE_ROOT=Path(args.database_root).resolve(),
        DATABASE_NAME=args.database_name,
    )
    print(f"Updating database: {settings.database_path}")
    update_database_static(settings.database_path)
