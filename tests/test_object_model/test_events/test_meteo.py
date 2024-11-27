import os
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest
import xarray as xr

from flood_adapt.object_model.hazard.event.meteo import MeteoHandler
from flood_adapt.object_model.hazard.interface.models import REFERENCE_TIME, TimeModel


def write_mock_nc_file(
    meteo_dir: Path, time_range: tuple[datetime, datetime]
) -> xr.Dataset:
    METEO_DATETIME_FORMAT = "%Y%m%d_%H%M"
    duration = time_range[1] - time_range[0]
    intervals = int(duration.total_seconds() // timedelta(hours=3).total_seconds())
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
    @pytest.fixture()
    def setup_meteo_test(self, tmp_path):
        handler = MeteoHandler(dir=tmp_path)
        time = TimeModel(
            start_time=REFERENCE_TIME,
            end_time=REFERENCE_TIME + timedelta(hours=3),
        )

        yield handler, time

    @pytest.fixture
    def mock_meteogrid_download(self):
        """Mock the download method of MeteoGrid to not do an expensive MeteoGrid.download call, and write a mock netcdf file instead."""

        def side_effect(
            time_range: tuple[datetime, datetime], parameters: list[str], path: Path
        ):
            write_mock_nc_file(path, time_range)

        with patch(
            "flood_adapt.object_model.hazard.event.meteo.MeteoGrid.download",
            side_effect=side_effect,
        ) as mock_download:
            yield mock_download

    def test_download_meteo_data(
        self, setup_meteo_test: tuple[MeteoHandler, TimeModel]
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
                assert (
                    "barometric_pressure" in ds
                ), "`barometric_pressure` not found in dataset"
                assert "precipitation" in ds, "`precipitation` not found in dataset"

    def test_read_meteo_no_nc_files_raises_filenotfound(
        self, mock_meteogrid_download, setup_meteo_test: tuple[MeteoHandler, TimeModel]
    ):
        # Arrange
        handler, time = setup_meteo_test
        mock_meteogrid_download.side_effect = (
            lambda time_range, parameters, path: None
        )  # Mock download to not write any files

        # Act
        with pytest.raises(FileNotFoundError) as excinfo:
            handler.read(time)

        assert f"No meteo files found in meteo directory {handler.dir}" in str(
            excinfo.value
        )

    def test_read_meteo_1_nc_file(
        self, mock_meteogrid_download, setup_meteo_test: tuple[MeteoHandler, TimeModel]
    ):
        # Arrange
        handler, time = setup_meteo_test

        # Act
        result = handler.read(time)

        # Assert
        assert isinstance(result, xr.Dataset)
        assert (
            len(os.listdir(handler.dir)) == 1
        ), "Expected 1 NetCDF file in the directory"
        assert "precip" in result, "`precip` not found in result"
        assert "press" in result, "`press` not found in result"

    def test_read_meteo_multiple_nc_files(
        self, mock_meteogrid_download, setup_meteo_test: tuple[MeteoHandler, TimeModel]
    ):
        # Arrange
        handler, time = setup_meteo_test
        time.start_time = REFERENCE_TIME
        time.end_time = REFERENCE_TIME + timedelta(hours=12)

        # Act
        result = handler.read(time)

        # Assert
        assert isinstance(result, xr.Dataset)
        assert (
            len(os.listdir(handler.dir)) > 1
        ), "Expected multiple NetCDF files in the directory"
        assert "precip" in result, "`precip` not found in result"
        assert "press" in result, "`press` not found in result"
