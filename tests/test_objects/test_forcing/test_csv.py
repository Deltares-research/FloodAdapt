import pandas as pd
import pytest

from flood_adapt.objects.forcing.csv import equal_csv, read_csv

CSV_CONTENT_HEADER = """time,data_0
2023-01-01,1.0
2023-01-02,2.0
2023-01-03,3.0
"""

CSV_CONTENT_NO_HEADER = """2023-01-01,1.0
2023-01-02,2.0
2023-01-03,3.0
"""

CSV_CONTENT_EMPTY = ""

CSV_CONTENT_INVALID_DATETIME = """time,data_0
invalid_date,1.0
2023-01-02,3.0
"""

CSV_CONTENT_NO_DATA_COLUMNS = """time
2023-01-01
2023-01-02
2023-01-03
"""


@pytest.fixture
def temp_dir(tmp_path):
    return tmp_path


def test_read_csv_with_header(temp_dir):
    # Arrange
    csv_path = temp_dir / "with_header.csv"
    csv_path.write_text(CSV_CONTENT_HEADER)
    expected_df = pd.DataFrame(
        {"data_0": [1.0, 2.0, 3.0]},
        index=pd.to_datetime(
            ["2023-01-01", "2023-01-02", "2023-01-03"], infer_datetime_format=True
        ),
    )
    expected_df.index.name = "time"
    expected_df.index.freq = pd.infer_freq(expected_df.index)

    # Act
    df = read_csv(csv_path)

    # Assert
    pd.testing.assert_frame_equal(df, expected_df)


def test_read_csv_no_header(temp_dir):
    # Arrange
    csv_path = temp_dir / "no_header.csv"
    csv_path.write_text(CSV_CONTENT_NO_HEADER)
    expected_df = pd.DataFrame(
        {"data_0": [1.0, 2.0, 3.0]},
        index=pd.to_datetime(["2023-01-01", "2023-01-02", "2023-01-03"]),
    )
    expected_df.index.name = "time"
    expected_df.index.freq = pd.infer_freq(expected_df.index)

    # Act
    df = read_csv(csv_path)

    # Assert
    pd.testing.assert_frame_equal(df, expected_df)


def test_read_csv_empty(temp_dir):
    # Arrange
    csv_path = temp_dir / "empty.csv"
    csv_path.write_text(CSV_CONTENT_EMPTY)

    # Act & Assert
    with pytest.raises(ValueError, match="The CSV file is empty"):
        read_csv(csv_path)


def test_read_csv_invalid_datetime(temp_dir):
    # Arrange
    csv_path = temp_dir / "invalid_datetime.csv"
    csv_path.write_text(CSV_CONTENT_INVALID_DATETIME)
    expected_df = pd.DataFrame({"data_0": [3.0]}, index=pd.to_datetime(["2023-01-02"]))
    expected_df.index.name = "time"

    # Act
    df = read_csv(csv_path)

    # Assert
    pd.testing.assert_frame_equal(df, expected_df)


def test_read_csv_no_data_columns(temp_dir):
    # Arrange
    csv_path = temp_dir / "no_data_columns.csv"
    csv_path.write_text(CSV_CONTENT_NO_DATA_COLUMNS)

    # Act & Assert
    with pytest.raises(ValueError, match="CSV file must have at least one data column"):
        read_csv(csv_path)


def test_equal_csv_identical(tmp_path):
    left = tmp_path / "a.csv"
    right = tmp_path / "b.csv"

    df = pd.DataFrame({"x": [1, 2], "y": [3, 4]})
    df.to_csv(left)
    df.to_csv(right)

    assert equal_csv(left, right) is True


def test_equal_csv_different_values(tmp_path):
    left = tmp_path / "a.csv"
    right = tmp_path / "b.csv"

    pd.DataFrame({"x": [1, 2]}).to_csv(left)
    pd.DataFrame({"x": [1, 3]}).to_csv(right)

    assert equal_csv(left, right) is False


def test_equal_csv_different_index(tmp_path):
    left = tmp_path / "a.csv"
    right = tmp_path / "b.csv"

    pd.DataFrame({"x": [1, 2]}, index=[0, 1]).to_csv(left)
    pd.DataFrame({"x": [1, 2]}, index=[1, 2]).to_csv(right)

    assert equal_csv(left, right) is False
