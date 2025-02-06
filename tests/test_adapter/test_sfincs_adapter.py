import tempfile
from copy import copy
from datetime import datetime, timedelta
from functools import partial
from pathlib import Path
from typing import Tuple
from unittest import mock

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
import xarray as xr

from flood_adapt.adapter.sfincs_adapter import SfincsAdapter
from flood_adapt.dbs_classes.database import Database
from flood_adapt.dbs_classes.interface.database import IDatabase
from flood_adapt.object_model.hazard.event.synthetic import (
    SyntheticEvent,
    SyntheticEventModel,
)
from flood_adapt.object_model.hazard.forcing.discharge import (
    DischargeConstant,
    DischargeSynthetic,
)
from flood_adapt.object_model.hazard.forcing.rainfall import (
    RainfallConstant,
    RainfallMeteo,
    RainfallNetCDF,
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
    WindCSV,
    WindMeteo,
    WindNetCDF,
    WindSynthetic,
    WindTrack,
)
from flood_adapt.object_model.hazard.interface.forcing import (
    ForcingSource,
    ForcingType,
    IDischarge,
    IForcing,
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
from flood_adapt.object_model.interface.config.sfincs import ObsPointModel, RiverModel
from flood_adapt.object_model.interface.measures import (
    FloodWallModel,
    GreenInfrastructureModel,
    PumpModel,
    SelectionType,
)
from flood_adapt.object_model.interface.scenarios import ScenarioModel
from flood_adapt.object_model.io import unit_system as us
from flood_adapt.object_model.projection import Projection
from flood_adapt.object_model.scenario import Scenario
from tests.fixtures import TEST_DATA_DIR
from tests.test_object_model.test_events.test_forcing.test_netcdf import (
    get_test_dataset,
)


@pytest.fixture()
def default_sfincs_adapter(test_db) -> SfincsAdapter:
    overland_path = test_db.static_path / "templates" / "overland"
    with SfincsAdapter(model_root=overland_path) as adapter:
        start_time = datetime(2023, 1, 1, 0, 0, 0)
        duration = timedelta(hours=3)

        adapter.set_timing(
            TimeModel(
                start_time=start_time,
                end_time=start_time + duration,
                time_step=timedelta(hours=1),
            )
        )
        adapter.ensure_no_existing_forcings()

        return adapter


@pytest.fixture()
def sfincs_adapter_with_dummy_scn(default_sfincs_adapter):
    # Mock scenario to get a rainfall multiplier
    dummy_scn = mock.Mock()
    dummy_event = mock.Mock()
    dummy_event.attrs.rainfall_multiplier = 2
    dummy_scn.event = dummy_event
    default_sfincs_adapter._current_scenario = dummy_scn

    yield default_sfincs_adapter


@pytest.fixture()
def sfincs_adapter_2_rivers(test_db: IDatabase) -> tuple[IDatabase, SfincsAdapter]:
    overland_2_rivers = test_db.static_path / "templates" / "overland_2_rivers"

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
                        value=5000 + i * 100, units=us.UnitTypesDischarge.cms
                    ),
                    x_coordinate=x,
                    y_coordinate=y,
                )
            )
    test_db.site.attrs.sfincs.river = rivers

    with SfincsAdapter(model_root=(overland_2_rivers)) as adapter:
        adapter.set_timing(TimeModel())
        adapter.ensure_no_existing_forcings()

        return adapter, test_db


@pytest.fixture()
def synthetic_discharge():
    if river := Database().site.attrs.sfincs.river:
        return DischargeSynthetic(
            river=river[0],
            timeseries=SyntheticTimeseriesModel[us.UnitfulDischarge](
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
    return Database().site.attrs.sfincs.river[0]


@pytest.fixture()
def synthetic_rainfall():
    return RainfallSynthetic(
        timeseries=SyntheticTimeseriesModel[us.UnitfulIntensity](
            shape_type=ShapeType.triangle,
            duration=us.UnitfulTime(value=3, units=us.UnitTypesTime.hours),
            peak_time=us.UnitfulTime(value=1, units=us.UnitTypesTime.hours),
            peak_value=us.UnitfulIntensity(value=10, units=us.UnitTypesIntensity.mm_hr),
        )
    )


@pytest.fixture()
def synthetic_wind():
    return WindSynthetic(
        magnitude=SyntheticTimeseriesModel[us.UnitfulVelocity](
            shape_type=ShapeType.triangle,
            duration=us.UnitfulTime(value=1, units=us.UnitTypesTime.days),
            peak_time=us.UnitfulTime(value=2, units=us.UnitTypesTime.hours),
            peak_value=us.UnitfulVelocity(value=1, units=us.UnitTypesVelocity.mps),
        ),
        direction=SyntheticTimeseriesModel[us.UnitfulDirection](
            shape_type=ShapeType.triangle,
            duration=us.UnitfulTime(value=1, units=us.UnitTypesTime.days),
            peak_time=us.UnitfulTime(value=2, units=us.UnitTypesTime.hours),
            peak_value=us.UnitfulDirection(
                value=1, units=us.UnitTypesDirection.degrees
            ),
        ),
    )


@pytest.fixture()
def synthetic_waterlevels():
    return WaterlevelSynthetic(
        surge=SurgeModel(
            timeseries=SyntheticTimeseriesModel[us.UnitfulLength](
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


@pytest.fixture()
def test_event_all_synthetic(
    synthetic_discharge,
    synthetic_rainfall,
    synthetic_waterlevels,
):
    return SyntheticEvent(
        SyntheticEventModel(
            name="all_synthetic",
            time=TimeModel(),
            forcings={
                ForcingType.DISCHARGE: [synthetic_discharge],
                ForcingType.RAINFALL: [synthetic_rainfall],
                ForcingType.WATERLEVEL: [synthetic_waterlevels],
            },
        )
    )


@pytest.fixture()
def database_with_synthetic_scenario(test_db, test_event_all_synthetic):
    test_db.events.save(test_event_all_synthetic)

    scn = Scenario(
        ScenarioModel(
            name="synthetic",
            event=test_event_all_synthetic.attrs.name,
            projection="current",
            strategy="no_measures",
        )
    )

    test_db.scenarios.save(scn)
    return test_db, scn


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
    mock_source.capitalize = mock.Mock(return_value="Unsupported_source")

    match type:
        case ForcingType.DISCHARGE:

            class UnsupportedDischarge(IDischarge):
                source: ForcingSource = mock_source
                river: RiverModel = mock.Mock(spec=RiverModel)

            unsupported = UnsupportedDischarge()
        case ForcingType.RAINFALL:

            class UnsupportedRainfall(IRainfall):
                source: ForcingSource = mock_source

            unsupported = UnsupportedRainfall()

        case ForcingType.WATERLEVEL:

            class UnsupportedWaterlevel(IWaterlevel):
                source: ForcingSource = mock_source

            unsupported = UnsupportedWaterlevel()
        case ForcingType.WIND:

            class UnsupportedWind(IWind):
                source: ForcingSource = mock_source

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

        def test_add_forcing_wind_from_netcdf(
            self, test_db: IDatabase, default_sfincs_adapter: SfincsAdapter
        ):
            # Arrange
            path = Path(tempfile.gettempdir()) / "wind_netcdf.nc"

            time = TimeModel(time_step=timedelta(hours=1))
            default_sfincs_adapter.set_timing(time)

            ds = get_test_dataset(
                time=time,
                lat=int(test_db.site.attrs.lat),
                lon=int(test_db.site.attrs.lon),
            )
            ds.to_netcdf(path)
            forcing = WindNetCDF(path=path)

            # Act
            default_sfincs_adapter.add_forcing(forcing)

            # Assert
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

        def test_add_forcing_waterlevels_csv(
            self, default_sfincs_adapter: SfincsAdapter, synthetic_wind: WindSynthetic
        ):
            # Arrange
            tmp_path = Path(tempfile.gettempdir()) / "wind.csv"
            t0, t1 = default_sfincs_adapter._model.get_model_time()
            time_frame = TimeModel(start_time=t0, end_time=t1)
            synthetic_wind.to_dataframe(time_frame).to_csv(tmp_path)

            forcing = WindCSV(path=tmp_path)

            # Act
            default_sfincs_adapter.add_forcing(forcing)

            # Assert
            assert default_sfincs_adapter.wind is not None

        def test_add_forcing_wind_unsupported(
            self, default_sfincs_adapter: SfincsAdapter
        ):
            # Arrange
            assert default_sfincs_adapter.wind is None

            wind = _unsupported_forcing_source(ForcingType.WIND)

            # Act
            default_sfincs_adapter.add_forcing(wind)

            # Assert
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

        def test_add_forcing_rainfall_from_netcdf(
            self, test_db: IDatabase, sfincs_adapter_with_dummy_scn: SfincsAdapter
        ):
            # Arrange
            adapter = sfincs_adapter_with_dummy_scn
            path = Path(tempfile.gettempdir()) / "wind_netcdf.nc"

            time = TimeModel(time_step=timedelta(hours=1))
            adapter.set_timing(time)

            ds = get_test_dataset(
                time=time,
                lat=int(test_db.site.attrs.lat),
                lon=int(test_db.site.attrs.lon),
            )
            ds.to_netcdf(path)
            forcing = RainfallNetCDF(path=path)

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
            assert adapter.rainfall is None

    class TestDischarge:
        def test_add_forcing_discharge_synthetic(
            self, default_sfincs_adapter: SfincsAdapter, synthetic_discharge
        ):
            # Arrange
            default_sfincs_adapter.set_timing(TimeModel())

            # Act
            default_sfincs_adapter.add_forcing(synthetic_discharge)

            # Assert
            assert default_sfincs_adapter.discharge is not None

        def test_add_forcing_discharge_unsupported(
            self, default_sfincs_adapter: SfincsAdapter, test_river
        ):
            # Arrange
            discharge = _unsupported_forcing_source(ForcingType.DISCHARGE)

            # Act
            default_sfincs_adapter.add_forcing(discharge)

            # Assert
            assert default_sfincs_adapter.discharge is None

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
                sfincs_adapter.add_forcing(forcing=forcing)

        def test_set_discharge_forcing_multiple_rivers(
            self,
            sfincs_adapter_2_rivers: tuple[SfincsAdapter, IDatabase],
        ):
            # Arrange
            num_rivers = 2
            sfincs_adapter, db = sfincs_adapter_2_rivers
            assert db.site.attrs.sfincs.river is not None
            assert len(db.site.attrs.sfincs.river) == num_rivers

            for i, river in enumerate(db.site.attrs.sfincs.river):
                discharge = DischargeConstant(
                    river=river,
                    discharge=us.UnitfulDischarge(
                        value=i * 1000, units=us.UnitTypesDischarge.cms
                    ),
                )

                # Act
                sfincs_adapter.add_forcing(forcing=discharge)

            # Assert
            river_locations = sfincs_adapter.discharge.vector.to_gdf()
            river_discharges = sfincs_adapter.discharge.to_dataframe()["dis"]

            for i, river in enumerate(db.site.attrs.sfincs.river):
                assert river_locations.geometry[i].x == river.x_coordinate
                assert river_locations.geometry[i].y == river.y_coordinate
                assert river_discharges[i] == i * 1000

        def test_set_discharge_forcing_matching_rivers(
            self, default_sfincs_adapter: SfincsAdapter, synthetic_discharge
        ):
            # Arrange

            # Act
            dis_before = copy(default_sfincs_adapter.discharge)
            default_sfincs_adapter.add_forcing(synthetic_discharge)
            dis_after = default_sfincs_adapter.discharge

            # Assert
            assert dis_before is None
            assert dis_after is not None

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
            t0, t1 = default_sfincs_adapter._model.get_model_time()
            time_frame = TimeModel(start_time=t0, end_time=t1)
            synthetic_waterlevels.to_dataframe(time_frame).to_csv(tmp_path)

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
            waterlevels = _unsupported_forcing_source(ForcingType.WATERLEVEL)

            # Act
            default_sfincs_adapter.add_forcing(waterlevels)

            # Assert
            assert default_sfincs_adapter.waterlevels is None


class TestAddMeasure:
    """Class to test the add_measure method of the SfincsAdapter class."""

    class TestFloodwall:
        @pytest.fixture()
        def floodwall(self, test_db) -> FloodWall:
            floodwall = FloodWall(
                FloodWallModel(
                    name="test_seawall",
                    description="seawall",
                    selection_type=SelectionType.polyline,
                    elevation=us.UnitfulLength(value=12, units=us.UnitTypesLength.feet),
                    polygon_file=str(TEST_DATA_DIR / "pump.geojson"),
                )
            )

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
            pump = Pump(
                PumpModel(
                    name="test_pump",
                    description="pump",
                    discharge=us.UnitfulDischarge(
                        value=100, units=us.UnitTypesDischarge.cfs
                    ),
                    selection_type=SelectionType.polyline,
                    polygon_file=str(TEST_DATA_DIR / "pump.geojson"),
                )
            )
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
            green_infra = GreenInfrastructure(
                GreenInfrastructureModel(
                    name="test_greeninfra",
                    description="greeninfra",
                    selection_type=SelectionType.polygon,
                    polygon_file=str(TEST_DATA_DIR / "green_infra.geojson"),
                    volume=us.UnitfulVolume(value=1, units=us.UnitTypesVolume.m3),
                    height=us.UnitfulHeight(value=2, units=us.UnitTypesLength.meters),
                    percent_area=0.5,
                )
            )

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
        if test_db.site.attrs.sfincs.obs_point is None:
            test_db.site.attrs.sfincs.obs_point = [
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
            test_db.static_path
            / "templates"
            / test_db.site.attrs.sfincs.config.overland_model
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

        site_points = test_db.site.attrs.sfincs.obs_point
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


@pytest.mark.parametrize(
    "forcing_fixture_name",
    [
        "synthetic_discharge",
        "synthetic_rainfall",
        "synthetic_wind",
        "synthetic_waterlevels",
    ],
)
def test_existing_forcings_in_template_raises(test_db, request, forcing_fixture_name):
    # Arrange
    forcing: IForcing = request.getfixturevalue(forcing_fixture_name)
    assert forcing is not None
    SFINCS_PATH = test_db.static_path / "templates" / "overland"
    COPY_PATH = Path(tempfile.gettempdir()) / "overland_copy" / forcing.type.lower()

    # Ensure template is clean
    adapter = SfincsAdapter(SFINCS_PATH)
    adapter.ensure_no_existing_forcings()

    # Mock scenario to get a rainfall multiplier
    mock_scn = mock.Mock()
    mock_event = mock.Mock()
    mock_event.attrs.rainfall_multiplier = 1.5
    mock_scn.event = mock_event
    adapter._current_scenario = mock_scn

    # Add forcing to the template
    adapter.add_forcing(forcing)
    adapter.write(COPY_PATH)

    # Act
    adapter = SfincsAdapter(COPY_PATH)
    with pytest.raises(ValueError) as e:
        adapter.ensure_no_existing_forcings()

    # Assert
    assert (
        f"{forcing.type.capitalize()} forcing(s) should not exists in the SFINCS template model. Remove it from the SFINCS model located at:"
        in str(e.value)
    )


class TestPostProcessing:
    @pytest.fixture(scope="class")
    def synthetic_rainfall_class(self):
        return RainfallSynthetic(
            timeseries=SyntheticTimeseriesModel[us.UnitfulIntensity](
                shape_type=ShapeType.triangle,
                duration=us.UnitfulTime(value=3, units=us.UnitTypesTime.hours),
                peak_time=us.UnitfulTime(value=1, units=us.UnitTypesTime.hours),
                peak_value=us.UnitfulIntensity(
                    value=10, units=us.UnitTypesIntensity.mm_hr
                ),
            )
        )

    @pytest.fixture(scope="class")
    def synthetic_discharge_class(self):
        if river := Database().site.attrs.sfincs.river:
            return DischargeSynthetic(
                river=river[0],
                timeseries=SyntheticTimeseriesModel[us.UnitfulDischarge](
                    shape_type=ShapeType.triangle,
                    duration=us.UnitfulTime(value=3, units=us.UnitTypesTime.hours),
                    peak_time=us.UnitfulTime(value=1, units=us.UnitTypesTime.hours),
                    peak_value=us.UnitfulDischarge(
                        value=10, units=us.UnitTypesDischarge.cms
                    ),
                ),
            )

    @pytest.fixture(scope="class")
    def synthetic_waterlevels_class(self):
        return WaterlevelSynthetic(
            surge=SurgeModel(
                timeseries=SyntheticTimeseriesModel[us.UnitfulLength](
                    shape_type=ShapeType.triangle,
                    duration=us.UnitfulTime(value=1, units=us.UnitTypesTime.days),
                    peak_time=us.UnitfulTime(value=8, units=us.UnitTypesTime.hours),
                    peak_value=us.UnitfulLength(
                        value=1, units=us.UnitTypesLength.meters
                    ),
                )
            ),
            tide=TideModel(
                harmonic_amplitude=us.UnitfulLength(
                    value=1, units=us.UnitTypesLength.meters
                ),
                harmonic_period=us.UnitfulTime(
                    value=12.42, units=us.UnitTypesTime.hours
                ),
                harmonic_phase=us.UnitfulTime(value=0, units=us.UnitTypesTime.hours),
            ),
        )

    @pytest.fixture(scope="class")
    def test_event_all_synthetic_class(
        self,
        synthetic_discharge_class,
        synthetic_rainfall_class,
        synthetic_waterlevels_class,
    ):
        return SyntheticEvent(
            SyntheticEventModel(
                name="all_synthetic",
                time=TimeModel(),
                forcings={
                    ForcingType.DISCHARGE: [synthetic_discharge_class],
                    ForcingType.RAINFALL: [synthetic_rainfall_class],
                    ForcingType.WATERLEVEL: [synthetic_waterlevels_class],
                },
            )
        )

    @pytest.fixture(scope="class")
    def adapter_preprocess_process_scenario_class(
        self,
        test_db_class: IDatabase,
        test_event_all_synthetic_class,
    ) -> Tuple[SfincsAdapter, Scenario]:
        """
        Prepare the database and SfincsAdapter for the test.

        It will:
            Create and save a synthetic event and scenario in the database.
            Create a SfincsAdapter instance with the overland model.
            Preprocess and process the scenario.

        Followed by running all tests in this class.
        """
        # Prepare database
        event = test_event_all_synthetic_class
        start_time = datetime(2023, 1, 1, 0, 0, 0)
        duration = timedelta(hours=3)
        time = TimeModel(
            start_time=start_time,
            end_time=start_time + duration,
        )
        event.attrs.time = time
        test_db_class.events.save(event)
        scn = Scenario(
            ScenarioModel(
                name="synthetic",
                event=event.attrs.name,
                projection="current",
                strategy="no_measures",
            )
        )
        test_db_class.scenarios.save(scn)

        # Prepare adapter
        overland_path = (
            test_db_class.static.get_overland_sfincs_model().get_model_root()
        )
        with SfincsAdapter(model_root=overland_path) as adapter:
            adapter.ensure_no_existing_forcings()

            adapter.preprocess(scn)
            adapter.process(scn)
            yield adapter, scn

    def test_write_geotiff(
        self,
        adapter_preprocess_process_scenario_class: Tuple[SfincsAdapter, Scenario],
    ):
        # Arrange
        adapter, scn = adapter_preprocess_process_scenario_class
        floodmap_path = adapter._get_result_path(scn) / f"FloodMap_{scn.attrs.name}.tif"

        # Act
        adapter.write_floodmap_geotiff(scenario=scn)

        # Assert
        assert floodmap_path.exists()
