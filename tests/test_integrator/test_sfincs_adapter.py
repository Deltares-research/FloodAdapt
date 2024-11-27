import tempfile
from pathlib import Path
from unittest import mock

import geopandas as gpd
import pandas as pd
import pytest
from adapter.sfincs_adapter import SfincsAdapter
from dbs_classes.database import Database
from dbs_classes.interface.database import IDatabase
from object_model.hazard.event.forcing.discharge import (
    DischargeConstant,
    DischargeSynthetic,
)
from object_model.hazard.event.forcing.rainfall import (
    RainfallConstant,
    RainfallMeteo,
    RainfallSynthetic,
)
from object_model.hazard.event.forcing.waterlevels import (
    SurgeModel,
    TideModel,
    WaterlevelCSV,
    WaterlevelGauged,
    WaterlevelModel,
    WaterlevelSynthetic,
)
from object_model.hazard.event.forcing.wind import (
    WindConstant,
    WindMeteo,
    WindSynthetic,
    WindTrack,
)
from object_model.hazard.interface.forcing import (
    IDischarge,
    IForcing,
    IRainfall,
    IWaterlevel,
    IWind,
)
from object_model.hazard.interface.models import TimeModel
from object_model.hazard.interface.timeseries import (
    ShapeType,
    SyntheticTimeseriesModel,
)
from object_model.hazard.measure.floodwall import FloodWall
from object_model.hazard.measure.green_infrastructure import (
    GreenInfrastructure,
)
from object_model.hazard.measure.pump import Pump
from object_model.interface.measures import HazardType, IMeasure
from object_model.interface.site import Obs_pointModel, RiverModel
from object_model.io import unit_system as us
from object_model.projection import Projection

from tests.fixtures import TEST_DATA_DIR


@pytest.fixture()
def default_sfincs_adapter(test_db) -> SfincsAdapter:
    overland_path = test_db.static_path / "templates" / "overland"
    adapter = SfincsAdapter(model_root=overland_path)
    adapter.set_timing(TimeModel())
    adapter._logger = mock.Mock()
    adapter.logger.handlers = []
    adapter.logger.warning = mock.Mock()

    return adapter


@pytest.fixture()
def sfincs_adapter_2_rivers(test_db: IDatabase) -> tuple[IDatabase, SfincsAdapter]:
    overland_2_rivers = test_db.static_path / "templates" / "overland_2_rivers"
    with open(overland_2_rivers / "sfincs.dis", "r") as f:
        l = f.readline()
        timestep, discharges = l.split("\t")
        discharges = [float(d) for d in discharges.split()]

    rivers = []
    with open(overland_2_rivers / "sfincs.src", "r") as f:
        lines = f.readlines()
        for i, line in enumerate(lines):
            x, y = line.split()
            x = float(x)
            y = float(y)
            rivers.append(
                RiverModel(
                    name=f"river_{x}_{y}",
                    mean_discharge=us.UnitfulDischarge(
                        value=discharges[i], units=us.UnitTypesDischarge.cms
                    ),
                    x_coordinate=x,
                    y_coordinate=y,
                )
            )
    test_db.site.attrs.river = rivers
    adapter = SfincsAdapter(model_root=str(overland_2_rivers))
    adapter.set_timing(TimeModel())
    adapter._logger = mock.Mock()
    adapter.logger.handlers = []
    adapter.logger.warning = mock.Mock()

    return adapter, test_db


@pytest.fixture()
def synthetic_discharge():
    if river := Database().site.attrs.river:
        return DischargeSynthetic(
            river=river[0],
            timeseries=SyntheticTimeseriesModel(
                shape_type=ShapeType.triangle,
                duration=us.UnitfulTime(value=3, units=us.UnitTypesTime.hours),
                peak_time=us.UnitfulTime(value=1, units=us.UnitTypesTime.hours),
                peak_value=us.UnitfulDischarge(
                    value=10, units=us.UnitTypesDischarge.cms
                ),
            ),
        )


@pytest.fixture()
def test_river() -> RiverModel:
    return RiverModel(
        name="test_river",
        mean_discharge=us.UnitfulDischarge(value=0, units=us.UnitTypesDischarge.cms),
        x_coordinate=0,
        y_coordinate=0,
    )


@pytest.fixture()
def river_in_db() -> RiverModel:
    return Database().site.attrs.river[0]


@pytest.fixture()
def synthetic_rainfall():
    return RainfallSynthetic(
        timeseries=SyntheticTimeseriesModel(
            shape_type=ShapeType.triangle,
            duration=us.UnitfulTime(value=3, units=us.UnitTypesTime.hours),
            peak_time=us.UnitfulTime(value=1, units=us.UnitTypesTime.hours),
            peak_value=us.UnitfulIntensity(value=10, units=us.UnitTypesIntensity.mm_hr),
        )
    )


@pytest.fixture()
def synthetic_wind():
    return WindSynthetic(
        magnitude=SyntheticTimeseriesModel(
            shape_type=ShapeType.triangle,
            duration=us.UnitfulTime(value=1, units=us.UnitTypesTime.days),
            peak_time=us.UnitfulTime(value=2, units=us.UnitTypesTime.hours),
            peak_value=us.UnitfulVelocity(value=1, units=us.UnitTypesVelocity.mps),
        ),
        direction=SyntheticTimeseriesModel(
            shape_type=ShapeType.triangle,
            duration=us.UnitfulTime(value=1, units=us.UnitTypesTime.days),
            peak_time=us.UnitfulTime(value=2, units=us.UnitTypesTime.hours),
            peak_value=us.UnitfulVelocity(value=1, units=us.UnitTypesVelocity.mps),
        ),
    )


@pytest.fixture()
def synthetic_waterlevels():
    return WaterlevelSynthetic(
        surge=SurgeModel(
            timeseries=SyntheticTimeseriesModel(
                shape_type=ShapeType.triangle,
                duration=us.UnitfulTime(value=1, units=us.UnitTypesTime.days),
                peak_time=us.UnitfulTime(value=8, units=us.UnitTypesTime.hours),
                peak_value=us.UnitfulLength(value=1, units=us.UnitTypesLength.meters),
            )
        ),
        tide=TideModel(
            harmonic_amplitude=us.UnitfulLength(
                value=1, units=us.UnitTypesLength.meters
            ),
            harmonic_period=us.UnitfulTime(value=12.42, units=us.UnitTypesTime.hours),
            harmonic_phase=us.UnitfulTime(value=0, units=us.UnitTypesTime.hours),
        ),
    )


class TestAddForcing:
    """
    Class to test the add_forcing method of the SfincsAdapter class.

    Since the add_forcing method is a dispatcher method, we will test the different cases of forcing types, while mocking the specific methods that handle each forcing type.
    To validate that hydromt_sfincs accepts the data that is returned by the forcing, the mocked methods should be tested separately.
    """

    class TestDispatch:
        @pytest.fixture()
        def sfincs_adapter(self, default_sfincs_adapter) -> SfincsAdapter:
            adapter = default_sfincs_adapter
            adapter._add_forcing_wind = mock.Mock()
            adapter._add_forcing_rain = mock.Mock()
            adapter._add_forcing_discharge = mock.Mock()
            adapter._add_forcing_waterlevels = mock.Mock()
            return adapter

        def test_add_forcing_wind(self, sfincs_adapter):
            forcing = mock.Mock(spec=IWind)

            sfincs_adapter.add_forcing(forcing)
            sfincs_adapter._add_forcing_wind.assert_called_once_with(forcing)

        def test_add_forcing_rain(self, sfincs_adapter: SfincsAdapter):
            forcing = mock.Mock(spec=IRainfall)

            sfincs_adapter.add_forcing(forcing)
            sfincs_adapter._add_forcing_rain.assert_called_once_with(forcing)

        def test_add_forcing_discharge(self, sfincs_adapter: SfincsAdapter):
            forcing = mock.Mock(spec=IDischarge)

            sfincs_adapter.add_forcing(forcing)
            sfincs_adapter._add_forcing_discharge.assert_called_once_with(forcing)

        def test_add_forcing_waterlevels(self, sfincs_adapter: SfincsAdapter):
            forcing = mock.Mock(spec=IWaterlevel)

            sfincs_adapter.add_forcing(forcing)
            sfincs_adapter._add_forcing_waterlevels.assert_called_once_with(forcing)

        def test_add_forcing_unsupported(self, sfincs_adapter: SfincsAdapter):
            forcing = mock.Mock(spec=IForcing)
            forcing._type = "unsupported_type"
            sfincs_adapter.add_forcing(forcing)
            sfincs_adapter.logger.warning.assert_called_once_with(
                f"Skipping unsupported forcing type {forcing.__class__.__name__}"
            )

    class TestWind:
        def test_add_forcing_wind_constant(self, default_sfincs_adapter: SfincsAdapter):
            forcing = WindConstant(
                speed=us.UnitfulVelocity(value=10, units=us.UnitTypesVelocity.mps),
                direction=us.UnitfulDirection(
                    value=20, units=us.UnitTypesDirection.degrees
                ),
            )
            default_sfincs_adapter._add_forcing_wind(forcing)

        def test_add_forcing_wind_synthetic(
            self, default_sfincs_adapter: SfincsAdapter, synthetic_wind
        ):
            default_sfincs_adapter._add_forcing_wind(synthetic_wind)

        def test_add_forcing_wind_from_meteo(
            self, default_sfincs_adapter: SfincsAdapter
        ):
            forcing = WindMeteo()

            default_sfincs_adapter._add_forcing_wind(forcing)

        def test_add_forcing_wind_from_track(
            self, test_db, tmp_path, default_sfincs_adapter: SfincsAdapter
        ):
            from cht_cyclones.tropical_cyclone import TropicalCyclone

            track_file = TEST_DATA_DIR / "IAN.cyc"
            spw_file = tmp_path / "IAN.spw"
            default_sfincs_adapter._sim_path = tmp_path / "sim_path"

            tc = TropicalCyclone()
            tc.read_track(track_file, fmt="ddb_cyc")
            tc.to_spiderweb(spw_file)

            forcing = WindTrack(path=spw_file)
            default_sfincs_adapter._add_forcing_wind(forcing)

        def test_add_forcing_wind_unsupported(
            self, default_sfincs_adapter: SfincsAdapter
        ):
            class UnsupportedWind(IWind):
                def default():
                    return UnsupportedWind

            forcing = UnsupportedWind()

            default_sfincs_adapter._add_forcing_wind(forcing)

            default_sfincs_adapter.logger.warning.assert_called_once_with(
                f"Unsupported wind forcing type: {forcing.__class__.__name__}"
            )

    class TestRainfall:
        def test_add_forcing_rain_constant(self, default_sfincs_adapter: SfincsAdapter):
            forcing = RainfallConstant(
                intensity=us.UnitfulIntensity(
                    value=10, units=us.UnitTypesIntensity.mm_hr
                )
            )
            default_sfincs_adapter._add_forcing_rain(forcing)

        def test_add_forcing_rain_synthetic(
            self, default_sfincs_adapter: SfincsAdapter, synthetic_rainfall
        ):
            default_sfincs_adapter._add_forcing_rain(synthetic_rainfall)

        def test_add_forcing_rain_from_meteo(
            self, default_sfincs_adapter: SfincsAdapter
        ):
            forcing = RainfallMeteo()

            default_sfincs_adapter._add_forcing_rain(forcing)

        def test_add_forcing_rain_unsupported(
            self, default_sfincs_adapter: SfincsAdapter
        ):
            class UnsupportedRain(IRainfall):
                def default():
                    return UnsupportedRain

            forcing = UnsupportedRain()

            default_sfincs_adapter._add_forcing_rain(forcing)

            default_sfincs_adapter.logger.warning.assert_called_once_with(
                f"Unsupported rainfall forcing type: {forcing.__class__.__name__}"
            )

    class TestDischarge:
        def test_add_forcing_discharge_synthetic(
            self, default_sfincs_adapter: SfincsAdapter, synthetic_discharge
        ):
            # Arrange
            default_sfincs_adapter.set_timing(TimeModel())

            # Act
            default_sfincs_adapter._add_forcing_discharge(synthetic_discharge)

        def test_add_forcing_discharge_unsupported(
            self, default_sfincs_adapter: SfincsAdapter, test_river
        ):
            # Arrange
            sfincs_adapter = default_sfincs_adapter

            class UnsupportedDischarge(IDischarge):
                def default():
                    return UnsupportedDischarge

            sfincs_adapter.logger.warning = mock.Mock()
            forcing = UnsupportedDischarge(river=test_river)

            # Act
            sfincs_adapter._add_forcing_discharge(forcing)

            # Assert
            sfincs_adapter.logger.warning.assert_called_once_with(
                f"Unsupported discharge forcing type: {forcing.__class__.__name__}"
            )

        def test_set_discharge_forcing_incorrect_rivers_raises(
            self,
            default_sfincs_adapter: SfincsAdapter,
        ):
            # Arrange
            sfincs_adapter = default_sfincs_adapter
            forcing = DischargeConstant(
                river=RiverModel(
                    name="test_river",
                    mean_discharge=us.UnitfulDischarge(
                        value=0, units=us.UnitTypesDischarge.cms
                    ),
                    x_coordinate=0,
                    y_coordinate=0,
                ),
                discharge=us.UnitfulDischarge(value=0, units=us.UnitTypesDischarge.cms),
            )

            # Act
            # Assert
            msg = f"River {forcing.river.name} is not defined in the sfincs model. Please ensure the river coordinates in the site.toml match the coordinates for rivers in the SFINCS model."
            with pytest.raises(ValueError, match=msg):
                sfincs_adapter._set_single_river_forcing(discharge=forcing)

        def test_set_discharge_forcing_multiple_rivers(
            self,
            sfincs_adapter_2_rivers: tuple[SfincsAdapter, IDatabase],
        ):
            # Arrange
            num_rivers = 2
            sfincs_adapter, db = sfincs_adapter_2_rivers
            assert db.site.attrs.river is not None
            assert len(db.site.attrs.river) == num_rivers

            for i, river in enumerate(db.site.attrs.river):
                discharge = DischargeConstant(
                    river=river,
                    discharge=us.UnitfulDischarge(
                        value=i * 1000, units=us.UnitTypesDischarge.cms
                    ),
                )

                # Act
                sfincs_adapter._set_single_river_forcing(discharge=discharge)

            # Assert
            river_locations = sfincs_adapter._model.forcing["dis"].vector.to_gdf()
            river_discharges = sfincs_adapter._model.forcing["dis"].to_dataframe()[
                "dis"
            ]

            for i, river in enumerate(db.site.attrs.river):
                assert (
                    river_locations.geometry[i + 1].x == river.x_coordinate
                )  # 1-based indexing for some reason
                assert (
                    river_locations.geometry[i + 1].y == river.y_coordinate
                )  # 1-based indexing for some reason
                assert river_discharges[i] == i * 1000

        def test_set_discharge_forcing_matching_rivers(
            self, default_sfincs_adapter: SfincsAdapter, synthetic_discharge
        ):
            # Arrange

            # Act
            default_sfincs_adapter._add_forcing_discharge(synthetic_discharge)

            # Assert

        def test_set_discharge_forcing_mismatched_coordinates(
            self, test_db, synthetic_discharge, default_sfincs_adapter: SfincsAdapter
        ):
            sfincs_adapter = default_sfincs_adapter
            synthetic_discharge.river = RiverModel(
                name="test_river",
                mean_discharge=us.UnitfulDischarge(
                    value=0, units=us.UnitTypesDischarge.cms
                ),
                x_coordinate=0,
                y_coordinate=0,
            )

            expected_message = r"River .+ is not defined in the sfincs model. Please ensure the river coordinates in the site.toml match the coordinates for rivers in the SFINCS model."

            with pytest.raises(ValueError, match=expected_message):
                sfincs_adapter._add_forcing_discharge(synthetic_discharge)

    class TestWaterLevel:
        def test_add_forcing_waterlevels_csv(
            self, default_sfincs_adapter: SfincsAdapter, synthetic_waterlevels
        ):
            tmp_path = Path(tempfile.gettempdir()) / "waterlevels.csv"
            synthetic_waterlevels.get_data().to_csv(tmp_path)
            forcing = WaterlevelCSV(path=tmp_path)

            default_sfincs_adapter._add_forcing_waterlevels(forcing)

        def test_add_forcing_waterlevels_synthetic(
            self, default_sfincs_adapter: SfincsAdapter, synthetic_waterlevels
        ):
            default_sfincs_adapter._add_forcing_waterlevels(synthetic_waterlevels)

        def test_add_forcing_waterlevels_gauged(
            self, default_sfincs_adapter: SfincsAdapter
        ):
            forcing = WaterlevelGauged()
            default_sfincs_adapter._add_forcing_waterlevels(forcing.get_data())

        def test_add_forcing_waterlevels_model(
            self, default_sfincs_adapter: SfincsAdapter
        ):
            default_sfincs_adapter._turn_off_bnd_press_correction = mock.Mock()
            default_sfincs_adapter._scenario = mock.Mock()

            forcing = mock.Mock(spec=WaterlevelModel)
            dummy_wl = [1, 2, 3]
            forcing.get_data.return_value = pd.DataFrame(
                data={"waterlevel": dummy_wl},
                index=pd.date_range("2023-01-01", periods=len(dummy_wl), freq="D"),
            )

            default_sfincs_adapter._add_forcing_waterlevels(forcing)

            current_wl = default_sfincs_adapter.waterlevels.to_numpy()[:, 0]

            assert all(current_wl == dummy_wl)
            default_sfincs_adapter._turn_off_bnd_press_correction.assert_called_once()

        def test_add_forcing_waterlevels_unsupported(
            self, default_sfincs_adapter: SfincsAdapter
        ):
            default_sfincs_adapter.logger.warning = mock.Mock()

            class UnsupportedWaterLevel(IWaterlevel):
                def default():
                    return UnsupportedWaterLevel

            forcing = UnsupportedWaterLevel()
            default_sfincs_adapter._add_forcing_waterlevels(forcing)

            default_sfincs_adapter.logger.warning.assert_called_once_with(
                f"Unsupported waterlevel forcing type: {forcing.__class__.__name__}"
            )


class TestAddMeasure:
    """Class to test the add_measure method of the SfincsAdapter class."""

    class TestDispatch:
        @pytest.fixture()
        def sfincs_adapter(
            self, default_sfincs_adapter: SfincsAdapter
        ) -> SfincsAdapter:
            adapter = default_sfincs_adapter

            adapter._add_measure_floodwall = mock.Mock()
            adapter._add_measure_greeninfra = mock.Mock()
            adapter._add_measure_pump = mock.Mock()
            adapter.logger.warning = mock.Mock()

            return adapter

        def test_add_measure_pump(self, sfincs_adapter: SfincsAdapter):
            measure = mock.Mock(spec=Pump)
            measure.attrs = mock.Mock()
            measure.attrs.type = HazardType.pump
            sfincs_adapter.add_measure(measure)
            sfincs_adapter._add_measure_pump.assert_called_once_with(measure)

        def test_add_measure_greeninfra(self, sfincs_adapter: SfincsAdapter):
            measure = mock.Mock(spec=GreenInfrastructure)
            measure.attrs = mock.Mock()
            measure.attrs.type = HazardType.greening
            sfincs_adapter.add_measure(measure)
            sfincs_adapter._add_measure_greeninfra.assert_called_once_with(measure)

        def test_add_measure_floodwall(self, sfincs_adapter: SfincsAdapter):
            measure = mock.Mock(spec=FloodWall)
            measure.attrs = mock.Mock()
            measure.attrs.type = HazardType.floodwall
            sfincs_adapter.add_measure(measure)
            sfincs_adapter._add_measure_floodwall.assert_called_once_with(measure)

        def test_add_measure_unsupported(self, sfincs_adapter: SfincsAdapter):
            class UnsupportedMeasure(IMeasure):
                pass

            measure = mock.Mock(spec=UnsupportedMeasure)
            measure.attrs = mock.Mock()
            measure.attrs.type = "UnsupportedMeasure"
            sfincs_adapter.add_measure(measure)
            sfincs_adapter.logger.warning.assert_called_once_with(
                f"Skipping unsupported measure type {measure.__class__.__name__}"
            )

    class TestFloodwall:
        @pytest.fixture()
        def floodwall(self, test_db) -> FloodWall:
            data = {
                "name": "test_seawall",
                "description": "seawall",
                "type": HazardType.floodwall,
                "elevation": us.UnitfulLength(value=12, units=us.UnitTypesLength.feet),
                "selection_type": "polyline",
                "polygon_file": str(TEST_DATA_DIR / "pump.geojson"),
            }
            floodwall = FloodWall.load_dict(data)
            test_db.measures.save(floodwall)
            return floodwall

        def test_add_measure_floodwall(
            self, default_sfincs_adapter: SfincsAdapter, floodwall
        ):
            default_sfincs_adapter._add_measure_floodwall(floodwall)
            # Asserts?

    class TestPump:
        @pytest.fixture()
        def pump(self, test_db) -> Pump:
            data = {
                "name": "test_pump",
                "description": "pump",
                "type": HazardType.pump,
                "discharge": us.UnitfulDischarge(
                    value=100, units=us.UnitTypesDischarge.cfs
                ),
                "selection_type": "polyline",
                "polygon_file": str(TEST_DATA_DIR / "pump.geojson"),
            }
            pump = Pump.load_dict(data)
            test_db.measures.save(pump)
            return pump

        def test_add_measure_pump(self, default_sfincs_adapter: SfincsAdapter, pump):
            # sfincs_adapter._model.setup_drainage_structures = mock.Mock()
            # pump = test_db.measures.get("pump")
            default_sfincs_adapter._add_measure_pump(pump)

    class TestGreenInfrastructure:
        @pytest.fixture()
        def water_square(self, test_db) -> GreenInfrastructure:
            data = {
                "name": "test_greeninfra",
                "description": "greeninfra",
                "type": HazardType.water_square,
                "selection_type": "polygon",
                "polygon_file": str(TEST_DATA_DIR / "green_infra.geojson"),
                "volume": {"value": 1, "units": "m3"},
                "height": {"value": 2, "units": "meters"},
            }

            green_infra = GreenInfrastructure.load_dict(data)
            test_db.measures.save(green_infra)
            return green_infra

        def test_add_measure_greeninfra(
            self, default_sfincs_adapter: SfincsAdapter, water_square
        ):
            default_sfincs_adapter._add_measure_greeninfra(water_square)


class TestAddProjection:
    """Class to test the add_projection method of the SfincsAdapter class."""

    def test_add_slr(
        self, default_sfincs_adapter: SfincsAdapter, dummy_projection: Projection
    ):
        # Arrange
        adapter = default_sfincs_adapter
        adapter._set_waterlevel_forcing(
            pd.DataFrame(
                index=pd.date_range("2023-01-01", periods=3, freq="D"),
                data={"waterlevel": [1.0, 2.0, 3.0]},
            )
        )
        slr = us.UnitfulLength(value=1.0, units=us.UnitTypesLength.meters)
        dummy_projection.attrs.physical_projection.sea_level_rise = slr

        wl_df_before = (
            adapter._model.forcing["bzs"]
            .to_dataframe()["bzs"]
            .groupby("time")
            .mean()
            .to_frame()
        )

        wl_df_expected = wl_df_before.apply(
            lambda x: x + slr.convert(us.UnitTypesLength.meters)
        )

        # Act
        adapter.add_projection(dummy_projection)
        wl_df_after = (
            adapter._model.forcing["bzs"]
            .to_dataframe()["bzs"]
            .groupby("time")
            .mean()
            .to_frame()
        )

        # Assert
        assert wl_df_expected.equals(wl_df_after)

    def test_add_rainfall_multiplier(
        self, default_sfincs_adapter: SfincsAdapter, dummy_projection: Projection
    ):
        # Arrange
        adapter = default_sfincs_adapter
        rainfall = RainfallConstant(
            intensity=us.UnitfulIntensity(value=10, units=us.UnitTypesIntensity.mm_hr)
        )
        adapter._add_forcing_rain(rainfall)
        rainfall_before = adapter._model.forcing["precip"]
        dummy_projection.get_physical_projection().attrs.rainfall_multiplier = 2

        rainfall_expected = (
            rainfall_before
            * dummy_projection.get_physical_projection().attrs.rainfall_multiplier
        )

        # Act
        adapter.add_projection(dummy_projection)
        rainfall_after = adapter._model.forcing["precip"]

        # Assert
        assert rainfall_expected.equals(rainfall_after)


class TestAddObsPoint:
    def test_add_obs_points(self, test_db: IDatabase):
        if test_db.site.attrs.obs_point is None:
            test_db.site.attrs.obs_point = [
                Obs_pointModel(
                    name="obs1",
                    description="Ashley River - James Island Expy",
                    lat=32.7765,
                    lon=-79.9543,
                )
            ]

        scenario_name = "current_extreme12ft_no_measures"
        path_in = (
            test_db.static_path / "templates" / test_db.site.attrs.sfincs.overland_model
        )

        with SfincsAdapter(model_root=path_in) as model:
            model.add_obs_points()
            # write sfincs model in output destination
            new_model_dir = (
                test_db.scenarios.output_path / scenario_name / "sfincs_model_obs_test"
            )
            model.write(path_out=new_model_dir)

        # assert points are the same
        sfincs_obs = pd.read_csv(
            new_model_dir.joinpath("sfincs.obs"),
            header=None,
            delim_whitespace=True,
        )

        names = []
        lat = []
        lon = []

        site_points = test_db.site.attrs.obs_point
        for pt in site_points:
            names.append(pt.name)
            lat.append(pt.lat)
            lon.append(pt.lon)
        df = pd.DataFrame({"Name": names, "Latitude": lat, "Longitude": lon})
        gdf = gpd.GeoDataFrame(
            df, geometry=gpd.points_from_xy(df.Longitude, df.Latitude), crs="EPSG:4326"
        )
        site_obs = gdf.drop(columns=["Longitude", "Latitude"]).to_crs(epsg=26917)

        assert len(sfincs_obs) == len(site_obs)
        for i in range(len(site_obs)):
            pytest.approx(sfincs_obs.loc[i, 0], site_obs.loc[i].geometry.x, abs=1)
            pytest.approx(sfincs_obs.loc[i, 1], site_obs.loc[i].geometry.y, abs=1)
