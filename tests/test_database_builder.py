import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from flood_adapt import Settings
from flood_adapt import unit_system as us
from flood_adapt.database_builder.create_database import SviConfigModel
from flood_adapt.database_builder.database_builder import (
    Basins,
    ConfigModel,
    DatabaseBuilder,
    FootprintsOptions,
    GuiConfigModel,
    Point,
    SpatialJoinModel,
    TideGaugeConfigModel,
    UnitSystems,
)
from flood_adapt.object_model.hazard.interface.forcing import Scstype
from flood_adapt.object_model.hazard.interface.tide_gauge import TideGaugeSource
from flood_adapt.object_model.interface.config.fiat import BenefitsModel, BFEModel
from flood_adapt.object_model.interface.config.sfincs import (
    DatumModel,
    FloodModel,
    ObsPointModel,
    SCSModel,
    SlrModel,
    WaterlevelReferenceModel,
)


class TestDataBaseBuilder:
    @pytest.fixture(scope="function")
    def config(self):
        db_path = Settings().database_path
        static_path = db_path / "static"
        templates_path = db_path / "static" / "templates"
        with tempfile.TemporaryDirectory() as tmpdirname:
            config = ConfigModel(
                #
                # General
                #
                name="test_db",
                database_path=tmpdirname,
                unit_system=UnitSystems.metric,
                gui=GuiConfigModel(
                    max_aggr_dmg=1e6,
                    max_flood_depth=1e6,
                    max_footprint_dmg=1e6,
                    max_benefits=1e6,
                ),
                infographics=True,
                probabilistic_set="test_set",
                #
                # SFINCS
                #
                references=WaterlevelReferenceModel(
                    reference="MLLW",
                    datums=[
                        DatumModel(
                            name="MLLW",
                            height=us.UnitfulLength(
                                value=0.0, units=us.UnitTypesLength.meters
                            ),
                        ),
                        DatumModel(
                            name="MSL",
                            height=us.UnitfulLength(
                                value=0.89, units=us.UnitTypesLength.meters
                            ),
                        ),
                        DatumModel(
                            name="NAVD88",
                            height=us.UnitfulLength(
                                value=0.957, units=us.UnitTypesLength.meters
                            ),
                        ),
                        DatumModel(
                            name="MHHW",
                            height=us.UnitfulLength(
                                value=1.757, units=us.UnitTypesLength.meters
                            ),
                        ),
                    ],
                ),
                sfincs_overland=FloodModel(
                    name=str(templates_path / "overland"),
                    reference="NAVD88",
                ),
                sfincs_offshore=FloodModel(
                    name=str(templates_path / "offshore"),
                    reference="MSL",
                ),
                excluded_datums=["NAVD88"],
                slr=SlrModel(
                    file=str(static_path / "slr/slr.csv"),
                    relative_to_year=2020,
                ),
                scs=SCSModel(
                    file=str(static_path / "scs/scs.csv"),
                    type=Scstype.type3,
                ),
                tide_gauge=TideGaugeConfigModel(
                    id=8665530,
                    ref="MSL",
                    source=TideGaugeSource.noaa_coops,
                    description="Charleston Cooper River Entrance",
                    location=Point(lat=32.78, lon=-79.9233),
                    max_distance=us.UnitfulLength(
                        value=100, units=us.UnitTypesLength.miles
                    ),
                ),
                cyclones=True,
                cyclone_basin=Basins.NA,
                obs_point=[
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
                ],
                #
                # FIAT
                #
                fiat=str(templates_path / "fiat"),
                aggregation_areas=[
                    SpatialJoinModel(
                        name="aggr_lvl_1",
                        file=str(
                            templates_path / "fiat/aggregation_areas/aggr_lvl_1.geojson"
                        ),
                        field_name="name",
                    ),
                    SpatialJoinModel(
                        name="aggr_lvl_2",
                        file=str(
                            templates_path / "fiat/aggregation_areas/aggr_lvl_2.geojson"
                        ),
                        field_name="name",
                    ),
                ],
                building_footprints=FootprintsOptions.OSM,
                fiat_buildings_name="buildings",
                fiat_roads_name="roads",
                bfe=SpatialJoinModel(
                    file=str(static_path / "bfe/bfe.geojson"),
                    name="bfe",
                    field_name="bfe",
                ),
                svi=SviConfigModel(
                    file=str(static_path / "svi/svi.geojson"),
                    field_name="svi",
                    threshold=0.5,
                ),
                road_width=5,
                return_periods=[1, 2, 5, 10, 25, 50, 100],
            )
            yield config

    def test_read_fiat_model(self, config: ConfigModel):
        builder = DatabaseBuilder(config)
        builder.read_template_fiat_model()

        assert (builder.static_path / "templates" / "fiat").exists()

    def test_read_template_sfincs_overland_model(self, config: ConfigModel):
        builder = DatabaseBuilder(config)
        builder.read_template_sfincs_overland_model()

        assert (builder.static_path / "templates" / "overland").exists()

    def test_read_template_sfincs_offshore_model(self, config: ConfigModel):
        builder = DatabaseBuilder(config)
        builder.read_template_sfincs_offshore_model()

        assert (builder.static_path / "templates" / "offshore").exists()

    def test_read_template_sfincs_offshore_model_not_available(
        self, config: ConfigModel
    ):
        config.sfincs_offshore = None
        builder = DatabaseBuilder(config)
        model = builder.read_template_sfincs_offshore_model()

        assert not (builder.static_path / "templates" / "offshore").exists()
        assert model is None

    def test_create_risk_model(self, config: ConfigModel):
        builder = DatabaseBuilder(config)
        risk = builder.create_risk_model()

        assert risk.return_periods == config.return_periods

    def test_create_benefits_with_test_set(self, config: ConfigModel):
        builder = DatabaseBuilder(config)

        benefits = builder.create_benefit_config()

        expected_benefits = BenefitsModel(
            current_year=datetime.now().year,  # TODO mock datetime
            current_projection="current",
            baseline_strategy="no_measures",
            event_set=config.probabilistic_set,
        )
        assert benefits == expected_benefits

    def test_create_benefits_without_test_set_returns_none(self, config: ConfigModel):
        builder = DatabaseBuilder(config)
        config.probabilistic_set = None
        benefits = builder.create_benefit_config()

        assert benefits is None

    def test_create_footprints(self, config: ConfigModel):
        builder = DatabaseBuilder(config)
        footprints = builder.create_footprints()

        assert footprints == config.building_footprints

    def test_create_aggregation_areas_from_config(self, config: ConfigModel):
        builder = DatabaseBuilder(config)

        areas = builder.create_aggregation_areas()

        assert areas is not None
        assert len(areas) == len(config.aggregation_areas)

        for i, area in enumerate(areas):
            file_name = Path(config.aggregation_areas[i].file).name
            expected_file = f"templates/fiat/aggregation_areas/{file_name}"
            assert area.file == expected_file
            assert (builder.static_path / expected_file).exists()

    def test_create_aggregation_areas_from_region(self, config: ConfigModel):
        builder = DatabaseBuilder(config)
        areas = builder.create_aggregation_areas()

        assert areas == config.aggregation_areas

    def test_create_aggregation_areas_from_fiat_model(self, config: ConfigModel):
        builder = DatabaseBuilder(config)
        areas = builder.create_aggregation_areas()

        assert areas == config.aggregation_areas

    def test_create_bfe(self, config: ConfigModel):
        builder = DatabaseBuilder(config)
        bfe = builder.create_bfe()

        expected_geopackage = builder.static_path / "bfe" / "bfe.gpkg"
        expected_csv = builder.static_path / "bfe" / "bfe.csv"

        expected_bfe = BFEModel(
            geom=expected_geopackage,
            table=expected_csv,
            field_name=config.bfe.field_name,
        )
        assert bfe is not None
        assert expected_geopackage.exists()
        assert expected_csv.exists()
        assert bfe == expected_bfe

    def test_create_svi(self, config: ConfigModel):
        builder = DatabaseBuilder(config)
        svi = builder.create_svi()

        assert svi == config.svi

    def test_create_sfincs_overland(self, config: ConfigModel):
        config.sfincs_offshore = None
        builder = DatabaseBuilder(config)
        sfincs = builder.create_overland_model()

        assert sfincs == config.sfincs_overland

    def test_create_sfincs_offshore(self, config: ConfigModel):
        builder = DatabaseBuilder(config)
        sfincs = builder.create_offshore_model()

        assert sfincs == config.sfincs_offshore

    def test_create_sfincs_offshore_no_offshore_model(self, config: ConfigModel):
        config.sfincs_offshore = None
        builder = DatabaseBuilder(config)
        sfincs = builder.create_offshore_model()

        assert sfincs is None

    def test_create_slr(self, config: ConfigModel):
        builder = DatabaseBuilder(config)
        slr = builder.create_slr()

        assert slr == config.slr

    def test_create_scs(self, config: ConfigModel):
        builder = DatabaseBuilder(config)
        scs = builder.create_scs_model()

        assert scs == config.scs

    def test_create_tide_gauge(self, config: ConfigModel):
        builder = DatabaseBuilder(config)
        tide_gauge = builder.create_tide_gauge()

        assert tide_gauge is not None
