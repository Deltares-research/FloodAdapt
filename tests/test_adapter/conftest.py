from datetime import datetime, timedelta
from functools import partial
from unittest import mock

import numpy as np
import pandas as pd
import pytest
import xarray as xr

from flood_adapt.adapter.sfincs_adapter import SfincsAdapter
from flood_adapt.config.config import Settings
from flood_adapt.config.hazard import (
    RiverModel,
)
from flood_adapt.dbs_classes import Database
from flood_adapt.dbs_classes.interface.database import IDatabase
from flood_adapt.objects import unit_system as us
from flood_adapt.objects.forcing import (
    DischargeSynthetic,
    ForcingSource,
    ForcingType,
    RainfallSynthetic,
    ShapeType,
    SurgeModel,
    TideModel,
    TimeFrame,
    TimeseriesFactory,
    WaterlevelSynthetic,
    WindSynthetic,
)
from flood_adapt.objects.forcing.forcing import (
    IDischarge,
    IRainfall,
    IWaterlevel,
    IWind,
)


@pytest.fixture()
def default_sfincs_adapter(test_db, setup_settings) -> SfincsAdapter:
    overland_path = test_db.static_path / "templates" / "overland"
    with SfincsAdapter(
        model_root=overland_path,
        delete_crashed_runs=setup_settings.delete_crashed_runs,
        exe_path=setup_settings.sfincs_bin_path,
    ) as adapter:
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
def sfincs_adapter_2_rivers(
    test_db: IDatabase, setup_settings: Settings
) -> tuple[SfincsAdapter, IDatabase]:
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

    with SfincsAdapter(
        model_root=(overland_2_rivers),
        delete_crashed_runs=setup_settings.delete_crashed_runs,
        exe_path=setup_settings.sfincs_bin_path,
    ) as adapter:
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
