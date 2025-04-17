import os
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest
import xarray as xr

from flood_adapt.objects.forcing.meteo_handler import MeteoHandler
from flood_adapt.objects.forcing.time_frame import REFERENCE_TIME, TimeFrame


def write_mock_nc_file(meteo_dir: Path, time: TimeFrame) -> xr.Dataset:
    time_range = MeteoHandler.get_time_range(time)
    METEO_DATETIME_FORMAT = "%Y%m%d_%H%M"
    duration = time_range[1] - time_range[0]
    intervals = int(duration.total_seconds() // timedelta(hours=3).total_seconds()) + 1
    gen = np.random.default_rng(42)

    for i in range(intervals):
        time_coord = time_range[0] + timedelta(hours=3 * i)
        ds = xr.Dataset(
            {
                "wind_u": (("lat", "lon"), gen.random((2, 2))),
                "wind_v": (("lat", "lon"), gen.random((2, 2))),
                "barometric_pressure": (("lat", "lon"), gen.random((2, 2))),
                "precipitation": (("lat", "lon"), gen.random((2, 2))),
            },
            coords={
                "time": [time_coord],
                "lat": [30.0, 30.1],
                "lon": [-90.0, -90.1],
            },
        )
        time_str = time_coord.strftime(METEO_DATETIME_FORMAT)
        file_path = meteo_dir / f"mock.{time_str}.nc"
        ds.to_netcdf(file_path)


class TestMeteoHandler:
    VARIABLES_DOWNLOADED = [
        "barometric_pressure",
        "precipitation",
        "wind_u",
        "wind_v",
    ]

    VARIABLES_RETURNED = [
        "press_msl",
        "precip",
        "wind10_u",
        "wind10_v",
    ]

    @pytest.fixture()
    def setup_meteo_test(self, tmp_path):
        handler = MeteoHandler(dir=tmp_path)
        time = TimeFrame(
            start_time=REFERENCE_TIME,
            end_time=REFERENCE_TIME + timedelta(hours=3),
        )

        yield handler, time

    def test_download_meteo_data(
        self, setup_meteo_test: tuple[MeteoHandler, TimeFrame]
    ):
        # Arrange
        handler, time_model = setup_meteo_test

        # Act
        handler.download(time_model)

        # Assert
        assert handler.dir.exists()
        nc_files = list(handler.dir.glob("*.nc"))
        assert len(nc_files) > 0, "No NetCDF files were downloaded"

        # Read the NetCDF file and assert its contents
        for nc_file in nc_files:
            with xr.open_dataset(nc_file) as ds:
                for var in self.VARIABLES_DOWNLOADED:
                    assert var in ds, f"`{var}` not found in dataset"

    def test_read_meteo_no_nc_files_raises_filenotfound(
        self, setup_meteo_test: tuple[MeteoHandler, TimeFrame]
    ):
        # Arrange
        handler, time = setup_meteo_test

        # patch MeteoHandler download to not download files
        with patch(
            "flood_adapt.objects.forcing.meteo_handler.MeteoHandler.download",
        ):
            # Act
            with pytest.raises(FileNotFoundError) as excinfo:
                handler.read(time)

            assert f"No meteo files found in meteo directory {handler.dir}" in str(
                excinfo.value
            )

    def test_read_meteo_1_nc_file(
        self, setup_meteo_test: tuple[MeteoHandler, TimeFrame]
    ):
        # Arrange
        handler, time = setup_meteo_test
        time.start_time = REFERENCE_TIME
        time.end_time = REFERENCE_TIME + timedelta(hours=1)
        # patch MeteoHandler
        with patch(
            "flood_adapt.objects.forcing.meteo_handler.MeteoHandler.download",
        ) as mock_download:
            mock_download.side_effect = write_mock_nc_file(handler.dir, time)
            # Act
            result = handler.read(time)

            # Assert
            assert isinstance(result, xr.Dataset)
            assert (
                len(os.listdir(handler.dir)) == 1
            ), "Expected 1 NetCDF file in the directory"

            for var in self.VARIABLES_RETURNED:
                assert var in result, f"Expected `{var}` in databaset, but not found"

            assert (
                result["lon"].min() > -180 and result["lon"].max() < 180
            ), f"Expected longitude in range (-180, 180), but got ({result['lon'].min()}, {result['lon'].max()})"

    def test_read_meteo_multiple_nc_files(
        self, setup_meteo_test: tuple[MeteoHandler, TimeFrame]
    ):
        # Arrange
        handler, time = setup_meteo_test
        time.start_time = REFERENCE_TIME
        time.end_time = REFERENCE_TIME + timedelta(hours=12)

        # patch MeteoHandler
        with patch(
            "flood_adapt.objects.forcing.meteo_handler.MeteoHandler.download",
        ) as mock_download:
            mock_download.side_effect = write_mock_nc_file(handler.dir, time)
            # Act
            result = handler.read(time)

            # Assert
            assert isinstance(result, xr.Dataset)
            assert (
                len(os.listdir(handler.dir)) > 1
            ), "Expected multiple NetCDF files in the directory"

            for var in self.VARIABLES_RETURNED:
                assert var in result, f"Expected `{var}` in databaset, but not found"

            assert (
                result["lon"].min() > -180 and result["lon"].max() < 180
            ), f"Expected longitude in range (-180, 180), but got ({result['lon'].min()}, {result['lon'].max()})"
