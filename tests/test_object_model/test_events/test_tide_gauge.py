from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from noaa_coops.station import COOPSAPIError

from flood_adapt.object_model.hazard.forcing.tide_gauge import (
    TideGauge,
    TideGaugeSource,
)
from flood_adapt.object_model.hazard.interface.models import TimeModel
from flood_adapt.object_model.hazard.interface.timeseries import CSVTimeseries
from flood_adapt.object_model.io import unit_system as us


@pytest.fixture
def tide_gauge_model():
    return


@pytest.fixture(autouse=True)
def clear_cache():
    TideGauge._cached_data = {}


@pytest.fixture
def mock_cht_station_source_get_data(dummy_1d_timeseries_df):
    with patch(
        "flood_adapt.object_model.hazard.forcing.tide_gauge.cht_station.source"
    ) as mock_source:
        mock_source_obj = MagicMock()
        mock_source_obj.get_data.return_value = dummy_1d_timeseries_df.iloc[:, 0]
        mock_source.return_value = mock_source_obj
        yield mock_source


@pytest.fixture
def setup_file_based_tide_gauge(
    dummy_time_model, dummy_1d_timeseries_df: pd.DataFrame, tmp_path
) -> tuple[TideGauge, Path, TimeModel, pd.DataFrame]:
    csv_path = tmp_path / "waterlevels.csv"
    dummy_1d_timeseries_df.to_csv(csv_path)

    tide_gauge = TideGauge(
        name=8665530,
        reference="MSL",
        source=TideGaugeSource.file,
        description="Charleston Cooper River Entrance",
        ID=8665530,
        lat=32.78,
        lon=-79.9233,
        file=csv_path,
    )

    expected_df = CSVTimeseries.load_file(
        path=csv_path, units=us.UnitfulLength(value=0, units=us.UnitTypesLength.meters)
    ).to_dataframe(time_frame=dummy_time_model)

    return tide_gauge, csv_path, dummy_time_model, expected_df


@pytest.fixture
def setup_download_based_tide_gauge(
    dummy_time_model, dummy_1d_timeseries_df: pd.DataFrame, tmp_path
) -> tuple[TideGauge, Path, TimeModel, pd.DataFrame]:
    csv_path = tmp_path / "waterlevels.csv"
    dummy_1d_timeseries_df.to_csv(csv_path)

    tide_gauge = TideGauge(
        name=8665530,
        reference="MSL",
        source=TideGaugeSource.noaa_coops,
        description="Charleston Cooper River Entrance",
        ID=8665530,
        lat=32.78,
        lon=-79.9233,
    )

    expected_df = CSVTimeseries.load_file(
        path=csv_path, units=us.UnitfulLength(value=0, units=us.UnitTypesLength.meters)
    ).to_dataframe(time_frame=dummy_time_model)
    return tide_gauge, csv_path, dummy_time_model, expected_df


def test_read_imported_waterlevels_from_file(setup_file_based_tide_gauge):
    # Arrange
    tide_gauge, csv_path, dummy_time_model, dummy_1d_timeseries_df = (
        setup_file_based_tide_gauge
    )

    # Act
    result_df = tide_gauge._read_imported_waterlevels(
        time=dummy_time_model, path=csv_path
    )

    # Assert
    assert dummy_1d_timeseries_df.equals(result_df)


def test_download_tide_gauge_data(
    mock_cht_station_source_get_data, setup_download_based_tide_gauge
):
    # Arrange
    tide_gauge, csv_path, dummy_time_model, expected_df = (
        setup_download_based_tide_gauge
    )

    # Act
    result_df = tide_gauge._download_tide_gauge_data(time=dummy_time_model)

    # Assert
    pd.testing.assert_frame_equal(expected_df, result_df)


def test_get_waterlevels_in_time_frame_from_file(
    setup_file_based_tide_gauge: tuple[TideGauge, Path, TimeModel, pd.DataFrame],
):
    # Arrange
    tide_gauge, _, dummy_time_model, expected_df = setup_file_based_tide_gauge

    # Act
    result_df = tide_gauge.get_waterlevels_in_time_frame(time=dummy_time_model)

    # Assert
    assert result_df is not None
    assert (
        abs((dummy_time_model.start_time - result_df.index[0]).total_seconds())
        < dummy_time_model.time_step.total_seconds()
    )
    assert (
        abs((dummy_time_model.end_time - result_df.index[-1]).total_seconds())
        < dummy_time_model.time_step.total_seconds()
    )

    # Ignore column names
    result_df.columns = ["waterlevel"]
    expected_df.columns = ["waterlevel"]

    pd.testing.assert_frame_equal(result_df, expected_df)


def test_get_waterlevels_in_time_frame_from_download(
    mock_cht_station_source_get_data, setup_download_based_tide_gauge
):
    # Arrange
    tide_gauge, csv_path, dummy_time_model, expected_df = (
        setup_download_based_tide_gauge
    )

    # Act
    result_df: pd.DataFrame = tide_gauge.get_waterlevels_in_time_frame(
        time=dummy_time_model
    )

    # Assert
    assert result_df is not None
    assert (
        abs((dummy_time_model.start_time - result_df.index[0]).total_seconds())
        < dummy_time_model.time_step.total_seconds()
    )
    assert (
        abs((dummy_time_model.end_time - result_df.index[-1]).total_seconds())
        < dummy_time_model.time_step.total_seconds()
    )

    # Ignore column names
    result_df.columns = ["waterlevel"]
    expected_df.columns = ["waterlevel"]

    pd.testing.assert_frame_equal(result_df, expected_df)


def test_download_tide_gauge_data_cache(
    mock_cht_station_source_get_data, setup_download_based_tide_gauge
):
    # Arrange
    tide_gauge, _, dummy_time_model, _ = setup_download_based_tide_gauge

    # Act
    df1 = tide_gauge._download_tide_gauge_data(time=dummy_time_model)
    df2 = tide_gauge._download_tide_gauge_data(time=dummy_time_model)

    # Assert
    pd.testing.assert_frame_equal(df1, df2)
    mock_cht_station_source_get_data.return_value.get_data.assert_called_once()


def test_download_tide_gauge_data_error(
    mock_cht_station_source_get_data, setup_download_based_tide_gauge
):
    # Arrange
    tide_gauge, _, dummy_time_model, _ = setup_download_based_tide_gauge

    mock_cht_station_source_get_data.return_value.get_data.side_effect = COOPSAPIError(
        "Some download error"
    )

    # Act
    result_df = tide_gauge._download_tide_gauge_data(time=dummy_time_model)

    # Assert
    assert result_df is None


def test_download_tide_gauge_other_error(
    mock_cht_station_source_get_data, setup_download_based_tide_gauge
):
    # Arrange
    tide_gauge, _, dummy_time_model, _ = setup_download_based_tide_gauge

    mock_cht_station_source_get_data.return_value.get_data.side_effect = Exception(
        "Some other error"
    )

    # Act & Assert
    with pytest.raises(Exception):
        tide_gauge._download_tide_gauge_data(time=dummy_time_model)
