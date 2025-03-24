import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock

import pandas as pd
import pytest

from flood_adapt import Settings
from flood_adapt import unit_system as us
from flood_adapt.database_builder.create_database import SviConfigModel
from flood_adapt.database_builder.database_builder import (
    ConfigModel,
    DatabaseBuilder,
    FootprintsOptions,
    Point,
    SpatialJoinModel,
    TideGaugeConfigModel,
)
from flood_adapt.object_model.hazard.interface.forcing import Scstype
from flood_adapt.object_model.hazard.interface.tide_gauge import TideGaugeSource
from flood_adapt.object_model.interface.config.fiat import (
    BenefitsModel,
    BFEModel,
    SVIModel,
)
from flood_adapt.object_model.interface.config.sfincs import (
    FloodModel,
    SCSModel,
    SlrModel,
)


class TestDataBaseBuilder:
    # @pytest.fixture(scope="function")
    # def config(self):
    #     db_path = Settings().database_path
    #     static_path = db_path / "static"
    #     templates_path = db_path / "static" / "templates"
    #     with tempfile.TemporaryDirectory() as tmpdirname:
    #         config = ConfigModel(
    #             #
    #             # General
    #             #
    #             name="test_db",
    #             database_path=tmpdirname,
    #             unit_system=UnitSystems.metric,
    #             gui=GuiConfigModel(
    #                 max_aggr_dmg=1e6,
    #                 max_flood_depth=1e6,
    #                 max_footprint_dmg=1e6,
    #                 max_benefits=1e6,
    #             ),
    #             infographics=True,
    #             probabilistic_set="test_set",
    #             #
    #             # SFINCS
    #             #
    #             references=WaterlevelReferenceModel(
    #                 reference="MLLW",
    #                 datums=[
    #                     DatumModel(
    #                         name="MLLW",
    #                         height=us.UnitfulLength(
    #                             value=0.0, units=us.UnitTypesLength.meters
    #                         ),
    #                     ),
    #                     DatumModel(
    #                         name="MSL",
    #                         height=us.UnitfulLength(
    #                             value=0.89, units=us.UnitTypesLength.meters
    #                         ),
    #                     ),
    #                     DatumModel(
    #                         name="NAVD88",
    #                         height=us.UnitfulLength(
    #                             value=0.957, units=us.UnitTypesLength.meters
    #                         ),
    #                     ),
    #                     DatumModel(
    #                         name="MHHW",
    #                         height=us.UnitfulLength(
    #                             value=1.757, units=us.UnitTypesLength.meters
    #                         ),
    #                     ),
    #                 ],
    #             ),
    #             sfincs_overland=FloodModel(
    #                 name=str(templates_path / "overland"),
    #                 reference="NAVD88",
    #             ),
    #             sfincs_offshore=FloodModel(
    #                 name=str(templates_path / "offshore"),
    #                 reference="MSL",
    #             ),
    #             excluded_datums=["NAVD88"],
    #             slr=SlrModel(
    #                 file=str(static_path / "slr/slr.csv"),
    #                 relative_to_year=2020,
    #             ),
    #             scs=SCSModel(
    #                 file=str(static_path / "scs/scs_rainfall.csv"),
    #                 type=Scstype.type3,
    #             ),
    #             tide_gauge=TideGaugeConfigModel(
    #                 id=8665530,
    #                 ref="MSL",
    #                 source=TideGaugeSource.noaa_coops,
    #                 description="Charleston Cooper River Entrance",
    #                 location=Point(lat=32.78, lon=-79.9233),
    #                 max_distance=us.UnitfulLength(
    #                     value=100, units=us.UnitTypesLength.miles
    #                 ),
    #             ),
    #             cyclones=True,
    #             cyclone_basin=Basins.NA,
    #             obs_point=[
    #                 ObsPointModel(
    #                     name="ashley_river",
    #                     description="Ashley River - James Island Expy",
    #                     lat=32.7765,
    #                     lon=-79.9543,
    #                 ),
    #                 ObsPointModel(
    #                     name=8665530,
    #                     description="Charleston Cooper River Entrance",
    #                     ID=8665530,
    #                     lat=32.78,
    #                     lon=-79.9233,
    #                 ),
    #             ],
    #             #
    #             # FIAT
    #             #
    #             fiat=str(templates_path / "fiat"),
    #             aggregation_areas=[
    #                 SpatialJoinModel(
    #                     name="aggr_lvl_1",
    #                     file=str(
    #                         templates_path / "fiat/aggregation_areas/aggr_lvl_1.geojson"
    #                     ),
    #                     field_name="name",
    #                 ),
    #                 SpatialJoinModel(
    #                     name="aggr_lvl_2",
    #                     file=str(
    #                         templates_path / "fiat/aggregation_areas/aggr_lvl_2.geojson"
    #                     ),
    #                     field_name="name",
    #                 ),
    #             ],
    #             building_footprints=FootprintsOptions.OSM,
    #             fiat_buildings_name="buildings",
    #             fiat_roads_name="roads",
    #             bfe=SpatialJoinModel(
    #                 file=str(static_path / "bfe/bfe.geojson"),
    #                 name="bfe",
    #                 field_name="bfe",
    #             ),
    #             svi=SviConfigModel(
    #                 file=str(static_path / "templates/fiat/svi/CDC_svi_2020.gpkg"),
    #                 field_name="SVI",
    #                 threshold=0.5,
    #             ),
    #             road_width=5,
    #             return_periods=[1, 2, 5, 10, 25, 50, 100],
    #         )
    #         yield config

    @pytest.fixture(scope="function")
    def config(self):
        """Create a temporary database path and return a minimal mocked ConfigModel object."""
        self.db_path = Settings().database_path
        self.static_path = self.db_path / "static"
        self.templates_path = self.db_path / "static" / "templates"
        with tempfile.TemporaryDirectory() as tmpdirname:
            config = Mock()
            config.database_path = tmpdirname
            config.fiat = str(self.templates_path / "fiat")
            config.sfincs_overland = FloodModel(
                name=str(self.templates_path / "overland"),
                reference="NAVD88",
            )
            config.sfincs_offshore = FloodModel(
                name=str(self.templates_path / "offshore"),
                reference="MSL",
            )
            config.unit_system = "metric"

            yield config

    ### Fiat ###
    def test_read_fiat_model(self, config: ConfigModel):
        # Arrange
        config.fiat = str(self.templates_path / "fiat")

        # Act
        builder = DatabaseBuilder(config)
        builder.read_template_fiat_model()

        # Assert
        assert (builder.static_path / "templates" / "fiat").exists()

    def test_create_risk_model(self, config: ConfigModel):
        # Arrange
        config.return_periods = [1, 2, 5, 10, 25, 50, 100]

        # Act
        builder = DatabaseBuilder(config)
        risk = builder.create_risk_model()

        # Assert
        assert risk.return_periods == config.return_periods

    def test_create_risk_model_returns_empty_list(self, config: ConfigModel):
        # Arrange
        config.return_periods = []

        # Act
        builder = DatabaseBuilder(config)
        risk = builder.create_risk_model()

        # Assert
        assert risk.return_periods == []

    def test_create_benefits_with_test_set(self, config: ConfigModel):
        # Arrange
        config.probabilistic_set = "test_set"

        # Act
        builder = DatabaseBuilder(config)
        benefits = builder.create_benefit_config()

        expected_benefits = BenefitsModel(
            current_year=datetime.now().year,  # TODO mock datetime
            current_projection="current",
            baseline_strategy="no_measures",
            event_set=config.probabilistic_set,
        )

        # Assert
        assert benefits == expected_benefits

    def test_create_benefits_without_test_set_returns_none(self, config: ConfigModel):
        # Arrange
        config.probabilistic_set = None

        # Act
        builder = DatabaseBuilder(config)
        benefits = builder.create_benefit_config()

        # Assert
        assert benefits is None

    def test_create_footprints_from_OSM(self, config: ConfigModel):
        # Arrange
        # TODO add/mock region
        config.building_footprints = FootprintsOptions.OSM
        config.fiat_buildings_name = "buildings"

        # Act
        builder = DatabaseBuilder(config)
        footprints = builder.create_footprints()

        # Assert
        assert footprints == config.building_footprints

    def test_create_aggregation_areas_from_config(self, config: ConfigModel):
        # Arrange
        config.aggregation_areas = [
            SpatialJoinModel(
                name="aggr_lvl_1",
                file=str(
                    self.templates_path / "fiat/aggregation_areas/aggr_lvl_1.geojson"
                ),
                field_name="name",
            ),
            SpatialJoinModel(
                name="aggr_lvl_2",
                file=str(
                    self.templates_path / "fiat/aggregation_areas/aggr_lvl_2.geojson"
                ),
                field_name="name",
            ),
        ]
        config.fiat_buildings_name = "buildings"

        # Act
        builder = DatabaseBuilder(config)
        areas = builder.create_aggregation_areas()

        # Assert
        assert areas is not None
        assert len(areas) == len(config.aggregation_areas)

        for i, area in enumerate(areas):
            file_name = Path(config.aggregation_areas[i].file).name
            expected_file = f"templates/fiat/aggregation_areas/{file_name}"
            assert area.file == expected_file
            assert (builder.static_path / expected_file).exists()

    def test_create_aggregation_areas_from_region(self, config: ConfigModel):
        # Arrange
        # TODO add/mock region
        config.aggregation_areas = None

        # Act
        builder = DatabaseBuilder(config)
        areas = builder.create_aggregation_areas()

        # Assert
        # TODO asserts

    def test_create_aggregation_areas_from_fiat_model(self, config: ConfigModel):
        # Arrange
        # TODO add/mock region file
        config.aggregation_areas = None

        # Act
        builder = DatabaseBuilder(config)
        areas = builder.create_aggregation_areas()

        # Assert
        assert areas is not None

    def test_create_bfe(self, config: ConfigModel):
        # Arrange
        config.bfe = SpatialJoinModel(
            file=str(self.static_path / "bfe/bfe.geojson"),
            name="bfe",
            field_name="bfe",
        )
        config.fiat_buildings_name = "buildings"

        # Act
        builder = DatabaseBuilder(config)
        bfe = builder.create_bfe()

        # Assert
        expected_geopackage = builder.static_path / "bfe/bfe.gpkg"
        expected_csv = builder.static_path / "bfe/bfe.csv"
        expected_bfe = BFEModel(
            geom="bfe/bfe.gpkg",
            table="bfe/bfe.csv",
            field_name=config.bfe.field_name,
        )
        assert bfe is not None
        assert expected_geopackage.exists()
        assert expected_csv.exists()
        assert bfe == expected_bfe

    def test_create_bfe_returns_none(self, config: ConfigModel):
        # Arrange
        config.bfe = None

        # Act
        builder = DatabaseBuilder(config)
        bfe = builder.create_bfe()

        # Assert
        assert bfe is None
        assert not (builder.static_path / "bfe").exists()

    def test_create_svi(self, config: ConfigModel):
        # Arrange
        config.svi = SviConfigModel(
            file=str(self.static_path / "templates/fiat/svi/CDC_svi_2020.gpkg"),
            field_name="SVI",
            threshold=0.5,
        )
        config.fiat_buildings_name = "buildings"

        # Act
        builder = DatabaseBuilder(config)
        svi = builder.create_svi()

        # Assert
        expected_svi_path = (
            builder.static_path / "templates" / "fiat" / "svi" / "svi.gpkg"
        )
        expected_svi = SVIModel(
            geom=expected_svi_path.relative_to(builder.static_path).as_posix(),
            field_name="SVI",
        )
        assert svi is not None
        assert expected_svi_path.exists()
        assert svi == expected_svi

    ### Sfincs ###
    def test_read_template_sfincs_overland_model(self, config: ConfigModel):
        # Arrange

        # Act
        builder = DatabaseBuilder(config)
        builder.read_template_sfincs_overland_model()

        # Assert
        assert (builder.static_path / "templates" / "overland").exists()

    def test_read_template_sfincs_offshore_model(self, config: ConfigModel):
        # Arrange

        # Act
        builder = DatabaseBuilder(config)
        builder.read_template_sfincs_offshore_model()

        # Assert
        assert (builder.static_path / "templates" / "offshore").exists()

    def test_read_template_sfincs_offshore_model_not_available(
        self, config: ConfigModel
    ):
        # Arrange
        config.sfincs_offshore = None

        # Act
        builder = DatabaseBuilder(config)
        model = builder.read_template_sfincs_offshore_model()

        # Assert
        assert not (builder.static_path / "templates" / "offshore").exists()
        assert model is None

    def test_create_sfincs_overland(self, config: ConfigModel):
        # Arrange
        config.sfincs_offshore = None

        # Act
        builder = DatabaseBuilder(config)
        sfincs = builder.create_overland_model()

        # Assert
        expected_floodmodel = FloodModel(
            name="overland",
            reference=config.sfincs_overland.reference,
        )
        assert sfincs == expected_floodmodel
        assert (builder.static_path / "templates" / "overland").exists()

    def test_create_sfincs_offshore(self, config: ConfigModel):
        # Arrange

        # Act
        builder = DatabaseBuilder(config)
        sfincs = builder.create_offshore_model()

        # Assert
        expected_floodmodel = FloodModel(
            name="offshore",
            reference=config.sfincs_offshore.reference,
        )

        assert sfincs == expected_floodmodel
        assert (builder.static_path / "templates" / "offshore").exists()

    def test_create_sfincs_offshore_no_offshore_model(self, config: ConfigModel):
        # Arrange
        config.sfincs_offshore = None

        # Act
        builder = DatabaseBuilder(config)
        sfincs = builder.create_offshore_model()

        # Assert
        assert sfincs is None
        assert not (builder.static_path / "templates" / "offshore").exists()

    def test_create_slr(self, config: ConfigModel):
        # Arrange
        config.slr = SlrModel(
            file=str(self.static_path / "slr/slr.csv"),
            relative_to_year=2020,
        )

        # Act
        builder = DatabaseBuilder(config)
        slr = builder.create_slr()

        # Assert
        expected_file = builder.static_path / "slr" / Path(config.slr.file).name
        expected_slr = SlrModel(
            file=expected_file.relative_to(builder.static_path).as_posix(),
            relative_to_year=config.slr.relative_to_year,
        )
        assert slr == expected_slr
        assert expected_file.exists()

    def test_create_slr_returns_none(self, config: ConfigModel):
        # Arrange
        config.slr = None

        # Act
        builder = DatabaseBuilder(config)
        slr = builder.create_slr()

        # Assert
        assert slr is None
        assert not (builder.static_path / "slr").exists()

    def test_create_scs(self, config: ConfigModel):
        # Arrange
        config.scs = SCSModel(
            file=str(self.static_path / "scs/scs_rainfall.csv"),
            type=Scstype.type3,
        )

        # Act
        builder = DatabaseBuilder(config)
        scs = builder.create_scs_model()

        # Assert
        expected_file = builder.static_path / "scs" / Path(config.scs.file).name
        expected_scs = SCSModel(
            file=expected_file.name,
            type=config.scs.type,
        )
        assert scs == expected_scs
        assert expected_file.exists()

    def test_create_scs_returns_none(self, config: ConfigModel):
        # Arrange
        config.scs = None

        # Act
        builder = DatabaseBuilder(config)
        scs = builder.create_scs_model()

        # Assert
        assert scs is None
        assert not (builder.static_path / "scs").exists()

    def test_create_tide_gauge_file_based(
        self, config: ConfigModel, dummy_1d_timeseries_df: pd.DataFrame, tmp_path: Path
    ):
        # Arrange
        tide_gauge_file = tmp_path / "dummy.csv"
        dummy_1d_timeseries_df.to_csv(tide_gauge_file)
        config.tide_gauge = TideGaugeConfigModel(
            id=8665530,
            ref="MSL",
            source=TideGaugeSource.file,
            file=str(tide_gauge_file),
            description="Charleston Cooper River Entrance",
            location=Point(lat=32.78, lon=-79.9233),
            max_distance=us.UnitfulLength(value=100, units=us.UnitTypesLength.miles),
        )

        # Act
        builder = DatabaseBuilder(config)
        tide_gauge = builder.create_tide_gauge()

        # Assert
        assert tide_gauge is not None
        assert tide_gauge.source == TideGaugeSource.file
        assert tide_gauge.file is not None
        assert (builder.static_path / tide_gauge.file).exists()

    def test_create_tide_gauge_file_based_file_is_none(self, config: ConfigModel):
        # Arrange
        config.tide_gauge = TideGaugeConfigModel(
            id=8665530,
            ref="MSL",
            source=TideGaugeSource.file,
            file=None,
            description="Charleston Cooper River Entrance",
            location=Point(lat=32.78, lon=-79.9233),
            max_distance=us.UnitfulLength(value=100, units=us.UnitTypesLength.miles),
        )

        # Act
        builder = DatabaseBuilder(config)
        tide_gauge = builder.create_tide_gauge()

        # Assert
        assert tide_gauge is None

    def test_create_tide_gauge_noaa_coops(self, config: ConfigModel):
        # Arrange
        config.tide_gauge = TideGaugeConfigModel(
            id=8665530,
            ref="MSL",
            source=TideGaugeSource.noaa_coops,
            description="Charleston Cooper River Entrance",
            location=Point(lat=32.78, lon=-79.9233),
            max_distance=us.UnitfulLength(value=100, units=us.UnitTypesLength.miles),
        )

        # Act
        builder = DatabaseBuilder(config)
        tide_gauge = builder.create_tide_gauge()

        # Assert
        assert tide_gauge is not None

    def test_create_tide_gauge_returns_none(self, config: ConfigModel):
        # Arrange
        config.tide_gauge = None

        # Act
        builder = DatabaseBuilder(config)
        tide_gauge = builder.create_tide_gauge()

        # Assert
        assert tide_gauge is None
