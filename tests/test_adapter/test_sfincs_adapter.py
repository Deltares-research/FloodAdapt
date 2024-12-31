import tempfile
from datetime import datetime, timedelta
from functools import partial
from pathlib import Path
from unittest import mock

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
import xarray as xr

from flood_adapt.adapter.sfincs_adapter import SfincsAdapter
from flood_adapt.dbs_classes.database import Database
from flood_adapt.dbs_classes.interface.database import IDatabase
from flood_adapt.object_model.hazard.forcing.discharge import (
    DischargeConstant,
    DischargeSynthetic,
)
from flood_adapt.object_model.hazard.forcing.plotting import get_waterlevel_df
from flood_adapt.object_model.hazard.forcing.rainfall import (
    RainfallConstant,
    RainfallMeteo,
    RainfallSynthetic,
)
from flood_adapt.object_model.hazard.forcing.waterlevels import (
    SurgeModel,
    TideModel,
    WaterlevelCSV,
    WaterlevelGauged,
    WaterlevelModel,
    WaterlevelSynthetic,
)
from flood_adapt.object_model.hazard.forcing.wind import (
    WindConstant,
    WindMeteo,
    WindSynthetic,
    WindTrack,
)
from flood_adapt.object_model.hazard.interface.forcing import (
    ForcingSource,
    ForcingType,
    IDischarge,
    IRainfall,
    IWaterlevel,
    IWind,
)
from flood_adapt.object_model.hazard.interface.models import (
    TimeModel,
)
from flood_adapt.object_model.hazard.interface.timeseries import (
    ShapeType,
    SyntheticTimeseriesModel,
)
from flood_adapt.object_model.hazard.measure.floodwall import FloodWall
from flood_adapt.object_model.hazard.measure.green_infrastructure import (
    GreenInfrastructure,
)
from flood_adapt.object_model.hazard.measure.pump import Pump
from flood_adapt.object_model.interface.measures import MeasureType
from flood_adapt.object_model.interface.site import ObsPointModel, RiverModel
from flood_adapt.object_model.io import unit_system as us
from flood_adapt.object_model.projection import Projection
from tests.fixtures import TEST_DATA_DIR


@pytest.fixture()
def default_sfincs_adapter(test_db) -> SfincsAdapter:
    overland_path = test_db.static_path / "templates" / "overland"
    with SfincsAdapter(model_root=overland_path) as adapter:
        start_time = datetime(2023, 1, 1, 0, 0, 0)
        duration = timedelta(hours=3)

        adapter.set_timing(
            TimeModel(start_time=start_time, end_time=start_time + duration)
        )
        adapter.logger = mock.Mock()
        adapter.logger.handlers = []
        adapter.logger.warning = mock.Mock()

        # make sure model is as expected
        # ? is it correct that the template model has waterlevels?
        assert adapter.waterlevels is not None, "Waterlevels should not be empty"

        # ? is it correct that the template model has discharge?
        assert adapter.discharge is not None, "Discharge should not be empty"

        assert not adapter.rainfall, "Rainfall should be empty"
        assert not adapter.wind, "Wind should be empty"

        return adapter


@pytest.fixture()
def sfincs_adapter_with_dummy_scn(default_sfincs_adapter):
    dummy_scn = mock.Mock()
    dummy_event = mock.Mock()
    dummy_event.attrs.rainfall_multiplier = 2
    dummy_scn.event = dummy_event
    default_sfincs_adapter._current_scenario = dummy_scn

    yield default_sfincs_adapter


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

    with SfincsAdapter(model_root=(overland_2_rivers)) as adapter:
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


def _mock_meteohandler_read(
    time: TimeModel,
    test_db: IDatabase,
    *args,
    **kwargs,
) -> xr.Dataset | xr.DataArray:
    gen = np.random.default_rng(42)
    lat = [test_db.site.attrs.lat - 10, test_db.site.attrs.lat + 10]
    lon = [test_db.site.attrs.lon - 10, test_db.site.attrs.lon + 10]
    _time = pd.date_range(
        start=time.start_time,
        end=time.end_time,
        freq=timedelta(hours=1),
        name="time",
    )

    ds = xr.Dataset(
        data_vars={
            "wind10_u": (("time", "lat", "lon"), gen.random((len(_time), 2, 2))),
            "wind10_v": (("time", "lat", "lon"), gen.random((len(_time), 2, 2))),
            "press_msl": (("time", "lat", "lon"), gen.random((len(_time), 2, 2))),
            "precip": (("time", "lat", "lon"), gen.random((len(_time), 2, 2))),
        },
        coords={
            "lat": lat,
            "lon": lon,
            "time": _time,
        },
        attrs={
            "crs": 4326,
        },
    )
    ds.raster.set_crs(4326)

    # Convert the longitude to -180 to 180 to match hydromt-sfincs
    if ds["lon"].min() > 180:
        ds["lon"] = ds["lon"] - 360

    return ds


@pytest.fixture()
def mock_meteohandler_read(test_db):
    with mock.patch(
        "flood_adapt.adapter.sfincs_adapter.MeteoHandler.read",
        side_effect=partial(_mock_meteohandler_read, test_db=test_db),
    ):
        yield


@pytest.fixture()
def mock_offshorehandler_get_resulting_waterlevels():
    with mock.patch(
        "flood_adapt.adapter.sfincs_offshore.OffshoreSfincsHandler.get_resulting_waterlevels"
    ) as mock_get_data_wl_from_model:
        df = pd.DataFrame(
            data={"waterlevel": [1, 2, 3]},
            index=pd.date_range("2023-01-01", periods=3, freq="H"),
        )
        mock_get_data_wl_from_model.return_value = df
        yield df


def _unsupported_forcing_source(type: ForcingType):
    mock_source: ForcingSource = mock.Mock(
        spec=(ForcingSource, str), return_value="unsupported_source"
    )
    mock_source.lower = mock.Mock(return_value="unsupported_source")

    match type:
        case ForcingType.DISCHARGE:

            class UnsupportedDischarge(IDischarge):
                source: ForcingSource = mock_source
                river: RiverModel = mock.Mock(spec=RiverModel)

                @classmethod
                def default(cls) -> "UnsupportedDischarge":
                    return UnsupportedDischarge()

            unsupported = UnsupportedDischarge()
        case ForcingType.RAINFALL:

            class UnsupportedRainfall(IRainfall):
                source: ForcingSource = mock_source

                @classmethod
                def default(cls) -> "UnsupportedRainfall":
                    return UnsupportedRainfall()

            unsupported = UnsupportedRainfall()

        case ForcingType.WATERLEVEL:

            class UnsupportedWaterlevel(IWaterlevel):
                source: ForcingSource = mock_source

                @classmethod
                def default(cls) -> "UnsupportedWaterlevel":
                    return UnsupportedWaterlevel()

            unsupported = UnsupportedWaterlevel()
        case ForcingType.WIND:

            class UnsupportedWind(IWind):
                source: ForcingSource = mock_source

                @classmethod
                def default(cls) -> "UnsupportedWind":
                    return UnsupportedWind()

            unsupported = UnsupportedWind()
        case _:
            raise ValueError(f"Unsupported forcing type: {type}")
    return unsupported


class TestAddForcing:
    """Class to test the add_forcing method of the SfincsAdapter class."""

    class TestWind:
        def test_add_forcing_wind_constant(self, default_sfincs_adapter: SfincsAdapter):
            forcing = WindConstant(
                speed=us.UnitfulVelocity(value=10, units=us.UnitTypesVelocity.mps),
                direction=us.UnitfulDirection(
                    value=20, units=us.UnitTypesDirection.degrees
                ),
            )

            assert default_sfincs_adapter.wind is None

            default_sfincs_adapter.add_forcing(forcing)

            assert default_sfincs_adapter.wind is not None
            assert (
                default_sfincs_adapter.wind.to_numpy()
                == [
                    forcing.speed.convert(us.UnitTypesVelocity.mps),
                    forcing.direction.convert(us.UnitTypesDirection.degrees),
                ]
            ).all()

        def test_add_forcing_wind_synthetic(
            self, default_sfincs_adapter: SfincsAdapter, synthetic_wind
        ):
            # Arrange
            assert default_sfincs_adapter.wind is None

            # Act
            default_sfincs_adapter.add_forcing(synthetic_wind)

            # Assert
            assert default_sfincs_adapter.wind is not None

        def test_add_forcing_wind_from_meteo(
            self, mock_meteohandler_read, default_sfincs_adapter: SfincsAdapter
        ):
            assert default_sfincs_adapter.wind is None

            forcing = WindMeteo()

            default_sfincs_adapter.add_forcing(forcing)

            assert default_sfincs_adapter.wind is not None

        def test_add_forcing_wind_from_track(
            self, test_db, tmp_path, default_sfincs_adapter: SfincsAdapter
        ):
            from cht_cyclones.tropical_cyclone import TropicalCyclone

            assert default_sfincs_adapter.wind is None

            # Arrange
            track_file = TEST_DATA_DIR / "IAN.cyc"
            spw_file = tmp_path / "IAN.spw"
            default_sfincs_adapter._sim_path = tmp_path / "sim_path"

            tc = TropicalCyclone()
            tc.read_track(track_file, fmt="ddb_cyc")
            tc.to_spiderweb(spw_file)

            forcing = WindTrack(path=spw_file)

            # Act
            default_sfincs_adapter.add_forcing(forcing)

            # Assert
            assert default_sfincs_adapter.wind is None
            assert default_sfincs_adapter._model.config.get("spwfile") == spw_file.name

        def test_add_forcing_wind_unsupported(
            self, default_sfincs_adapter: SfincsAdapter
        ):
            # Arrange
            assert default_sfincs_adapter.wind is None

            wind = _unsupported_forcing_source(ForcingType.WIND)

            # Act
            default_sfincs_adapter.add_forcing(wind)

            # Assert
            default_sfincs_adapter.logger.warning.assert_called_once_with(
                f"Unsupported wind forcing type: {wind.__class__.__name__}"
            )
            assert default_sfincs_adapter.wind is None

    class TestRainfall:
        def test_add_forcing_constant(
            self, sfincs_adapter_with_dummy_scn: SfincsAdapter
        ):
            # Arrange
            adapter = sfincs_adapter_with_dummy_scn
            assert adapter.rainfall is None

            forcing = RainfallConstant(
                intensity=us.UnitfulIntensity(
                    value=10, units=us.UnitTypesIntensity.mm_hr
                )
            )
            # Act
            adapter.add_forcing(forcing)

            # Assert
            assert adapter.rainfall is not None
            assert (
                adapter.rainfall.to_numpy()
                == [forcing.intensity.convert(us.UnitTypesIntensity.mm_hr)]
            ).all() is not None

        def test_add_forcing_synthetic(
            self, sfincs_adapter_with_dummy_scn: SfincsAdapter, synthetic_rainfall
        ):
            # Arrange
            adapter = sfincs_adapter_with_dummy_scn
            assert adapter.rainfall is None

            # Act
            adapter.add_forcing(synthetic_rainfall)

            # Assert
            assert adapter.rainfall is not None

        def test_add_forcing_from_meteo(
            self,
            mock_meteohandler_read,
            sfincs_adapter_with_dummy_scn: SfincsAdapter,
        ):
            # Arrange
            adapter = sfincs_adapter_with_dummy_scn
            assert adapter.rainfall is None
            forcing = RainfallMeteo()

            # Act
            adapter.add_forcing(forcing)

            # Assert
            assert adapter.rainfall is not None

        def test_add_forcing_unsupported(
            self, sfincs_adapter_with_dummy_scn: SfincsAdapter
        ):
            # Arrange
            adapter = sfincs_adapter_with_dummy_scn
            assert adapter.rainfall is None
            rainfall = _unsupported_forcing_source(ForcingType.RAINFALL)

            # Act
            adapter.add_forcing(rainfall)

            # Assert
            adapter.logger.warning.assert_called_once_with(
                f"Unsupported rainfall forcing type: {rainfall.__class__.__name__}"
            )
            assert adapter.rainfall is None

    class TestDischarge:
        def test_add_forcing_discharge_synthetic(
            self, default_sfincs_adapter: SfincsAdapter, synthetic_discharge
        ):
            # Arrange
            default_sfincs_adapter.set_timing(TimeModel())

            # Act
            dis_before = default_sfincs_adapter.discharge.copy()
            default_sfincs_adapter.add_forcing(synthetic_discharge)
            dis_after = default_sfincs_adapter.discharge

            # Assert
            assert dis_before is not None
            assert dis_after is not None
            assert not dis_before.equals(dis_after)

        def test_add_forcing_discharge_unsupported(
            self, default_sfincs_adapter: SfincsAdapter, test_river
        ):
            # Arrange
            default_sfincs_adapter.logger.warning = mock.Mock()
            discharge = _unsupported_forcing_source(ForcingType.DISCHARGE)

            # Act
            dis_before = default_sfincs_adapter.discharge.copy()
            default_sfincs_adapter.add_forcing(discharge)
            dis_after = default_sfincs_adapter.discharge

            # Assert
            default_sfincs_adapter.logger.warning.assert_called_once_with(
                f"Unsupported discharge forcing type: {discharge.__class__.__name__}"
            )
            assert dis_before.equals(dis_after)

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
            river_locations = sfincs_adapter.discharge.vector.to_gdf()
            river_discharges = sfincs_adapter.discharge.to_dataframe()["dis"]

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
            dis_before = default_sfincs_adapter.discharge.copy()
            default_sfincs_adapter.add_forcing(synthetic_discharge)
            dis_after = default_sfincs_adapter.discharge

            # Assert
            assert not dis_before.equals(dis_after)

        def test_set_discharge_forcing_mismatched_coordinates(
            self, test_db, synthetic_discharge, default_sfincs_adapter: SfincsAdapter
        ):
            # Arrange
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

            # Act
            # Assert
            with pytest.raises(ValueError, match=expected_message):
                sfincs_adapter.add_forcing(synthetic_discharge)

    class TestWaterLevel:
        def test_add_forcing_waterlevels_csv(
            self, default_sfincs_adapter: SfincsAdapter, synthetic_waterlevels
        ):
            # Arrange
            tmp_path = Path(tempfile.gettempdir()) / "waterlevels.csv"
            get_waterlevel_df(synthetic_waterlevels, time_frame=TimeModel()).to_csv(
                tmp_path
            )

            forcing = WaterlevelCSV(path=tmp_path)

            # Act
            default_sfincs_adapter.add_forcing(forcing)

            # Assert
            assert default_sfincs_adapter.waterlevels is not None

        def test_add_forcing_waterlevels_synthetic(
            self, default_sfincs_adapter: SfincsAdapter, synthetic_waterlevels
        ):
            # Arrange
            # Act
            default_sfincs_adapter.add_forcing(synthetic_waterlevels)

            # Assert
            assert default_sfincs_adapter.waterlevels is not None

        def test_add_forcing_waterlevels_gauged(
            self, default_sfincs_adapter: SfincsAdapter
        ):
            # Arrange
            forcing = WaterlevelGauged()

            # Act
            default_sfincs_adapter.add_forcing(forcing)

            # Assert
            assert default_sfincs_adapter.waterlevels is not None

        def test_add_forcing_waterlevels_model(
            self,
            mock_offshorehandler_get_resulting_waterlevels,
            default_sfincs_adapter: SfincsAdapter,
        ):
            # Arrange
            default_sfincs_adapter._turn_off_bnd_press_correction = mock.Mock()
            default_sfincs_adapter._current_scenario = mock.Mock()
            forcing = WaterlevelModel()

            # Act
            default_sfincs_adapter.add_forcing(forcing)

            # Assert
            current_wl = default_sfincs_adapter.waterlevels.to_numpy()[:, 0]
            expected_wl = mock_offshorehandler_get_resulting_waterlevels.to_numpy()[
                :, 0
            ]

            assert all(current_wl == expected_wl)
            default_sfincs_adapter._turn_off_bnd_press_correction.assert_called_once()

        def test_add_forcing_waterlevels_unsupported(
            self, default_sfincs_adapter: SfincsAdapter
        ):
            # Arrange
            default_sfincs_adapter.logger.warning = mock.Mock()

            waterlevels = _unsupported_forcing_source(ForcingType.WATERLEVEL)

            # Act
            default_sfincs_adapter.add_forcing(waterlevels)

            # Assert
            default_sfincs_adapter.logger.warning.assert_called_once_with(
                f"Unsupported waterlevel forcing type: {waterlevels.__class__.__name__}"
            )


class TestAddMeasure:
    """Class to test the add_measure method of the SfincsAdapter class."""

    class TestFloodwall:
        @pytest.fixture()
        def floodwall(self, test_db) -> FloodWall:
            data = {
                "name": "test_seawall",
                "description": "seawall",
                "type": MeasureType.floodwall.value,
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
            # Arrange

            # Act
            default_sfincs_adapter.add_measure(floodwall)

            # Assert

    class TestPump:
        @pytest.fixture()
        def pump(self, test_db) -> Pump:
            data = {
                "name": "test_pump",
                "description": "pump",
                "type": MeasureType.pump,
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
            # Arrange

            # Act
            default_sfincs_adapter.add_measure(pump)

            # Assert

    class TestGreenInfrastructure:
        @pytest.fixture()
        def water_square(self, test_db) -> GreenInfrastructure:
            data = {
                "name": "test_greeninfra",
                "description": "greeninfra",
                "type": MeasureType.water_square,
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
            # Arrange

            # Act
            default_sfincs_adapter._add_measure_greeninfra(water_square)

            # Assert


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

        wl_df_expected = adapter.waterlevels + slr.convert(us.UnitTypesLength.meters)

        # Act
        adapter.add_projection(dummy_projection)

        # Assert
        assert wl_df_expected.equals(adapter.waterlevels)

    def test_add_rainfall_multiplier(
        self, default_sfincs_adapter: SfincsAdapter, dummy_projection: Projection
    ):
        # Arrange
        adapter = default_sfincs_adapter
        rainfall = RainfallConstant(
            intensity=us.UnitfulIntensity(value=10, units=us.UnitTypesIntensity.mm_hr)
        )

        adapter.add_forcing(rainfall)
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
                ObsPointModel(
                    name="obs1",
                    description="Ashley River - James Island Expy",
                    lat=32.7765,
                    lon=-79.9543,
                )
            ]

        # Arrange
        scenario_name = "current_extreme12ft_no_measures"
        path_in = (
            test_db.static_path / "templates" / test_db.site.attrs.sfincs.overland_model
        )

        # Act
        with SfincsAdapter(model_root=path_in) as model:
            model.add_obs_points()
            # write sfincs model in output destination
            new_model_dir = (
                test_db.scenarios.output_path / scenario_name / "sfincs_model_obs_test"
            )
            model.write(path_out=new_model_dir)

        # Assert
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
