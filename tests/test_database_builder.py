import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock

import pandas as pd
import pytest
import tomli

from flood_adapt import Settings
from flood_adapt import unit_system as us
from flood_adapt.api.static import read_database
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
from flood_adapt.object_model.interface.config.fiat import (
    AggregationModel,
    BenefitsModel,
    BFEModel,
    EquityModel,
    SVIModel,
)
from flood_adapt.object_model.interface.config.sfincs import (
    DatumModel,
    DemModel,
    FloodModel,
    ObsPointModel,
    SCSModel,
    SlrModel,
    WaterlevelReferenceModel,
)


class TestDataBaseBuilder:
    @pytest.fixture(scope="function")
    def mock_config(self):
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
            config.unit_system = UnitSystems.metric

            yield config

    ### Fiat ###
    def test_read_fiat_model(self, mock_config: ConfigModel):
        # Arrange
        mock_config.fiat = str(self.templates_path / "fiat")
        builder = DatabaseBuilder(mock_config)

        # Act
        builder.read_template_fiat_model()

        # Assert
        assert (builder.static_path / "templates" / "fiat").exists()

    def test_create_risk_model(self, mock_config: ConfigModel):
        # Arrange
        mock_config.return_periods = [1, 2, 5, 10, 25, 50, 100]
        builder = DatabaseBuilder(mock_config)

        # Act
        risk = builder.create_risk_model()

        # Assert
        assert risk.return_periods == mock_config.return_periods

    def test_create_risk_model_returns_empty_list(self, mock_config: ConfigModel):
        # Arrange
        mock_config.return_periods = []
        builder = DatabaseBuilder(mock_config)

        # Act
        risk = builder.create_risk_model()

        # Assert
        assert risk.return_periods == []

    def test_create_benefits_with_test_set(self, mock_config: ConfigModel):
        # Arrange
        mock_config.probabilistic_set = "test_set"
        builder = DatabaseBuilder(mock_config)

        # Act
        benefits = builder.create_benefit_config()

        expected_benefits = BenefitsModel(
            current_year=datetime.now().year,  # TODO mock datetime
            current_projection="current",
            baseline_strategy="no_measures",
            event_set=mock_config.probabilistic_set,
        )

        # Assert
        assert benefits == expected_benefits

    def test_create_benefits_without_test_set_returns_none(
        self, mock_config: ConfigModel
    ):
        # Arrange
        mock_config.probabilistic_set = None
        builder = DatabaseBuilder(mock_config)

        # Act
        benefits = builder.create_benefit_config()

        # Assert
        assert benefits is None

    def test_create_footprints_from_OSM(self, mock_config: ConfigModel):
        # Arrange
        # TODO add/mock region
        mock_config.building_footprints = FootprintsOptions.OSM
        mock_config.fiat_buildings_name = "buildings"
        builder = DatabaseBuilder(mock_config)

        # Act
        footprints = builder.create_footprints()

        # Assert
        assert footprints == mock_config.building_footprints

    def test_create_aggregation_areas_from_config(self, mock_config: ConfigModel):
        # Arrange
        mock_config.aggregation_areas = [
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
        mock_config.fiat_buildings_name = "buildings"
        builder = DatabaseBuilder(mock_config)

        # Act
        areas = builder.create_aggregation_areas()

        # Assert
        assert areas is not None
        assert len(areas) == len(mock_config.aggregation_areas)

        for i, area in enumerate(areas):
            file_name = (
                Path(mock_config.aggregation_areas[i].file).with_suffix(".gpkg").name
            )
            expected_file = f"templates/fiat/exposure/aggregation_areas/{file_name}"
            assert area.file == expected_file
            assert (builder.static_path / expected_file).exists()

    def test_create_aggregation_areas_from_region(self, mock_config: ConfigModel):
        # Arrange
        # TODO add/mock region
        mock_config.fiat_buildings_name = "buildings"
        mock_config.aggregation_areas = None
        builder = DatabaseBuilder(mock_config)

        # Act
        areas = builder.create_aggregation_areas()

        # Assert
        expected_region = Path(builder.fiat_model.root).joinpath(
            "aggregation_areas", "region.geojson"
        )
        expected_areas = [
            AggregationModel(
                name="region",
                file=str(expected_region.relative_to(builder.static_path).as_posix()),
                field_name="aggr_id",
            )
        ]
        assert areas is not None
        assert areas == expected_areas
        assert expected_region.exists()

    def test_create_aggregation_areas_from_fiat_model(self, mock_config: ConfigModel):
        # Arrange
        # TODO get a fiat model with aggregation areas
        mock_config.aggregation_areas = None
        mock_config.fiat_buildings_name = "buildings"
        builder = DatabaseBuilder(mock_config)
        builder.fiat_model = Mock(wraps=builder.fiat_model)
        builder.fiat_model.spatial_joins = {
            "aggregation_areas": [
                {
                    "name": "aggr_lvl_1",
                    "file": "aggregation_areas/aggr_lvl_1.geojson",
                    "field_name": "name",
                    "equity": {
                        "census_data": "census_data.geojson",
                        "percapitaincome_label": "income",
                        "totalpopulation_label": "population",
                    },
                },
                {
                    "name": "aggr_lvl_2",
                    "file": "aggregation_areas/aggr_lvl_2.geojson",
                    "field_name": "name",
                    "equity": None,
                },
            ]
        }

        # Act
        areas = builder.create_aggregation_areas()

        # Assert
        assert areas is not None
        expected_areas = [
            AggregationModel(
                name="aggr_lvl_1",
                file="templates/fiat/aggregation_areas/aggr_lvl_1.geojson",
                field_name="name",
                equity=EquityModel(
                    census_data="templates/fiat/census_data.geojson",
                    percapitaincome_label="income",
                    totalpopulation_label="population",
                ),
            ),
            AggregationModel(
                name="aggr_lvl_2",
                file="templates/fiat/aggregation_areas/aggr_lvl_2.geojson",
                field_name="name",
                equity=None,
            ),
        ]
        assert areas == expected_areas

    def test_create_bfe(self, mock_config: ConfigModel):
        # Arrange
        mock_config.bfe = SpatialJoinModel(
            file=str(self.static_path / "bfe/bfe.geojson"),
            name="bfe",
            field_name="bfe",
        )
        mock_config.fiat_buildings_name = "buildings"
        builder = DatabaseBuilder(mock_config)

        # Act
        bfe = builder.create_bfe()

        # Assert
        expected_geopackage = builder.static_path / "bfe/bfe.gpkg"
        expected_csv = builder.static_path / "bfe/bfe.csv"
        expected_bfe = BFEModel(
            geom="bfe/bfe.gpkg",
            table="bfe/bfe.csv",
            field_name=mock_config.bfe.field_name,
        )
        assert bfe is not None
        assert expected_geopackage.exists()
        assert expected_csv.exists()
        assert bfe == expected_bfe

    def test_create_bfe_returns_none(self, mock_config: ConfigModel):
        # Arrange
        mock_config.bfe = None
        builder = DatabaseBuilder(mock_config)

        # Act
        bfe = builder.create_bfe()

        # Assert
        assert bfe is None
        assert not (builder.static_path / "bfe").exists()

    def test_create_svi(self, mock_config: ConfigModel):
        # Arrange
        mock_config.svi = SviConfigModel(
            file=str(self.static_path / "templates/fiat/svi/CDC_svi_2020.gpkg"),
            field_name="SVI",
            threshold=0.5,
        )
        mock_config.fiat_buildings_name = "buildings"
        builder = DatabaseBuilder(mock_config)

        # Act
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
    def test_read_template_sfincs_overland_model(self, mock_config: ConfigModel):
        # Arrange
        builder = DatabaseBuilder(mock_config)

        # Act
        builder.read_template_sfincs_overland_model()

        # Assert
        assert (builder.static_path / "templates" / "overland").exists()

    def test_read_template_sfincs_offshore_model(self, mock_config: ConfigModel):
        # Arrange
        builder = DatabaseBuilder(mock_config)

        # Act
        builder.read_template_sfincs_offshore_model()

        # Assert
        assert (builder.static_path / "templates" / "offshore").exists()

    def test_read_template_sfincs_offshore_model_not_available(
        self, mock_config: ConfigModel
    ):
        # Arrange
        mock_config.sfincs_offshore = None
        builder = DatabaseBuilder(mock_config)

        # Act
        model = builder.read_template_sfincs_offshore_model()

        # Assert
        assert not (builder.static_path / "templates" / "offshore").exists()
        assert model is None

    def test_create_sfincs_overland(self, mock_config: ConfigModel):
        # Arrange
        mock_config.sfincs_offshore = None
        builder = DatabaseBuilder(mock_config)

        # Act
        sfincs = builder.create_overland_model()

        # Assert
        expected_floodmodel = FloodModel(
            name="overland",
            reference=mock_config.sfincs_overland.reference,
        )
        assert sfincs == expected_floodmodel
        assert (builder.static_path / "templates" / "overland").exists()

    def test_create_sfincs_offshore(self, mock_config: ConfigModel):
        # Arrange
        builder = DatabaseBuilder(mock_config)

        # Act
        sfincs = builder.create_offshore_model()

        # Assert
        expected_floodmodel = FloodModel(
            name="offshore",
            reference=mock_config.sfincs_offshore.reference,
        )

        assert sfincs == expected_floodmodel
        assert (builder.static_path / "templates" / "offshore").exists()

    def test_create_sfincs_offshore_no_offshore_model(self, mock_config: ConfigModel):
        # Arrange
        mock_config.sfincs_offshore = None
        builder = DatabaseBuilder(mock_config)

        # Act
        sfincs = builder.create_offshore_model()

        # Assert
        assert sfincs is None
        assert not (builder.static_path / "templates" / "offshore").exists()

    def test_create_slr(self, mock_config: ConfigModel):
        # Arrange
        mock_config.slr = SlrModel(
            file=str(self.static_path / "slr/slr.csv"),
            relative_to_year=2020,
        )
        builder = DatabaseBuilder(mock_config)

        # Act
        slr = builder.create_slr()

        # Assert
        expected_file = builder.static_path / "slr" / Path(mock_config.slr.file).name
        expected_slr = SlrModel(
            file=expected_file.relative_to(builder.static_path).as_posix(),
            relative_to_year=mock_config.slr.relative_to_year,
        )
        assert slr == expected_slr
        assert expected_file.exists()

    def test_create_slr_returns_none(self, mock_config: ConfigModel):
        # Arrange
        mock_config.slr = None
        builder = DatabaseBuilder(mock_config)

        # Act
        slr = builder.create_slr()

        # Assert
        assert slr is None
        assert not (builder.static_path / "slr").exists()

    def test_create_scs(self, mock_config: ConfigModel):
        # Arrange
        mock_config.scs = SCSModel(
            file=str(self.static_path / "scs/scs_rainfall.csv"),
            type=Scstype.type3,
        )
        builder = DatabaseBuilder(mock_config)

        # Act
        scs = builder.create_scs_model()

        # Assert
        expected_file = builder.static_path / "scs" / Path(mock_config.scs.file).name
        expected_scs = SCSModel(
            file=expected_file.name,
            type=mock_config.scs.type,
        )
        assert scs == expected_scs
        assert expected_file.exists()

    def test_create_scs_returns_none(self, mock_config: ConfigModel):
        # Arrange
        mock_config.scs = None
        builder = DatabaseBuilder(mock_config)

        # Act
        scs = builder.create_scs_model()

        # Assert
        assert scs is None
        assert not (builder.static_path / "scs").exists()

    def test_create_dem_model_tiles_created(self, mock_config: ConfigModel):
        # Arrange
        mock_config.subgrid = DemModel(
            filename=str(self.static_path / "dem/charleston_14m.tif"),
            units=us.UnitTypesLength.meters,
        )
        builder = DatabaseBuilder(mock_config)

        root = Path(builder.sfincs_overland_model.root)
        assert not (root / "tiles/indices").exists()
        assert not (root / "tiles/topobathy").exists()

        # Act
        dem = builder.create_dem_model()

        # Assert
        expected_tif = (
            builder.static_path / "dem" / Path(mock_config.subgrid.filename).name
        )
        expected_dem = DemModel(
            filename=expected_tif.name,
            units=mock_config.subgrid.units,
        )
        expected_tiles = builder.static_path / "dem" / "tiles"
        expected_indices = expected_tiles / "indices"
        expected_topo = expected_tiles / "topobathy"

        assert dem == expected_dem

        for file in [
            expected_tif,
            expected_tiles,
            expected_indices,
            expected_topo,
        ]:
            assert file.exists()

    def test_create_dem_model_tiles_moved(self, mock_config: ConfigModel):
        # Arrange
        mock_config.subgrid = DemModel(
            filename=str(self.static_path / "dem/charleston_14m.tif"),
            units=us.UnitTypesLength.meters,
        )
        tiles_path = self.static_path / "dem/tiles"
        indices_path = tiles_path / "indices"
        topo_path = tiles_path / "topobathy"
        for file in [tiles_path, indices_path, topo_path]:
            assert file.exists()

        builder = DatabaseBuilder(mock_config)
        builder.sfincs_overland_model.setup_tiles = Mock()
        shutil.copytree(tiles_path, Path(builder.sfincs_overland_model.root) / "tiles")

        # Act
        dem = builder.create_dem_model()

        # Assert
        builder.sfincs_overland_model.setup_tiles.assert_not_called()
        expected_tif = (
            builder.static_path / "dem" / Path(mock_config.subgrid.filename).name
        )
        expected_dem = DemModel(
            filename=expected_tif.name,
            units=mock_config.subgrid.units,
        )
        expected_tiles = builder.static_path / "dem" / "tiles"
        expected_indices = expected_tiles / "indices"
        expected_topo = expected_tiles / "topobathy"

        assert dem == expected_dem

        for file in [
            expected_tif,
            expected_tiles,
            expected_indices,
            expected_topo,
        ]:
            assert file.exists()

    def test_create_tide_gauge_file_based(
        self,
        mock_config: ConfigModel,
        dummy_1d_timeseries_df: pd.DataFrame,
        tmp_path: Path,
    ):
        # Arrange
        tide_gauge_file = tmp_path / "dummy.csv"
        dummy_1d_timeseries_df.to_csv(tide_gauge_file)
        mock_config.tide_gauge = TideGaugeConfigModel(
            id=8665530,
            ref="MSL",
            source=TideGaugeSource.file,
            file=str(tide_gauge_file),
            description="Charleston Cooper River Entrance",
            location=Point(lat=32.78, lon=-79.9233),
            max_distance=us.UnitfulLength(value=100, units=us.UnitTypesLength.miles),
        )
        builder = DatabaseBuilder(mock_config)

        # Act
        tide_gauge = builder.create_tide_gauge()

        # Assert
        assert tide_gauge is not None
        assert tide_gauge.source == TideGaugeSource.file
        assert tide_gauge.file is not None
        assert (builder.static_path / tide_gauge.file).exists()

    def test_create_tide_gauge_file_based_file_is_none(self, mock_config: ConfigModel):
        # Arrange
        mock_config.tide_gauge = TideGaugeConfigModel(
            id=8665530,
            ref="MSL",
            source=TideGaugeSource.file,
            file=None,
            description="Charleston Cooper River Entrance",
            location=Point(lat=32.78, lon=-79.9233),
            max_distance=us.UnitfulLength(value=100, units=us.UnitTypesLength.miles),
        )
        builder = DatabaseBuilder(mock_config)

        # Act
        tide_gauge = builder.create_tide_gauge()

        # Assert
        assert tide_gauge is None

    def test_create_tide_gauge_noaa_coops(self, mock_config: ConfigModel):
        # Arrange
        mock_config.tide_gauge = TideGaugeConfigModel(
            id=8665530,
            ref="MSL",
            source=TideGaugeSource.noaa_coops,
            description="Charleston Cooper River Entrance",
            location=Point(lat=32.78, lon=-79.9233),
            max_distance=us.UnitfulLength(value=100, units=us.UnitTypesLength.miles),
        )
        builder = DatabaseBuilder(mock_config)

        # Act
        tide_gauge = builder.create_tide_gauge()

        # Assert
        assert tide_gauge is not None

    def test_create_tide_gauge_returns_none(self, mock_config: ConfigModel):
        # Arrange
        mock_config.tide_gauge = None
        builder = DatabaseBuilder(mock_config)

        # Act
        tide_gauge = builder.create_tide_gauge()

        # Assert
        assert tide_gauge is None

    def test_create_infometrics_mandatory_only(self, mock_config: ConfigModel):
        # Arrange
        mock_config.svi = SviConfigModel(
            file=str(self.templates_path / "fiat/svi/CDC_svi_2020.gpkg"),
            field_name="SVI",
            threshold=0.5,
        )
        mock_config.fiat_buildings_name = "buildings"
        mock_config.infographics = None
        # TODO fix create_aggregation_areas()
        builder = DatabaseBuilder(mock_config)

        # Act
        builder.create_infometrics()

        # Assert
        path_im = builder.root / "static" / "templates" / "infometrics"
        assert path_im.exists()
        for file_name in [
            "mandatory_metrics_config_risk.toml",
            "mandatory_metrics_config.toml",
        ]:
            file_path = path_im / file_name
            assert file_path.exists()
            with open(file_path, "rb") as f:
                attrs = tomli.load(f)
                assert attrs["aggregateBy"] == ["aggr_lvl_1", "aggr_lvl_2"]
                assert all(
                    "road" not in query["name"].lower() for query in attrs["queries"]
                )
                assert all(
                    query["long_name"] == "Damage in USD" for query in attrs["queries"]
                )
                assert all(query["filter"] == "SVI > 0.5" for query in attrs["queries"])

    def test_create_infometrics_no_svi(self, mock_config: ConfigModel):
        # Arrange
        mock_config.svi = None
        mock_config.fiat_buildings_name = "buildings"
        # TODO fix create_aggregation_areas()
        builder = DatabaseBuilder(mock_config)

        # Act
        builder.create_infometrics()

        # Assert
        path_im = builder.root / "static" / "templates" / "infometrics"
        assert path_im.exists()
        for file_name in ["metrics_config.toml", "metrics_config_risk.toml"]:
            file_path = path_im / file_name
            assert file_path.exists()
            with open(file_path, "rb") as f:
                attrs = tomli.load(f)
                assert attrs["aggregateBy"] == ["aggr_lvl_1", "aggr_lvl_2"]
                assert all(
                    "road" not in query["name"].lower() for query in attrs["queries"]
                )
                assert all(
                    query["long_name"] == "Damage in USD" for query in attrs["queries"]
                )
                assert all(
                    "SVI_threshold" not in query["filter"] for query in attrs["queries"]
                )

    def test_create_infometrics_no_roads(self, mock_config: ConfigModel):
        # Arrange
        mock_config.svi = None
        mock_config.fiat_buildings_name = "buildings"
        # TODO fix create_aggregation_areas()
        builder = DatabaseBuilder(mock_config)

        # Act
        builder.create_infometrics()

        # Assert
        path_im = builder.root / "static" / "templates" / "infometrics"
        assert path_im.exists()
        for file_name in ["metrics_config.toml", "metrics_config_risk.toml"]:
            file_path = path_im / file_name
            assert file_path.exists()
            with open(file_path, "rb") as f:
                attrs = tomli.load(f)
                assert attrs["aggregateBy"] == ["aggr_lvl_1", "aggr_lvl_2"]
                assert all(
                    "road" not in query["name"].lower() for query in attrs["queries"]
                )
                assert all(
                    query["long_name"] == "Damage in USD" for query in attrs["queries"]
                )
                assert all(
                    "SVI_threshold" not in query["filter"] for query in attrs["queries"]
                )

    def test_build(self, full_config: ConfigModel):
        # Arrange
        builder = DatabaseBuilder(full_config)

        # Act
        builder.build()

        # Assert
        db = read_database(full_config.database_path)
        assert db is not None

    @pytest.fixture(scope="function")
    def full_config(self):
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
                subgrid=DemModel(
                    filename=str(static_path / "dem/charleston_14m.tif"),
                    units=us.UnitTypesLength.meters,
                ),
                excluded_datums=["NAVD88"],
                slr=SlrModel(
                    file=str(static_path / "slr/slr.csv"),
                    relative_to_year=2020,
                ),
                scs=SCSModel(
                    file=str(static_path / "scs/scs_rainfall.csv"),
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
                    file=str(static_path / "templates/fiat/svi/CDC_svi_2020.gpkg"),
                    field_name="SVI",
                    threshold=0.5,
                ),
                road_width=5,
                return_periods=[1, 2, 5, 10, 25, 50, 100],
            )
            yield config
