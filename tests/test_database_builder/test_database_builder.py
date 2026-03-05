import logging
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock

import geopandas as gpd
import pandas as pd
import pytest
import shapely
from pydantic import ValidationError
from shapely import Polygon

from flood_adapt.config.hazard import (
    DatumModel,
    DemModel,
    FloodModel,
    ObsPointModel,
    SCSModel,
    SlrScenariosModel,
    WaterlevelReferenceModel,
)
from flood_adapt.config.impacts import (
    AggregationModel,
    BenefitsModel,
    BFEModel,
    EquityModel,
    RiskModel,
    SVIModel,
)
from flood_adapt.config.settings import Settings
from flood_adapt.database_builder.database_builder import (
    Basins,
    ConfigModel,
    DatabaseBuilder,
    FootprintsOptions,
    GuiConfigModel,
    SpatialJoinModel,
    SviConfigModel,
    TideGaugeConfigModel,
    UnitSystems,
)
from flood_adapt.dbs_classes.database import Database
from flood_adapt.misc.io import read_toml
from flood_adapt.misc.log import FloodAdaptLogging
from flood_adapt.objects.forcing import unit_system as us
from flood_adapt.objects.forcing.tide_gauge import TideGaugeSource
from flood_adapt.objects.forcing.timeseries import Scstype


class TestDataBaseBuilder:
    @pytest.fixture(scope="function")
    def mock_config(self):
        """Create a temporary database path and return a minimal mocked ConfigModel object."""
        self.db_path = Settings().database_path
        self.static_path = self.db_path / "static"
        self.templates_path = self.db_path / "static" / "templates"
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdirname:
            config = Mock(spec=ConfigModel)
            config.database_path = tmpdirname
            config.name = "charleston_db_builder"
            config.fiat = str(self.templates_path / "fiat")
            config.sfincs_overland = FloodModel(
                name=str(self.templates_path / "overland"),
                reference="NAVD88",
            )
            config.sfincs_offshore = FloodModel(
                name=str(self.templates_path / "offshore"),
                reference="MSL",
            )
            config.unit_system = UnitSystems.imperial
            config.event_infographics = None
            config.risk_infographics = None
            config.event_additional_infometrics = None
            config.risk_additional_infometrics = None
            config.return_periods = None

            yield config

    @pytest.fixture(scope="function")
    def mock_aggregation_areas(self):
        """Fixture to mock the create_aggregation_areas method."""
        return Mock(
            return_value=[
                AggregationModel(
                    name="aggr_lvl_1", file="aggr_lvl_1.geojson", field_name="name"
                ),
                AggregationModel(
                    name="aggr_lvl_2", file="aggr_lvl_2.geojson", field_name="name"
                ),
            ]
        )

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

    def test_create_risk_model_returns_default_risk_if_risk_event(
        self, mock_config: ConfigModel
    ):
        # Arrange
        mock_config.probabilistic_set = str(
            self.db_path / "input" / "events" / "test_set"
        )
        mock_config.return_periods = []
        builder = DatabaseBuilder(mock_config)
        builder._probabilistic_set_name = "test_set"

        # Act
        risk = builder.create_risk_model()

        # Assert
        assert risk == RiskModel()

    def test_add_probabilistic_set(self, mock_config: ConfigModel):
        # Arrange
        mock_config.probabilistic_set = str(
            self.db_path / "input" / "events" / "test_set"
        )
        builder = DatabaseBuilder(mock_config)
        builder.add_probabilistic_set()

        assert builder._probabilistic_set_name == "test_set"

    def test_create_benefits_with_test_set(self, mock_config: ConfigModel):
        # Arrange
        mock_config.probabilistic_set = str(
            self.db_path / "input" / "events" / "test_set"
        )
        builder = DatabaseBuilder(mock_config)
        builder._probabilistic_set_name = "test_set"

        # Act
        benefits = builder.create_benefit_config()

        expected_benefits = BenefitsModel(
            current_year=datetime.now().year,  # TODO mock datetime
            current_projection="current",
            baseline_strategy="no_measures",
            event_set="test_set",
        )

        # Assert
        assert benefits == expected_benefits

    def test_create_benefits_without_test_set_returns_none(
        self, mock_config: ConfigModel
    ):
        # Arrange
        mock_config.probabilistic_set = None
        builder = DatabaseBuilder(mock_config)
        builder.add_probabilistic_set()
        # Act
        benefits = builder.create_benefit_config()

        # Assert
        assert benefits is None

    def test_create_footprints_returns_none(self, mock_config: ConfigModel):
        # Arrange
        mock_config.building_footprints = None
        mock_config.fiat_buildings_name = "buildings"
        builder = DatabaseBuilder(mock_config)
        builder.read_template_fiat_model()
        builder.fiat_model = Mock(wraps=builder.fiat_model)

        mock_df = pd.DataFrame({"geometry": [shapely.geometry.Point(0, 0)]})
        mock_exposure_geoms = MagicMock()
        mock_exposure_geoms.__getitem__.return_value = (
            mock_df  # Simulate dictionary-like behavior
        )

        builder.fiat_model.exposure.exposure_geoms = mock_exposure_geoms
        builder.fiat_model.exposure.exposure_db.columns = ["not BF_FID"]
        builder.fiat_model.exposure.geom_names = ["buildings"]
        # Act
        footprints = builder.create_footprints()

        # Assert
        assert footprints is None

    def test_create_footprints_from_config(self, mock_config: ConfigModel):
        # TODO check
        # Arrange
        mock_config.building_footprints = SpatialJoinModel(
            name="BF_FID",
            file=str(self.templates_path / "fiat/exposure/buildings.gpkg"),
            field_name="object_id",
        )
        mock_config.fiat_buildings_name = "buildings"
        builder = DatabaseBuilder(mock_config)
        builder.read_template_fiat_model()

        # Act
        footprints = builder.create_footprints()

        # Assert
        expected_file = (
            Path(builder.fiat_model.root)
            / "exposure"
            / "building_footprints"
            / "building_footprints.gpkg"
        )
        assert footprints is not None
        assert expected_file.exists()
        assert footprints == expected_file.relative_to(builder.static_path)

    def test_create_footprints_from_OSM(self, mock_config: ConfigModel):
        # Arrange
        mock_config.building_footprints = FootprintsOptions.OSM
        mock_config.fiat_buildings_name = "buildings"
        builder = DatabaseBuilder(mock_config)
        builder.read_template_fiat_model()

        del builder.fiat_model.exposure.exposure_db["BF_FID"]

        # Act
        footprints = builder.create_footprints()

        # Assert
        expected_file = Path(
            "templates/fiat/exposure/building_footprints/building_footprints.gpkg"
        )
        assert footprints == expected_file
        assert (builder.static_path / expected_file).exists()

    def test_create_footprints_already_exists(self, mock_config: ConfigModel):
        # Arrange
        mock_config.building_footprints = None
        mock_config.fiat_buildings_name = "buildings"

        builder = DatabaseBuilder(mock_config)
        builder.read_template_fiat_model()
        builder.fiat_model = Mock(wraps=builder.fiat_model)
        builder.fiat_model.exposure.exposure_db = pd.DataFrame(columns=["BF_FID"])
        builder.fiat_model.exposure.exposure_geoms = [
            gpd.GeoDataFrame(
                {"object_id": [1], "geometry": [shapely.geometry.Point(0, 0)]},
                geometry="geometry",
            )
        ]
        builder.fiat_model.exposure.geom_names = ["buildings"]
        builder.fiat_model.spatial_joins = {
            "additional_attributes": [
                {
                    "name": "BF_FID",
                    "file": "exposure/building_footprints/building_footprints.gpkg",
                }
            ]
        }
        fiat_path = builder.static_path / "templates" / "fiat"
        builder.fiat_model.root = fiat_path
        (fiat_path / "exposure/building_footprints").mkdir(parents=True, exist_ok=True)
        (fiat_path / "exposure/building_footprints/building_footprints.gpkg").touch()

        # Act
        footprints = builder.create_footprints()

        # Assert
        expected_path = (
            fiat_path / "exposure/building_footprints/building_footprints.gpkg"
        )
        assert footprints == expected_path.relative_to(builder.static_path)

    def test_create_footprints_from_geometries(self, mock_config: ConfigModel):
        # Arrange
        mock_config.building_footprints = None
        mock_config.fiat_buildings_name = "buildings"

        builder = DatabaseBuilder(mock_config)
        builder.read_template_fiat_model()
        builder.fiat_model = Mock(wraps=builder.fiat_model)
        builder.fiat_model.exposure.exposure_db = pd.DataFrame(columns=["object_id"])
        builder.fiat_model.exposure.exposure_geoms = [
            gpd.GeoDataFrame(
                {
                    "object_id": [1],
                    "geometry": [Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])],
                },
                geometry="geometry",
            )
        ]
        builder.fiat_model.exposure.geom_names = ["buildings"]

        # Act
        footprints = builder.create_footprints()

        # Assert
        assert footprints is None

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
        builder.read_template_fiat_model()
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
        mock_config.aggregation_areas = None
        mock_config.fiat_buildings_name = "buildings"
        builder = DatabaseBuilder(mock_config)
        builder.read_template_fiat_model()
        builder.fiat_model.spatial_joins["aggregation_areas"] = None

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
        mock_config.aggregation_areas = None
        mock_config.fiat_buildings_name = "buildings"
        builder = DatabaseBuilder(mock_config)
        builder.read_template_fiat_model()
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
        builder.read_template_fiat_model()
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
        builder.read_template_fiat_model()
        del builder.fiat_model.exposure.exposure_db["SVI"]
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
        assert "SVI" in builder.fiat_model.exposure.exposure_db.columns
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
        builder.read_template_sfincs_offshore_model()

        # Assert
        assert not (builder.static_path / "templates" / "offshore").exists()
        assert builder.sfincs_offshore_model is None

    def test_create_sfincs_overland(self, mock_config: ConfigModel):
        # Arrange
        mock_config.sfincs_offshore = None
        builder = DatabaseBuilder(mock_config)
        builder.read_template_sfincs_overland_model()

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
        builder.read_template_sfincs_overland_model()
        builder.read_template_sfincs_offshore_model()

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
        builder.read_template_sfincs_overland_model()
        builder.read_template_sfincs_offshore_model()

        # Act
        sfincs = builder.create_offshore_model()

        # Assert
        assert sfincs is None
        assert not (builder.static_path / "templates" / "offshore").exists()

    def test_create_slr(self, mock_config: ConfigModel):
        # Arrange
        mock_config.slr_scenarios = SlrScenariosModel(
            file=str(self.static_path / "slr/slr.csv"),
            relative_to_year=2020,
        )
        builder = DatabaseBuilder(mock_config)
        builder.make_folder_structure()
        # Act
        slr = builder.create_slr()

        # Assert
        expected_file = (
            builder.static_path
            / "slr_scenarios"
            / Path(mock_config.slr_scenarios.file).name
        )
        expected_slr = SlrScenariosModel(
            file=expected_file.relative_to(builder.static_path).as_posix(),
            relative_to_year=mock_config.slr_scenarios.relative_to_year,
        )
        assert slr == expected_slr
        assert expected_file.exists()

    def test_create_slr_returns_none(self, mock_config: ConfigModel):
        # Arrange
        mock_config.slr_scenarios = None
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

    def test_create_dem_index_created(self, mock_config: ConfigModel):
        # Arrange
        mock_config.dem = DemModel(
            filename=str(self.static_path / "dem/charleston_14m.tif"),
            units=us.UnitTypesLength.meters,
        )
        mock_config.gui = GuiConfigModel(
            max_flood_depth=10.0,
            max_aggr_dmg=1_000_000.0,
            max_footprint_dmg=500_000.0,
            max_benefits=1_000_000.0,
            topobathy_min_max=(-10.0, 10.0),
        )
        builder = DatabaseBuilder(mock_config)
        builder.setup()

        # Act
        dem = builder.create_dem_model()

        # Assert
        expected_tif = builder.static_path / "dem" / Path(mock_config.dem.filename).name
        expected_dem = DemModel(
            filename=expected_tif.name,
            units=mock_config.dem.units,
        )
        expected_indices = builder.static_path / "dem" / "index.tif"

        assert dem == expected_dem

        for file in [
            expected_tif,
            expected_indices,
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
            lat=32.78,
            lon=-79.9233,
            max_distance=us.UnitfulLength(value=100, units=us.UnitTypesLength.miles),
        )
        builder = DatabaseBuilder(mock_config)
        builder.water_level_references = WaterlevelReferenceModel(
            reference="MSL",
            datums=[
                DatumModel(
                    name="MSL",
                    height=us.UnitfulLength(value=0, units=us.UnitTypesLength.meters),
                )
            ],
        )
        # Act
        tide_gauge = builder.create_tide_gauge()

        # Assert
        assert tide_gauge is not None
        assert tide_gauge.source == TideGaugeSource.file
        assert tide_gauge.file is not None
        assert (builder.static_path / tide_gauge.file).exists()

    def test_create_tide_gauge_returns_none(self, mock_config: ConfigModel):
        # Arrange
        mock_config.tide_gauge = None
        builder = DatabaseBuilder(mock_config)

        # Act
        tide_gauge = builder.create_tide_gauge()

        # Assert
        assert tide_gauge is None

    def test_create_tide_gauge_file_is_none_raises(self, mock_config: ConfigModel):
        # Arrange
        mock_config.tide_gauge = TideGaugeConfigModel(
            id=8665530,
            ref="MSL",
            source=TideGaugeSource.file,
            file=None,
            description="Charleston Cooper River Entrance",
            lat=32.78,
            lon=-79.9233,
            max_distance=us.UnitfulLength(value=100, units=us.UnitTypesLength.miles),
        )

        builder = DatabaseBuilder(mock_config)
        builder.water_level_references = WaterlevelReferenceModel(
            reference="MSL",
            datums=[
                DatumModel(
                    name="MSL",
                    height=us.UnitfulLength(value=0, units=us.UnitTypesLength.meters),
                )
            ],
        )

        # Act
        with pytest.raises(ValueError) as excinfo:
            builder.create_tide_gauge()

        # Assert
        assert (
            "Tide gauge file needs to be provided when 'file' is selected as the source."
            in str(excinfo.value)
        )

    def test_create_tide_gauge_file_based_ref_is_none_returns_msl(
        self,
        mock_config: ConfigModel,
        tmp_path: Path,
        dummy_1d_timeseries_df: pd.DataFrame,
    ):
        # Arrange
        tide_gauge_file = tmp_path / "dummy.csv"
        dummy_1d_timeseries_df.to_csv(tide_gauge_file)
        mock_config.tide_gauge = TideGaugeConfigModel(
            id=8665530,
            ref=None,
            source=TideGaugeSource.file,
            file=str(tide_gauge_file),
            description="Charleston Cooper River Entrance",
            lat=32.78,
            lon=-79.9233,
            max_distance=us.UnitfulLength(value=100, units=us.UnitTypesLength.miles),
        )
        builder = DatabaseBuilder(mock_config)
        builder.water_level_references = WaterlevelReferenceModel(
            reference="MSL",
            datums=[
                DatumModel(
                    name="MSL",
                    height=us.UnitfulLength(value=0, units=us.UnitTypesLength.meters),
                )
            ],
        )

        # Act
        tide_gauge = builder.create_tide_gauge()

        # Assert
        assert tide_gauge.reference == "MSL"

    def test_create_tide_gauge_noaa_coops(self, mock_config: ConfigModel):
        # Arrange
        mock_config.tide_gauge = TideGaugeConfigModel(
            id=8665530,
            ref="MSL",
            source=TideGaugeSource.noaa_coops,
            description="Charleston Cooper River Entrance",
            lat=32.78,
            lon=-79.9233,
            max_distance=us.UnitfulLength(value=100, units=us.UnitTypesLength.miles),
        )
        builder = DatabaseBuilder(mock_config)
        builder.water_level_references = WaterlevelReferenceModel(
            reference="MSL",
            datums=[
                DatumModel(
                    name="MSL",
                    height=us.UnitfulLength(value=0, units=us.UnitTypesLength.meters),
                )
            ],
        )
        # Act
        tide_gauge = builder.create_tide_gauge()
        datum_names = [datum.name for datum in builder.water_level_references.datums]
        # Assert
        assert tide_gauge is not None
        assert tide_gauge.reference == "MSL"
        assert "NAVD88" in datum_names
        assert "MSL" in datum_names
        assert "MHHW" in datum_names
        assert "MLLW" in datum_names

    # TODO split tests of infometrics for imperial and metric types!
    def test_create_infometrics_mandatory_only(
        self, mock_config: ConfigModel, mock_aggregation_areas
    ):
        # Arrange
        mock_config.infographics = False
        builder = DatabaseBuilder(mock_config)
        builder.setup()
        builder.create_aggregation_areas = mock_aggregation_areas
        builder._probabilistic_set_name = "test_set"
        # Act
        builder.create_infometrics()

        # Assert
        path_im = builder.root / "static" / "templates" / "infometrics"
        assert path_im.exists()

        # Check that exactly two TOML files are generated with the expected names
        files = list(path_im.glob("*.toml"))
        assert len(files) == 2
        assert {file.name for file in files} == {
            "mandatory_metrics_config_risk.toml",
            "mandatory_metrics_config.toml",
        }

        # Check risk metrics
        file_path = path_im / "mandatory_metrics_config_risk.toml"
        attrs = read_toml(file_path)
        assert attrs["aggregateBy"] == ["aggr_lvl_1", "aggr_lvl_2"]
        assert any(
            query["name"] == "ExpectedAnnualDamages" for query in attrs["queries"]
        )
        assert any("TotalDamageRP" in query["name"] for query in attrs["queries"])

        # Check event metrics
        file_path = path_im / "mandatory_metrics_config.toml"
        attrs = read_toml(file_path)
        assert attrs["aggregateBy"] == ["aggr_lvl_1", "aggr_lvl_2"]
        assert any("TotalDamageEvent" in query["name"] for query in attrs["queries"])

    def test_create_infometrics_with_default_infographics(
        self, mock_config: ConfigModel, mock_aggregation_areas
    ):
        # Arrange
        mock_config.svi = SviConfigModel(
            file=str(self.templates_path / "fiat/svi/CDC_svi_2020.gpkg"),
            field_name="SVI",
            threshold=0.8,
        )
        mock_config.infographics = True
        builder = DatabaseBuilder(mock_config)
        builder.setup()
        builder.create_aggregation_areas = mock_aggregation_areas
        builder._has_roads = True
        builder._probabilistic_set_name = "test_set"
        # Act
        builder.create_infometrics()

        # Assert
        path_im = builder.root / "static" / "templates" / "infometrics"
        assert path_im.exists()

        # Check that exactly two TOML files are generated with the expected names
        files = list(path_im.glob("*.toml"))
        assert len(files) == 5
        assert {file.name for file in files} == {
            "mandatory_metrics_config_risk.toml",
            "mandatory_metrics_config.toml",
            "metrics_additional_risk_configs.toml",
            "infographic_metrics_config.toml",
            "infographic_metrics_config_risk.toml",
        }

        # Check risk metrics
        file_path = path_im / "infographic_metrics_config_risk.toml"
        attrs = read_toml(file_path)
        assert attrs["aggregateBy"] == ["aggr_lvl_1", "aggr_lvl_2"]
        assert any(query["name"] == "LikelyFloodedHomes" for query in attrs["queries"])
        assert any("ImpactedHomes" in query["name"] for query in attrs["queries"])
        assert any("HighSVI" in query["name"] for query in attrs["queries"])
        assert any("LowSVI" in query["name"] for query in attrs["queries"])
        for query in attrs["queries"]:
            if "SVI" in query["name"]:
                assert any(
                    part.startswith("`SVI` < 0.8") or part.startswith("`SVI` >= 0.8")
                    for part in query["filter"].split(" AND ")
                )

        # Check event metrics
        file_path = path_im / "infographic_metrics_config.toml"
        attrs = read_toml(file_path)
        assert attrs["aggregateBy"] == ["aggr_lvl_1", "aggr_lvl_2"]
        assert any("road" in query["name"].lower() for query in attrs["queries"])
        assert any("Residential" in query["name"] for query in attrs["queries"])
        assert any("Commercial" in query["name"] for query in attrs["queries"])
        assert any("LowVulnerability" in query["name"] for query in attrs["queries"])
        assert any("HighVulnerability" in query["name"] for query in attrs["queries"])
        for query in attrs["queries"]:
            if "SVI" in query["name"]:
                assert any(
                    part.startswith("`SVI` < 0.8") or part.startswith("`SVI` >= 0.8")
                    for part in query["filter"].split(" AND ")
                )

    def test_create_infometrics_no_svi(
        self, mock_config: ConfigModel, mock_aggregation_areas
    ):
        # Arrange
        mock_config.svi = None
        mock_config.infographics = True
        builder = DatabaseBuilder(mock_config)
        builder.setup()
        builder.create_aggregation_areas = mock_aggregation_areas
        builder._probabilistic_set_name = "test_set"
        # Act
        builder.create_infometrics()

        # Assert
        path_im = builder.root / "static" / "templates" / "infometrics"
        assert path_im.exists()
        # Check that exactly two TOML files are generated with the expected names
        files = list(path_im.glob("*.toml"))
        assert len(files) == 5
        assert {file.name for file in files} == {
            "mandatory_metrics_config_risk.toml",
            "mandatory_metrics_config.toml",
            "metrics_additional_risk_configs.toml",
            "infographic_metrics_config.toml",
            "infographic_metrics_config_risk.toml",
        }

        # Check risk metrics
        file_path = path_im / "infographic_metrics_config_risk.toml"
        attrs = read_toml(file_path)
        assert attrs["aggregateBy"] == ["aggr_lvl_1", "aggr_lvl_2"]
        assert any(query["name"] == "LikelyFloodedHomes" for query in attrs["queries"])
        assert any("ImpactedHomes" in query["name"] for query in attrs["queries"])
        assert all("SVI" not in query["name"] for query in attrs["queries"])

        # Check event metrics
        file_path = path_im / "infographic_metrics_config.toml"
        attrs = read_toml(file_path)
        assert attrs["aggregateBy"] == ["aggr_lvl_1", "aggr_lvl_2"]
        assert all("road" not in query["name"].lower() for query in attrs["queries"])
        assert any("Residential" in query["name"] for query in attrs["queries"])
        assert any("Commercial" in query["name"] for query in attrs["queries"])
        assert all("Vulnerability" not in query["name"] for query in attrs["queries"])

    def test_create_infometrics_no_roads(
        self, mock_config: ConfigModel, mock_aggregation_areas
    ):
        # Arrange
        mock_config.svi = None
        mock_config.infographics = True
        builder = DatabaseBuilder(mock_config)
        builder.setup()
        builder.create_aggregation_areas = mock_aggregation_areas
        builder._has_roads = False
        builder._probabilistic_set_name = "test_set"
        # Act
        builder.create_infometrics()

        # Assert
        path_im = builder.root / "static" / "templates" / "infometrics"
        assert path_im.exists()
        # Check that exactly two TOML files are generated with the expected names
        files = list(path_im.glob("*.toml"))
        assert len(files) == 5
        assert {file.name for file in files} == {
            "mandatory_metrics_config_risk.toml",
            "mandatory_metrics_config.toml",
            "metrics_additional_risk_configs.toml",
            "infographic_metrics_config.toml",
            "infographic_metrics_config_risk.toml",
        }

        # Check event metrics
        file_path = path_im / "infographic_metrics_config.toml"
        attrs = read_toml(file_path)
        assert all("road" not in query["name"].lower() for query in attrs["queries"])

    def test_create_infometrics_no_risk(
        self, mock_config: ConfigModel, mock_aggregation_areas
    ):
        # Arrange
        mock_config.svi = None
        mock_config.infographics = True
        builder = DatabaseBuilder(mock_config)
        builder.setup()
        builder.create_aggregation_areas = mock_aggregation_areas
        builder._has_roads = False
        builder._probabilistic_set_name = None
        # Act
        builder.create_infometrics()

        # Assert
        path_im = builder.root / "static" / "templates" / "infometrics"
        assert path_im.exists()
        # Check that exactly two TOML files are generated with the expected names
        files = list(path_im.glob("*.toml"))
        assert len(files) == 2
        assert {file.name for file in files} == {
            "mandatory_metrics_config.toml",
            "infographic_metrics_config.toml",
        }

        # Check event metrics
        file_path = path_im / "infographic_metrics_config.toml"
        attrs = read_toml(file_path)
        assert all("road" not in query["name"].lower() for query in attrs["queries"])

    def test_build(self, full_config: ConfigModel):
        # Arrange
        builder = DatabaseBuilder(full_config)

        # Act
        builder.build()

        # Assert
        assert full_config.database_path is not None
        db = Database(
            database_root=Path(full_config.database_path),
            database_name=full_config.name,
        )
        assert db is not None

    @pytest.mark.parametrize(
        "loglevel, expected",
        [(logging.DEBUG, True), (logging.INFO, False), (logging.WARNING, False)],
    )
    def test_debug_timer(
        self, full_config: ConfigModel, caplog, loglevel: int, expected: bool
    ):
        # Arrange
        FloodAdaptLogging(level=loglevel)
        caplog.set_level(loglevel, logger="FloodAdapt")

        # Act
        DatabaseBuilder(full_config)  # __init__ will call create_default_units

        # Assert
        start_logged = any(
            "Started 'create_default_units'" in msg for msg in caplog.messages
        )
        end_logged = any(
            "Finished 'create_default_units' in" in msg and "seconds" in msg
            for msg in caplog.messages
        )

        if expected:
            assert start_logged, "Expected 'Started' message not captured"
            assert end_logged, "Expected 'Finished' message not captured"
        else:
            assert (
                not start_logged
            ), "Unexpected 'Started' message found at this log level"
            assert (
                not end_logged
            ), "Unexpected 'Finished' message found at this log level"

    @pytest.fixture(scope="function")
    def full_config(self):
        db_path = Settings().database_path
        static_path = db_path / "static"
        templates_path = db_path / "static" / "templates"
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdirname:
            config = ConfigModel(
                #
                # General
                #
                name="test_db",
                database_path=tmpdirname,
                unit_system=UnitSystems.imperial,
                gui=GuiConfigModel(
                    max_flood_depth=5,
                    max_aggr_dmg=1e6,
                    max_footprint_dmg=250000,
                    max_benefits=5e6,
                ),
                infographics=True,
                probabilistic_set=str(db_path / "input" / "events" / "test_set"),
                #
                # SFINCS
                #
                sfincs_overland=FloodModel(
                    name=str(templates_path / "overland"),
                    reference="NAVD88",
                ),
                sfincs_offshore=FloodModel(
                    name=str(templates_path / "offshore"),
                    reference="MSL",
                    vertical_offset=us.UnitfulLength(
                        value=0.33, units=us.UnitTypesLength.feet
                    ),
                ),
                dem=DemModel(
                    filename=str(static_path / "dem/charleston_14m.tif"),
                    units=us.UnitTypesLength.meters,
                ),
                excluded_datums=["NAVD88"],
                slr_scenarios=SlrScenariosModel(
                    file=str(static_path / "slr/slr.csv"),
                    relative_to_year=2020,
                ),
                scs=SCSModel(
                    file=str(static_path / "scs/scs_rainfall.csv"),
                    type=Scstype.type3,
                ),
                tide_gauge=TideGaugeConfigModel(
                    source=TideGaugeSource.noaa_coops,
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
                road_width=us.UnitfulLength(value=5, units=us.UnitTypesLength.meters),
                return_periods=[1, 2, 5, 10, 25, 50, 100],
            )
            yield config

    def test_config_model_raises_when_non_coastal_with_offshore(self):
        db_path = Settings().database_path
        templates_path = db_path / "static" / "templates"

        with pytest.raises(ValidationError) as exc_info:
            ConfigModel(
                name="test_db",
                unit_system=UnitSystems.imperial,
                is_coastal=False,
                gui=GuiConfigModel(
                    max_flood_depth=5,
                    max_aggr_dmg=1e6,
                    max_footprint_dmg=250000,
                    max_benefits=5e6,
                ),
                sfincs_overland=FloodModel(
                    name=str(templates_path / "overland"),
                    reference="NAVD88",
                ),
                sfincs_offshore=FloodModel(
                    name=str(templates_path / "offshore"),
                    reference="MSL",
                ),
                fiat=str(templates_path / "fiat"),
            )

        error_msg = str(exc_info.value)
        assert (
            "When 'is_coastal' is False (thus this is an inland site), 'sfincs_offshore' cannot be provided."
            in error_msg
        )
