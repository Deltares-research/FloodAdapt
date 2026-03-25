import tempfile
from copy import copy
from datetime import datetime, timedelta
from functools import partial
from pathlib import Path
from unittest import mock

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
import xarray as xr
from cht_cyclones.tropical_cyclone import TropicalCyclone
from shapely.geometry import Polygon
from shapely.ops import unary_union

from flood_adapt.adapter.sfincs_adapter import SfincsAdapter
from flood_adapt.config.hazard import (
    DatumModel,
    FloodModel,
    ObsPointModel,
    RiverModel,
    WaterlevelReferenceModel,
)
from flood_adapt.dbs_classes.database import Database
from flood_adapt.dbs_classes.interface.database import IDatabase
from flood_adapt.objects.events.hurricane import TranslationModel
from flood_adapt.objects.events.synthetic import (
    SyntheticEvent,
)
from flood_adapt.objects.forcing import unit_system as us
from flood_adapt.objects.forcing.discharge import (
    DischargeConstant,
    DischargeCSV,
    DischargeSynthetic,
)
from flood_adapt.objects.forcing.forcing import (
    ForcingSource,
    ForcingType,
    IDischarge,
    IForcing,
    IRainfall,
    IWaterlevel,
    IWind,
)
from flood_adapt.objects.forcing.rainfall import (
    RainfallConstant,
    RainfallCSV,
    RainfallMeteo,
    RainfallNetCDF,
    RainfallSynthetic,
    RainfallTrack,
)
from flood_adapt.objects.forcing.time_frame import (
    TimeFrame,
)
from flood_adapt.objects.forcing.timeseries import (
    ShapeType,
    TimeseriesFactory,
)
from flood_adapt.objects.forcing.waterlevels import (
    SurgeModel,
    TideModel,
    WaterlevelCSV,
    WaterlevelGauged,
    WaterlevelModel,
    WaterlevelSynthetic,
)
from flood_adapt.objects.forcing.wind import (
    WindConstant,
    WindCSV,
    WindMeteo,
    WindNetCDF,
    WindSynthetic,
    WindTrack,
)
from flood_adapt.objects.measures.measures import (
    FloodWall,
    GreenInfrastructure,
    Measure,
    Pump,
    SelectionType,
)
from flood_adapt.objects.projections.projections import Projection
from flood_adapt.objects.scenarios.scenarios import Scenario
from tests.conftest import IS_WINDOWS
from tests.fixtures import TEST_DATA_DIR
from tests.test_objects.test_forcing.test_netcdf import (
    get_test_dataset,
    time_model_2_hr_timestep,
)


@pytest.fixture()
def default_sfincs_adapter(test_db) -> SfincsAdapter:
    overland_path = test_db.static_path / "templates" / "overland"
    with SfincsAdapter(model_root=overland_path) as adapter:
        start_time = datetime(2023, 1, 1, 0, 0, 0)
        duration = timedelta(hours=3)

        adapter.set_timing(
            TimeFrame(
                start_time=start_time,
                end_time=start_time + duration,
                time_step=timedelta(hours=1),
            )
        )
        adapter._ensure_no_existing_forcings()

        return adapter


@pytest.fixture()
def sfincs_adapter_with_dummy_scn(default_sfincs_adapter):
    # Mock scenario to get a rainfall multiplier
    dummy_scn = mock.Mock()
    dummy_event = mock.Mock()
    dummy_event.rainfall_multiplier = 2
    dummy_event.time = TimeFrame()
    dummy_scn.event = dummy_event
    default_sfincs_adapter._scenario = dummy_scn

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
    test_db.site.sfincs.river = rivers

    with SfincsAdapter(model_root=(overland_2_rivers)) as adapter:
        adapter.set_timing(TimeFrame())
        adapter._ensure_no_existing_forcings()

        return adapter, test_db


@pytest.fixture()
def synthetic_discharge():
    if river := Database().site.sfincs.river:
        return DischargeSynthetic(
            river=river[0],
            timeseries=TimeseriesFactory.from_args(
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
    return Database().site.sfincs.river[0]


@pytest.fixture()
def synthetic_rainfall():
    return RainfallSynthetic(
        timeseries=TimeseriesFactory.from_args(
            shape_type=ShapeType.triangle,
            duration=us.UnitfulTime(value=3, units=us.UnitTypesTime.hours),
            peak_time=us.UnitfulTime(value=1, units=us.UnitTypesTime.hours),
            peak_value=us.UnitfulIntensity(value=10, units=us.UnitTypesIntensity.mm_hr),
        )
    )


@pytest.fixture()
def synthetic_wind():
    return WindSynthetic(
        magnitude=TimeseriesFactory.from_args(
            shape_type=ShapeType.triangle,
            duration=us.UnitfulTime(value=1, units=us.UnitTypesTime.days),
            peak_time=us.UnitfulTime(value=2, units=us.UnitTypesTime.hours),
            peak_value=us.UnitfulVelocity(value=1, units=us.UnitTypesVelocity.mps),
        ),
        direction=TimeseriesFactory.from_args(
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
            timeseries=TimeseriesFactory.from_args(
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
    time: TimeFrame,
    test_db: IDatabase,
    *args,
    **kwargs,
) -> xr.Dataset | xr.DataArray:
    gen = np.random.default_rng(42)
    lat = [test_db.site.lat - 10, test_db.site.lat + 10]
    lon = [test_db.site.lon - 10, test_db.site.lon + 10]
    _time = pd.date_range(
        start=time.start_time,
        end=time.end_time,
        freq=timedelta(hours=1),
        name="time",
    )

    ds = xr.Dataset(
        data_vars={
            "wind10_u": (("time", "y", "x"), gen.random((len(_time), 2, 2))),
            "wind10_v": (("time", "y", "x"), gen.random((len(_time), 2, 2))),
            "press_msl": (("time", "y", "x"), gen.random((len(_time), 2, 2))),
            "precip": (("time", "y", "x"), gen.random((len(_time), 2, 2))),
        },
        coords={
            "y": lat,
            "x": lon,
            "time": _time,
        },
        attrs={
            "crs": 4326,
        },
    )
    ds.raster.set_crs(4326)

    # Convert the longitude to -180 to 180 to match hydromt-sfincs
    if ds["x"].min() > 180:
        ds["x"] = ds["x"] - 360

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


@pytest.fixture()
def spw_file() -> Path:
    cyc_file = TEST_DATA_DIR / "IAN.cyc"
    spw_file = TEST_DATA_DIR / "IAN.spw"
    if spw_file.exists():
        return spw_file
    tc = TropicalCyclone()
    tc.include_rainfall = True
    tc.read_track(cyc_file, fmt="ddb_cyc")
    tc.to_spiderweb(spw_file)
    return spw_file


def _assert_timeseries_equal(
    ds: xr.Dataset | xr.DataArray,
    expected: np.ndarray,
    var_name: str | None = None,
    rtol: float = 1e-6,
):
    if isinstance(ds, xr.Dataset):
        if var_name is None:
            assert (
                len(ds.data_vars) == 1
            ), "Dataset has multiple variables, specify var_name"
            da = next(iter(ds.data_vars.values()))
        else:
            da = ds[var_name]
    else:
        da = ds

    actual = da.to_numpy()

    assert (
        actual.shape == expected.shape
    ), f"Shape mismatch: {actual.shape} != {expected.shape}"

    np.testing.assert_allclose(actual, expected, rtol=rtol)


def _assert_time_equal(ds: xr.Dataset | xr.DataArray, expected_time: np.ndarray):
    actual_time = ds.coords["time"].to_numpy()
    assert (actual_time == expected_time).all()


class TestAddForcing:
    """Class to test the add_forcing method of the SfincsAdapter class."""

    class TestWind:
        def test_add_forcing_wind_constant(self, default_sfincs_adapter: SfincsAdapter):
            # Arrange
            speed_value = 10
            direction_value = 20
            forcing = WindConstant(
                speed=us.UnitfulVelocity(
                    value=speed_value, units=us.UnitTypesVelocity.mps
                ),
                direction=us.UnitfulDirection(
                    value=direction_value, units=us.UnitTypesDirection.degrees
                ),
            )

            # Act
            default_sfincs_adapter.add_forcing(forcing)

            # Assert
            expected = np.array(
                [
                    [speed_value, direction_value],
                    [speed_value, direction_value],
                ]
            )
            assert default_sfincs_adapter.wind is not None
            _assert_timeseries_equal(default_sfincs_adapter.wind, expected)

        def test_add_forcing_wind_synthetic(
            self, default_sfincs_adapter: SfincsAdapter, synthetic_wind: WindSynthetic
        ):
            # Arrange
            assert default_sfincs_adapter.wind is None

            # Act
            default_sfincs_adapter.add_forcing(synthetic_wind)

            # Assert
            assert default_sfincs_adapter.wind is not None
            expected = synthetic_wind.to_dataframe(
                default_sfincs_adapter.get_model_time()
            )
            actual = default_sfincs_adapter.wind["wind"]
            np.testing.assert_allclose(
                actual.sel(index="dir").to_numpy(),
                expected["dir"].to_numpy(),
            )

        def test_add_forcing_wind_from_meteo(
            self, mock_meteohandler_read, default_sfincs_adapter: SfincsAdapter
        ):
            # Arrange
            forcing = WindMeteo()
            assert default_sfincs_adapter.wind is None

            # Act
            default_sfincs_adapter.add_forcing(forcing)

            # Assert
            assert default_sfincs_adapter.wind is not None

        def test_add_forcing_wind_from_netcdf(
            self, test_db: IDatabase, default_sfincs_adapter: SfincsAdapter
        ):
            # Arrange
            path = Path(tempfile.gettempdir()) / "wind_netcdf.nc"

            time = time_model_2_hr_timestep()

            default_sfincs_adapter.set_timing(time)

            ds = get_test_dataset(
                time=time,
                lat=int(test_db.site.lat),
                lon=int(test_db.site.lon),
            )
            ds.to_netcdf(path)
            forcing = WindNetCDF(path=path)

            # Act
            default_sfincs_adapter.add_forcing(forcing)

            # Assert
            assert default_sfincs_adapter.wind is not None

        def test_add_forcing_wind_from_track_cyc(
            self, test_db, tmp_path, default_sfincs_adapter: SfincsAdapter
        ):
            # Arrange
            track_file = TEST_DATA_DIR / "IAN.cyc"
            default_sfincs_adapter._event = mock.Mock()
            default_sfincs_adapter._event.hurricane_translation = TranslationModel(
                eastwest_translation=us.UnitfulLength(
                    value=0, units=us.UnitTypesLength.meters
                ),
                northsouth_translation=us.UnitfulLength(
                    value=0, units=us.UnitTypesLength.meters
                ),
            )

            forcing = WindTrack(path=track_file)

            # Act
            default_sfincs_adapter.add_forcing(forcing)

            # Assert
            spw_name = track_file.with_suffix(".spw").name
            assert default_sfincs_adapter.wind is None
            assert default_sfincs_adapter._model.config.get("spwfile") == spw_name
            assert (default_sfincs_adapter.root / spw_name).exists()

        def test_add_forcing_wind_from_track_spw(
            self,
            test_db,
            tmp_path,
            default_sfincs_adapter: SfincsAdapter,
            spw_file: Path,
        ):
            # Arrange
            forcing = WindTrack(path=spw_file)

            # Act
            default_sfincs_adapter.add_forcing(forcing)

            # Assert
            assert default_sfincs_adapter._model.config.get("spwfile") == spw_file.name
            assert (default_sfincs_adapter.root / spw_file.name).exists()

        def test_add_forcing_wind_csv(
            self, default_sfincs_adapter: SfincsAdapter, synthetic_wind: WindSynthetic
        ):
            assert default_sfincs_adapter.wind is None

            tmp_path = Path(tempfile.gettempdir()) / "wind.csv"
            t0, t1 = default_sfincs_adapter._model.get_model_time()
            time_frame = TimeFrame(start_time=t0, end_time=t1)

            expected = synthetic_wind.to_dataframe(time_frame)
            expected.to_csv(tmp_path)

            forcing = WindCSV(path=tmp_path)

            default_sfincs_adapter.add_forcing(forcing)

            assert default_sfincs_adapter.wind is not None

            actual = default_sfincs_adapter.wind["wind"]

            # direction should match exactly
            np.testing.assert_allclose(
                actual.sel(index="dir").to_numpy(),
                expected["dir"].to_numpy(),
            )

        def test_add_forcing_wind_unsupported(
            self, default_sfincs_adapter: SfincsAdapter
        ):
            # Arrange
            wind = _unsupported_forcing_source(ForcingType.WIND)

            # Act
            default_sfincs_adapter.add_forcing(wind)

            # Assert
            assert default_sfincs_adapter.wind is None

    class TestRainfall:
        def test_add_forcing_rainfall_constant(
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
            expected_value = forcing.intensity.convert(us.UnitTypesIntensity.mm_hr)
            actual = adapter.rainfall.as_numpy()["precip"]
            assert actual.shape[0] == len(adapter.rainfall.time)
            np.testing.assert_allclose(actual, expected_value)

        def test_add_forcing_rainfall_csv(
            self,
            sfincs_adapter_with_dummy_scn: SfincsAdapter,
            synthetic_rainfall: RainfallSynthetic,
        ):
            # Arrange
            adapter = sfincs_adapter_with_dummy_scn
            assert adapter.rainfall is None
            tmp_path = Path(tempfile.gettempdir()) / "wind.csv"
            time_frame = adapter.get_model_time()
            synthetic_rainfall.to_dataframe(time_frame).to_csv(tmp_path)

            # Act
            forcing = RainfallCSV(path=tmp_path)
            adapter.add_forcing(forcing)

            # Assert
            assert adapter.rainfall is not None
            conversion = us.UnitfulIntensity(value=1.0, units=forcing.units).convert(
                us.UnitTypesIntensity.mm_hr
            )
            expected = (
                (forcing.to_dataframe(time_frame=time_frame) * conversion)
                .to_numpy()
                .flatten()
            )
            _assert_timeseries_equal(adapter.rainfall, expected, var_name="precip")

        def test_add_forcing_rainfall_synthetic(
            self, sfincs_adapter_with_dummy_scn: SfincsAdapter, synthetic_rainfall
        ):
            # Arrange
            adapter = sfincs_adapter_with_dummy_scn
            assert adapter.rainfall is None

            # Act
            adapter.add_forcing(synthetic_rainfall)

            # Assert
            assert adapter.rainfall is not None
            time_frame = adapter.get_model_time()
            conversion = us.UnitfulIntensity(
                value=1.0, units=synthetic_rainfall.timeseries.peak_value.units
            ).convert(us.UnitTypesIntensity.mm_hr)
            expected = (
                (synthetic_rainfall.to_dataframe(time_frame) * conversion)
                .to_numpy()
                .flatten()
            )
            _assert_timeseries_equal(adapter.rainfall, expected, var_name="precip")

        def test_add_forcing_rainfall_meteo(
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

        def test_add_forcing_rainfall_netcdf(
            self, test_db: IDatabase, sfincs_adapter_with_dummy_scn: SfincsAdapter
        ):
            # Arrange
            adapter = sfincs_adapter_with_dummy_scn
            assert adapter.rainfall is None
            path = Path(tempfile.gettempdir()) / "wind_netcdf.nc"

            time = time_model_2_hr_timestep()
            adapter.set_timing(time)

            ds = get_test_dataset(
                time=time,
                lat=int(test_db.site.lat),
                lon=int(test_db.site.lon),
            )
            ds.to_netcdf(path)
            forcing = RainfallNetCDF(path=path)

            # Act
            adapter.add_forcing(forcing)

            # Assert
            assert adapter.rainfall is not None

        def test_add_forcing_rainfall_track_cyc(
            self, test_db, default_sfincs_adapter: SfincsAdapter
        ):
            # Arrange
            track_file = TEST_DATA_DIR / "IAN.cyc"
            default_sfincs_adapter._event = mock.Mock()
            default_sfincs_adapter._event.hurricane_translation = TranslationModel(
                eastwest_translation=us.UnitfulLength(
                    value=10, units=us.UnitTypesLength.miles
                ),
                northsouth_translation=us.UnitfulLength(
                    value=10, units=us.UnitTypesLength.miles
                ),
            )

            forcing = RainfallTrack(path=track_file)

            # Act
            default_sfincs_adapter.add_forcing(forcing)

            # Assert
            spw_name = track_file.with_suffix(".spw").name
            assert default_sfincs_adapter._model.config.get("spwfile") == spw_name
            assert (default_sfincs_adapter.root / spw_name).exists()

        def test_add_forcing_rainfall_track_spw(
            self,
            test_db,
            default_sfincs_adapter: SfincsAdapter,
            spw_file: Path,
        ):
            # Arrange
            forcing = RainfallTrack(path=spw_file)

            # Act
            default_sfincs_adapter.add_forcing(forcing)

            # Assert
            assert default_sfincs_adapter._model.config.get("spwfile") == spw_file.name
            assert (default_sfincs_adapter.root / spw_file.name).exists()

        def test_add_forcing_rainfall_unsupported(
            self, sfincs_adapter_with_dummy_scn: SfincsAdapter
        ):
            # Arrange
            adapter = sfincs_adapter_with_dummy_scn
            rainfall = _unsupported_forcing_source(ForcingType.RAINFALL)

            # Act
            adapter.add_forcing(rainfall)

            # Assert
            assert adapter.rainfall is None

    class TestDischarge:
        def test_add_forcing_discharge_constant(
            self, default_sfincs_adapter: SfincsAdapter, synthetic_discharge
        ):
            # Arrange
            assert default_sfincs_adapter.discharge is None
            river = synthetic_discharge.river
            forcing = DischargeConstant(
                river=river,
                discharge=us.UnitfulDischarge(
                    value=5000, units=us.UnitTypesDischarge.cms
                ),
            )

            # Act
            default_sfincs_adapter.add_forcing(forcing)

            # Assert
            assert default_sfincs_adapter.discharge is not None
            time_frame = default_sfincs_adapter.get_model_time()
            conversion = us.UnitfulDischarge(
                value=1.0, units=forcing.discharge.units
            ).convert(us.UnitTypesDischarge.cms)
            expected = (forcing.to_dataframe(time_frame) * conversion).to_numpy()
            _assert_timeseries_equal(
                default_sfincs_adapter.discharge, expected, var_name="dis"
            )

        def test_add_forcing_discharge_csv(
            self, default_sfincs_adapter: SfincsAdapter, synthetic_discharge
        ):
            # Arrange
            assert default_sfincs_adapter.discharge is None
            tmp_path = Path(tempfile.gettempdir()) / "discharge.csv"
            time_frame = default_sfincs_adapter.get_model_time()
            synthetic_discharge.to_dataframe(time_frame).to_csv(tmp_path)

            forcing = DischargeCSV(path=tmp_path, river=synthetic_discharge.river)

            # Act
            default_sfincs_adapter.add_forcing(forcing)

            # Assert
            assert default_sfincs_adapter.discharge is not None
            conversion = us.UnitfulDischarge(value=1.0, units=forcing.units).convert(
                us.UnitTypesDischarge.cms
            )
            expected = (
                forcing.to_dataframe(time_frame=time_frame) * conversion
            ).to_numpy()
            _assert_timeseries_equal(
                default_sfincs_adapter.discharge, expected, var_name="dis"
            )

        def test_add_forcing_discharge_synthetic(
            self, default_sfincs_adapter: SfincsAdapter, synthetic_discharge
        ):
            # Arrange
            assert default_sfincs_adapter.discharge is None
            default_sfincs_adapter.set_timing(TimeFrame())

            # Act
            default_sfincs_adapter.add_forcing(synthetic_discharge)

            # Assert
            assert default_sfincs_adapter.discharge is not None
            time_frame = default_sfincs_adapter.get_model_time()
            conversion = us.UnitfulDischarge(
                value=1.0, units=synthetic_discharge.timeseries.peak_value.units
            ).convert(us.UnitTypesDischarge.cms)
            expected = (
                synthetic_discharge.to_dataframe(time_frame) * conversion
            ).to_numpy()
            _assert_timeseries_equal(
                default_sfincs_adapter.discharge, expected, var_name="dis"
            )

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
            assert db.site.sfincs.river is not None
            assert len(db.site.sfincs.river) == num_rivers

            for i, river in enumerate(db.site.sfincs.river):
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

            for i, river in enumerate(db.site.sfincs.river):
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
        @pytest.fixture()
        def adapter_with_datum(self, default_sfincs_adapter: SfincsAdapter):
            default_sfincs_adapter.database.site.gui.plotting.synthetic_tide.datum = (
                "MSL"
            )
            default_sfincs_adapter.settings.config.offshore_model = FloodModel(
                name="offshore",
                reference="MSL",
            )
            default_sfincs_adapter.settings.water_level = WaterlevelReferenceModel(
                reference="NAVD88",
                datums=[
                    DatumModel(
                        name="NAVD88",
                        height=us.UnitfulLength(
                            value=0, units=us.UnitTypesLength.meters
                        ),
                    ),
                    DatumModel(
                        name="MSL",
                        height=us.UnitfulLength(
                            value=1, units=us.UnitTypesLength.meters
                        ),
                    ),
                ],
            )
            return default_sfincs_adapter

        def test_add_forcing_waterlevels_csv(
            self, adapter_with_datum: SfincsAdapter, synthetic_waterlevels
        ):
            # Arrange
            assert adapter_with_datum.waterlevels is None
            tmp_path = Path(tempfile.gettempdir()) / "waterlevels.csv"
            time_frame = adapter_with_datum.get_model_time()
            synthetic_waterlevels.to_dataframe(time_frame).to_csv(tmp_path)
            forcing = WaterlevelCSV(path=tmp_path, units=us.UnitTypesLength.feet)

            conversion = us.UnitfulLength(value=1.0, units=forcing.units).convert(
                us.UnitTypesLength.meters
            )

            expected = (
                (forcing.to_dataframe(time_frame=time_frame) * conversion)
                .to_numpy()
                .flatten()
            )

            # Act
            adapter_with_datum.add_forcing(forcing)

            # Assert
            assert adapter_with_datum.waterlevels is not None
            actual = adapter_with_datum.waterlevels["bzs"].isel(index=0).as_numpy()
            np.testing.assert_allclose(actual, expected, rtol=1e-2)

        def test_add_forcing_waterlevels_synthetic(
            self,
            adapter_with_datum: SfincsAdapter,
            synthetic_waterlevels: WaterlevelSynthetic,
        ):
            # Arrange
            assert adapter_with_datum.waterlevels is None
            time_frame = adapter_with_datum.get_model_time()
            conversion = us.UnitfulLength(
                value=1.0, units=synthetic_waterlevels.surge.timeseries.peak_value.units
            ).convert(us.UnitTypesLength.meters)
            datum_correction = adapter_with_datum.settings.water_level.get_datum(
                adapter_with_datum.database.site.gui.plotting.synthetic_tide.datum
            ).height.convert(us.UnitTypesLength.meters)

            expected = (
                (
                    synthetic_waterlevels.to_dataframe(time_frame=time_frame)
                    * conversion
                    + datum_correction
                )
                .to_numpy()
                .flatten()
            )

            # Act
            adapter_with_datum.add_forcing(synthetic_waterlevels)

            # Assert
            assert adapter_with_datum.waterlevels is not None
            actual = adapter_with_datum.waterlevels["bzs"].isel(index=0).as_numpy()
            np.testing.assert_allclose(actual, expected, rtol=1e-2)

        def test_add_forcing_waterlevels_gauged(
            self, adapter_with_datum: SfincsAdapter
        ):
            # Arrange
            assert adapter_with_datum.waterlevels is None
            time_frame = adapter_with_datum.get_model_time()
            forcing = WaterlevelGauged()

            conversion = us.UnitfulLength(
                value=1.0, units=adapter_with_datum.settings.tide_gauge.units
            ).convert(us.UnitTypesLength.meters)

            datum_height = adapter_with_datum.settings.water_level.get_datum(
                adapter_with_datum.settings.tide_gauge.reference
            ).height.convert(us.UnitTypesLength.meters)

            expected = (
                (
                    adapter_with_datum.settings.tide_gauge.get_waterlevels_in_time_frame(
                        time=time_frame,
                    )
                    * conversion
                    + datum_height
                )
                .to_numpy()
                .flatten()
            )

            # Act
            adapter_with_datum.add_forcing(forcing)

            # Assert
            assert adapter_with_datum.waterlevels is not None
            actual = (
                adapter_with_datum.waterlevels["bzs"]
                .isel(index=0)  # pick first bnd point since all are equal anyways
                .as_numpy()
            )
            np.testing.assert_allclose(actual, expected, rtol=1e-2)

        def test_add_forcing_waterlevels_model(
            self,
            mock_offshorehandler_get_resulting_waterlevels,
            adapter_with_datum: SfincsAdapter,
        ):
            # Arrange
            assert adapter_with_datum.waterlevels is None
            adapter_with_datum._turn_off_bnd_press_correction = mock.Mock()
            adapter_with_datum._scenario = mock.Mock()
            adapter_with_datum._event = mock.Mock()
            forcing = WaterlevelModel()

            datum_correction = adapter_with_datum.settings.water_level.get_datum(
                adapter_with_datum.settings.config.offshore_model.reference
            ).height.convert(us.UnitTypesLength.meters)

            expected = (
                (mock_offshorehandler_get_resulting_waterlevels + datum_correction)
                .to_numpy()
                .flatten()
            )

            # Act
            adapter_with_datum.add_forcing(forcing)

            # Assert
            assert adapter_with_datum.waterlevels is not None
            actual = (
                adapter_with_datum.waterlevels["bzs"]
                .isel(index=0)  # pick first bnd point since all are equal anyways
                .as_numpy()
            )
            np.testing.assert_allclose(actual, expected, rtol=1e-2)
            adapter_with_datum._turn_off_bnd_press_correction.assert_called_once()

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

    @staticmethod
    def get_measure_gdf(adapter: SfincsAdapter, measure: Measure) -> gpd.GeoDataFrame:
        measure = adapter.database.measures.get(measure.name)
        measure_gdf = gpd.read_file(
            adapter.database.measures.input_path / measure.name / measure.polygon_file
        )
        return measure_gdf.to_crs(adapter._model.crs.to_epsg())

    class TestFloodwall:
        @pytest.fixture()
        def floodwall(self, test_db) -> FloodWall:
            floodwall = FloodWall(
                name="test_seawall",
                description="seawall",
                selection_type=SelectionType.polyline,
                elevation=us.UnitfulLengthRefValue(
                    value=12, units=us.UnitTypesLength.feet
                ),
                polygon_file=str(TEST_DATA_DIR / "seawall.geojson"),
            )

            test_db.measures.add(floodwall)
            return floodwall

        def test_add_measure_floodwall_datum(
            self,
            default_sfincs_adapter: SfincsAdapter,
            floodwall: FloodWall,
            tmp_path: Path,
        ):
            # Arrange
            expected_coords, expected_height = self.get_expected_floodwall_attributes(
                default_sfincs_adapter, floodwall
            )

            original_weirs = default_sfincs_adapter.weirs.copy()

            # Act
            default_sfincs_adapter.add_measure(floodwall)

            weirs = default_sfincs_adapter.weirs

            # Assert: structure
            assert not weirs.empty
            assert len(weirs) == len(original_weirs) + 1

            # Assert: new weir exists and is uniquely identifiable
            added = weirs[weirs["name"] == floodwall.name]

            assert (
                len(added) == 1
            ), f"Expected exactly one weir with name {floodwall.name}"

            geom = added.geometry.iloc[0]

            coords = (
                list(geom.coords)
                if geom.geom_type == "LineString"
                else [c for part in geom.geoms for c in part.coords]
            )

            added_coords = [(round(x, 1), round(y, 1)) for x, y in coords]

            # Assert: geometry
            assert len(added_coords) == len(expected_coords)

            for i, (exp, act) in enumerate(zip(expected_coords, added_coords)):
                assert exp[0] == pytest.approx(act[0], abs=0.2), f"x mismatch at {i}"
                assert exp[1] == pytest.approx(act[1], abs=0.2), f"y mismatch at {i}"

            # Assert: elevation (single value per weir)
            assert "z" in added.columns

            added_height = added["z"].iloc[0]

            expected_total_height = round(
                floodwall.elevation.convert(us.UnitTypesLength.meters), 1
            )

            assert added_height == pytest.approx(expected_total_height, abs=0.2)

        def test_add_measure_floodwall_floodmap(
            self,
            default_sfincs_adapter: SfincsAdapter,
            test_db,
        ):
            floodwall = FloodWall(
                name="test_seawall_floodmap",
                description="seawall floodmap",
                selection_type=SelectionType.polyline,
                elevation=us.UnitfulLengthRefValue(
                    value=2,
                    units=us.UnitTypesLength.feet,
                    type=us.VerticalReference.floodmap,
                ),
                polygon_file=str(TEST_DATA_DIR / "seawall.geojson"),
            )

            test_db.measures.add(floodwall)

            bfe_value = 1.25

            test_db.site.fiat.config.bfe = mock.Mock(
                geom="dummy_bfe.geojson",
                field_name="bfe",
                units=us.UnitTypesLength.meters,
            )

            # Get expected geometry (already in model CRS)
            gdf_raw = TestAddMeasure.get_measure_gdf(default_sfincs_adapter, floodwall)

            raw_lines = []
            for geom in gdf_raw.geometry:
                if geom.geom_type == "LineString":
                    raw_lines.append(geom)
                elif geom.geom_type == "MultiLineString":
                    raw_lines.extend(list(geom.geoms))
                else:
                    raise AssertionError(f"Unsupported geometry type: {geom.geom_type}")

            original_weirs = default_sfincs_adapter.weirs.copy()

            # Mock BFE
            # Get the floodwall extent in model CRS to build a covering BFE polygon
            bounds = gdf_raw.total_bounds  # minx, miny, maxx, maxy
            minx, miny, maxx, maxy = bounds
            # Add a buffer so the polygon fully covers the line
            buf = 500
            gdf_bfe = gpd.GeoDataFrame(
                {
                    "bfe": [bfe_value],
                    "geometry": [
                        Polygon(
                            [
                                (minx - buf, miny - buf),
                                (maxx + buf, miny - buf),
                                (maxx + buf, maxy + buf),
                                (minx - buf, maxy + buf),
                            ]
                        )
                    ],
                },
                crs=gdf_raw.crs,  # same CRS as the floodwall geometry
            )

            original_get_geodataframe = (
                default_sfincs_adapter._model.data_catalog.get_geodataframe
            )

            def mock_get_gdf(source, *args, **kwargs):
                if str(source).endswith("dummy_bfe.geojson"):
                    return gdf_bfe
                return original_get_geodataframe(source, *args, **kwargs)

            with mock.patch.object(
                default_sfincs_adapter._model.data_catalog,
                "get_geodataframe",
                side_effect=mock_get_gdf,
            ):
                default_sfincs_adapter.add_measure(floodwall)

            weirs = default_sfincs_adapter.weirs

            # --- structure ---
            assert len(weirs) == len(original_weirs) + 1

            added = weirs[weirs["name"] == floodwall.name]
            assert len(added) == 1

            geom = added.geometry.iloc[0]

            # --- flatten actual geometry ---
            if geom.geom_type == "LineString":
                actual_lines = [geom]
            elif geom.geom_type == "MultiLineString":
                actual_lines = list(geom.geoms)
            else:
                raise AssertionError(f"Unexpected geometry: {geom.geom_type}")

            # --- geometry comparison (robust) ---
            assert len(actual_lines) == len(raw_lines)

            union_raw = unary_union(raw_lines)
            union_actual = unary_union(actual_lines)

            # symmetric tolerance check
            assert union_raw.buffer(25.0).covers(union_actual)
            assert union_actual.buffer(25.0).covers(union_raw)

            # --- height check ---
            expected_height = round(
                floodwall.elevation.convert(us.UnitTypesLength.meters), 1
            )
            expected_total_height = round(expected_height + bfe_value, 1)

            heights = weirs.loc[added.index, "z"].to_numpy()
            assert np.allclose(
                heights,
                expected_total_height,
                atol=0.5,
            )

        def get_expected_floodwall_attributes(
            self, adapter: SfincsAdapter, floodwall: FloodWall
        ):
            measure_gdf = TestAddMeasure.get_measure_gdf(adapter, floodwall)

            expected_coords = []
            for geom in measure_gdf.geometry:
                for linestring in geom.geoms:
                    expected_coords.extend(linestring.coords)
            expected_coords = [(round(x, 1), round(y, 1)) for x, y in expected_coords]
            expected_height = round(
                floodwall.elevation.convert(us.UnitTypesLength.meters), 1
            )

            return expected_coords, expected_height

    class TestPump:
        @pytest.fixture()
        def pump(self, test_db) -> Pump:
            pump = Pump(
                name="test_pump",
                description="pump",
                discharge=us.UnitfulDischarge(
                    value=100, units=us.UnitTypesDischarge.cfs
                ),
                selection_type=SelectionType.polyline,
                polygon_file=str(TEST_DATA_DIR / "pump.geojson"),
            )
            test_db.measures.add(pump)
            return pump

        def test_add_measure_pump(
            self, default_sfincs_adapter: SfincsAdapter, pump: Pump, tmp_path: Path
        ):
            # Arrange
            original = default_sfincs_adapter.drainage.copy()

            expected_snk_coord, expected_src_coord, expected_discharge = (
                self.get_expected_pump_attributes(default_sfincs_adapter, pump)
            )

            # Act
            default_sfincs_adapter.add_measure(pump)

            # Assert
            drainage = default_sfincs_adapter.drainage

            assert (
                len(drainage) == len(original) + 1
            ), "Expected one new entry in drainage structures"

            # Identify the newly added pump row
            new_row = drainage.iloc[-1]

            # Check type
            assert new_row["type"] in (
                1,
                2,
            ), "All entries should be pumps (1) or culverts (2)"

            # Extract geometry
            coords = list(new_row.geometry.coords)
            assert len(coords) == 2, "Expected exactly 2 coordinates in pump line"

            added_snk = coords[0]
            added_src = coords[-1]

            # Check sink coords
            assert expected_snk_coord[0] == pytest.approx(added_snk[0], abs=0.2)
            assert expected_snk_coord[1] == pytest.approx(added_snk[1], abs=0.2)

            # Check source coords
            assert expected_src_coord[0] == pytest.approx(added_src[0], abs=0.2)
            assert expected_src_coord[1] == pytest.approx(added_src[1], abs=0.2)

            # Check discharge
            assert new_row["par1"] == pytest.approx(
                expected_discharge, rel=1e-3
            ), f"Discharge mismatch: {new_row['par1']} vs {expected_discharge}"

        def get_expected_pump_attributes(self, default_sfincs_adapter, pump):
            measure_gdf = TestAddMeasure.get_measure_gdf(default_sfincs_adapter, pump)

            for geom in measure_gdf.geometry:
                coords = list(geom.coords)
                assert len(coords) == 2, "Expected 2 coordinates in pump geometry"

                expected_snk_coord = (round(coords[0][0], 1), round(coords[0][1], 1))
                expected_src_coord = (round(coords[-1][0], 1), round(coords[-1][1], 1))
                break

            expected_discharge = round(
                pump.discharge.convert(us.UnitTypesDischarge.cms), 6
            )

            return expected_snk_coord, expected_src_coord, expected_discharge

    class TestGreenInfrastructure:
        @pytest.fixture()
        def water_square(self, test_db) -> GreenInfrastructure:
            green_infra = GreenInfrastructure(
                name="test_greeninfra",
                description="greeninfra",
                selection_type=SelectionType.polygon,
                polygon_file=str(TEST_DATA_DIR / "green_infra.geojson"),
                volume=us.UnitfulVolume(value=1, units=us.UnitTypesVolume.m3),
                height=us.UnitfulHeight(value=2, units=us.UnitTypesLength.meters),
                percent_area=0.5,
            )

            test_db.measures.add(green_infra)
            return green_infra

        def test_add_measure_greeninfra(
            self,
            default_sfincs_adapter: SfincsAdapter,
            water_square: GreenInfrastructure,
            tmp_path: Path,
        ):
            # Arrange
            new_root = tmp_path / "greeninfra"
            vol_file = default_sfincs_adapter._model.config.get("volfile")
            assert vol_file is None

            # Act
            default_sfincs_adapter._add_measure_greeninfra(water_square)
            default_sfincs_adapter.write(path_out=new_root)

            # Assert
            vol_file = default_sfincs_adapter._model.config.get("volfile")
            assert vol_file is not None
            with open(default_sfincs_adapter.root / vol_file, "rb") as f:
                contents_after = f.readlines()

            assert contents_after


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
        dummy_projection.physical_projection.sea_level_rise = slr

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
        rainfall_before = adapter._model.precipitation.data.copy()
        dummy_projection.physical_projection.rainfall_multiplier = 2

        rainfall_expected = (
            rainfall_before * dummy_projection.physical_projection.rainfall_multiplier
        )

        # Act
        adapter.add_projection(dummy_projection)
        rainfall_after = adapter._model.precipitation.data

        # Assert
        assert rainfall_expected.equals(rainfall_after)


class TestAddObsPoint:
    def test_add_obs_points(self, test_db: IDatabase):
        if test_db.site.sfincs.obs_point is None:
            test_db.site.sfincs.obs_point = [
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
            / test_db.site.sfincs.config.overland_model.name
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

        site_points = test_db.site.sfincs.obs_point
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
    adapter._ensure_no_existing_forcings()

    # Mock scenario to get a rainfall multiplier
    mock_scn = mock.Mock()
    mock_event = mock.Mock()
    mock_event.rainfall_multiplier = 1.5
    mock_scn.event = mock_event
    adapter._scenario = mock_scn

    # Add forcing to the template
    adapter.add_forcing(forcing)
    adapter.write(COPY_PATH)

    # Act
    adapter = SfincsAdapter(COPY_PATH)
    with pytest.raises(
        ValueError, match=r"Forcing\(s\) should not exists in the SFINCS template model"
    ):
        adapter._ensure_no_existing_forcings()


@pytest.mark.skipif(
    not IS_WINDOWS,
    reason="Only run on windows where we have a working sfincs binary",
)
class TestPostProcessing:
    @pytest.fixture(scope="class")
    def synthetic_rainfall_class(self):
        return RainfallSynthetic(
            timeseries=TimeseriesFactory.from_args(
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
        if river := Database().site.sfincs.river:
            return DischargeSynthetic(
                river=river[0],
                timeseries=TimeseriesFactory.from_args(
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
                timeseries=TimeseriesFactory.from_args(
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
            name="all_synthetic",
            time=TimeFrame(),
            forcings={
                ForcingType.DISCHARGE: [synthetic_discharge_class],
                ForcingType.RAINFALL: [synthetic_rainfall_class],
                ForcingType.WATERLEVEL: [synthetic_waterlevels_class],
            },
        )

    @pytest.fixture(scope="class")
    def adapter_preprocess_process_scenario_class(
        self,
        test_db_class: IDatabase,
        test_event_all_synthetic_class,
    ) -> tuple[SfincsAdapter, Scenario]:
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
        time = TimeFrame(
            start_time=start_time,
            end_time=start_time + duration,
        )
        event.time = time
        test_db_class.events.add(event)
        scn = Scenario(
            name="synthetic",
            event=event.name,
            projection="current",
            strategy="no_measures",
        )
        test_db_class.scenarios.add(scn)

        # Prepare adapter
        overland_path = test_db_class.static.get_overland_sfincs_model().root
        with SfincsAdapter(model_root=overland_path) as adapter:
            adapter._ensure_no_existing_forcings()

            adapter.preprocess(scn, event)
            adapter.process(scn, event)
            yield adapter, scn

    @pytest.fixture(scope="class")
    def floodmaps_1d(self):
        # 3 simulations, 5 grid cells (1D for simplicity)
        floodmaps = [
            np.array([np.nan, 2.0, np.nan, 4.0, np.nan]),
            np.array([2.0, 3.0, np.nan, 5.0, np.nan]),
            np.array([3.0, 4.0, np.nan, 6.0, np.nan]),
        ]
        frequencies = [1.2, 0.01, 0.001]  # decreasing probability
        zb = np.array([0.0, 1.0, 0.0, 2.0, 2.0])  # bed elevation as numpy array
        mask = np.array([1, 1, 0, 1, 1])
        return_periods = [2, 50, 100]
        return floodmaps, frequencies, zb, mask, return_periods

    @pytest.fixture(scope="class")
    def floodmaps_2d(self):
        # 3 simulations, 2x3 grid (2D)
        floodmaps = [
            np.array([[np.nan, 2.0, 3.0], [np.nan, 4.0, np.nan]]),
            np.array([[2.0, 3.0, 4.0], [np.nan, 5.0, np.nan]]),
            np.array([[3.0, 4.0, 5.0], [np.nan, 6.0, np.nan]]),
        ]
        frequencies = [1.2, 0.01, 0.001]  # decreasing probability
        zb = np.array(
            [[0.0, 1.0, 2.0], [0.0, 3.0, 0.0]]
        )  # bed elevation as numpy array
        mask = np.array([[1, 1, 1], [0, 1, 1]])
        return_periods = [2, 50, 100]
        return floodmaps, frequencies, zb, mask, return_periods

    @pytest.mark.integration
    def test_write_geotiff(
        self,
        adapter_preprocess_process_scenario_class: tuple[SfincsAdapter, Scenario],
    ):
        # Arrange
        adapter, scn = adapter_preprocess_process_scenario_class
        floodmap_path = adapter._get_result_path(scn) / f"FloodMap_{scn.name}.tif"

        # Act
        adapter.write_floodmap_geotiff(scenario=scn)

        # Assert
        assert floodmap_path.exists()

    @pytest.mark.parametrize("floodmaps_fixture", ["floodmaps_1d", "floodmaps_2d"])
    def test_calc_rp_maps_basic(self, request, floodmaps_fixture):
        floodmaps, frequencies, zb, mask, return_periods = request.getfixturevalue(
            floodmaps_fixture
        )
        rp_maps = SfincsAdapter.calc_rp_maps(
            floodmaps, frequencies, zb, mask, return_periods
        )
        # Should return a list of np.ndarray, one per return period
        assert isinstance(rp_maps, list)
        assert len(rp_maps) == len(return_periods)
        for da in rp_maps:
            assert isinstance(da, np.ndarray)
            # Should have the same coordinates as the input (excluding masked cells)
            assert floodmaps[0].shape == da.shape

    @pytest.mark.parametrize("floodmaps_fixture", ["floodmaps_1d", "floodmaps_2d"])
    def test_calc_rp_maps_dry_cells(self, request, floodmaps_fixture):
        floodmaps, frequencies, zb, mask, return_periods = request.getfixturevalue(
            floodmaps_fixture
        )
        rp_maps = SfincsAdapter.calc_rp_maps(
            floodmaps, frequencies, zb, mask, return_periods
        )

        always_dry = np.all(np.isnan(floodmaps), axis=0)

        for da in rp_maps:
            # Assert that masked cells (mask == 0) are nan in all rp_maps
            assert np.all(np.isnan(da)[mask == 0])
            # Assert that cells that are always dry (no flood in any simulation) are nan
            assert np.all(np.isnan(da[always_dry]))

    def test_calc_rp_maps_increase_freq(self, floodmaps_2d):
        floodmaps, frequencies, zb, mask, return_periods = floodmaps_2d
        rp_maps1 = SfincsAdapter.calc_rp_maps(
            floodmaps, frequencies, zb, mask, return_periods
        )
        # Increase the frequency of the first floodmap
        frequencies = [f * 10 for f in frequencies]
        rp_maps2 = SfincsAdapter.calc_rp_maps(
            floodmaps, frequencies, zb, mask, return_periods
        )
        # Ensure the rp with increased frequencies have larger values
        for rp1, rp2 in zip(rp_maps1, rp_maps2):
            mask_valid = ~np.isnan(rp1) & ~np.isnan(rp2)
            assert np.all(
                rp2[mask_valid] >= rp1[mask_valid]
            ), "Return period maps with increased frequencies should have larger values (for non-NaN values)"

    def test_calc_rp_maps_increase_value(self, floodmaps_2d):
        # Make sure that for each rp_map in the list, as index increases, the values also increase
        floodmaps, frequencies, zb, mask, return_periods = floodmaps_2d
        rp_maps = SfincsAdapter.calc_rp_maps(
            floodmaps, frequencies, zb, mask, return_periods
        )

        for i in range(len(rp_maps) - 1):
            mask_valid = ~np.isnan(rp_maps[i]) & ~np.isnan(rp_maps[i + 1])
            assert np.all(
                rp_maps[i + 1][mask_valid] >= rp_maps[i][mask_valid]
            ), f"Return period map at index {i + 1} should have values greater than or equal to index {i}"
