import os
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

import pytest
import xarray as xr

from flood_adapt.object_model.hazard.event.meteo import download_meteo, read_meteo
from flood_adapt.object_model.hazard.interface.models import TimeModel


class TestDownloadMeteo:
    def test_download_meteo_data_exists(self, test_db, tmp_path):
        # Arrange
        meteo_dir = Path(tmp_path, "meteo")
        time = TimeModel()

        # Act
        download_meteo(meteo_dir, time, test_db.site.attrs)

        # Assert
        assert meteo_dir.exists()
        assert len(os.listdir(meteo_dir)) > 0, "No files were downloaded"


class TestReadMeteo:
    @staticmethod
    def write_mock_nc_file(meteo_dir: Path, time: TimeModel):
        ds = xr.Dataset(
            {
                "barometric_pressure": (("x", "y"), [[1013, 1012], [1011, 1010]]),
                "precipitation": (("x", "y"), [[0.1, 0.2], [0.3, 0.4]]),
            },
            coords={
                "x": [0, 1],
                "y": [0, 1],
            },
        )
        file_path = meteo_dir / f"mock.{time.start_time.strftime('%Y%m%d_%H%M')}.nc"
        ds.to_netcdf(file_path)
        return ds

    @patch("flood_adapt.object_model.hazard.event.meteo.download_meteo")
    def test_read_meteo_only_1_nc_file(mock_download_meteo, test_db, tmp_path):
        # Arrange
        meteo_dir = tmp_path
        time = TimeModel()

        expected_ds = TestReadMeteo.write_mock_nc_file(meteo_dir, time)
        expected_ds.raster.set_crs(4326)
        expected_ds = expected_ds.rename({"barometric_pressure": "press"})
        expected_ds = expected_ds.rename({"precipitation": "precip"})

        # Act
        result = read_meteo(meteo_dir, time, test_db.site.attrs)

        # Assert
        assert isinstance(result, xr.Dataset)
        assert result == expected_ds

    @patch("flood_adapt.object_model.hazard.event.meteo.download_meteo")
    def test_read_meteo_multiple_nc_files(mock_download_meteo, test_db, tmp_path):
        # Arrange
        meteo_dir = tmp_path
        _time = TimeModel()
        datasets = []

        for i in range(5):
            time = TimeModel(
                start_time=_time.start_time + timedelta(days=i),
                end_time=_time.end_time + timedelta(days=i),
            )
            ds = TestReadMeteo.write_mock_nc_file(meteo_dir, time)
            datasets.append(ds)

        expected_ds = xr.concat(datasets, dim="time")
        expected_ds.raster.set_crs(4326)
        expected_ds = expected_ds.rename({"barometric_pressure": "press"})
        expected_ds = expected_ds.rename({"precipitation": "precip"})

        # Act
        result = read_meteo(meteo_dir, _time, test_db.site.attrs)

        # Assert
        assert isinstance(result, xr.Dataset)
        assert result == expected_ds

    def test_read_meteo_no_nc_files(self, test_db, tmp_path):
        # Arrange
        meteo_dir = tmp_path

        # Act & Assert
        with pytest.raises(ValueError) as e:
            read_meteo(meteo_dir, TimeModel(), test_db.site.attrs)
        assert "No meteo files found in the specified directory" in str(e.value)
