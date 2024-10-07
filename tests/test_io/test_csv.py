import pandas as pd
import pytest

from flood_adapt.object_model.io.csv import read_csv

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
    csv_path = temp_dir / "with_header.csv"
    csv_path.write_text(CSV_CONTENT_HEADER)

    df = read_csv(csv_path)

    expected_df = pd.DataFrame(
        {"data_0": [1.0, 2.0, 3.0]},
        index=pd.to_datetime(["2023-01-01", "2023-01-02", "2023-01-03"]),
    )
    expected_df.index.name = "time"

    pd.testing.assert_frame_equal(df, expected_df)


def test_read_csv_no_header(temp_dir):
    csv_path = temp_dir / "no_header.csv"
    csv_path.write_text(CSV_CONTENT_NO_HEADER)

    df = read_csv(csv_path)

    expected_df = pd.DataFrame(
        {"data_0": [1.0, 2.0, 3.0]},
        index=pd.to_datetime(["2023-01-01", "2023-01-02", "2023-01-03"]),
    )
    expected_df.index.name = "time"

    pd.testing.assert_frame_equal(df, expected_df)


def test_read_csv_empty(temp_dir):
    csv_path = temp_dir / "empty.csv"
    csv_path.write_text(CSV_CONTENT_EMPTY)

    with pytest.raises(ValueError, match="The CSV file is empty"):
        read_csv(csv_path)


def test_read_csv_invalid_datetime(temp_dir):
    csv_path = temp_dir / "invalid_datetime.csv"
    csv_path.write_text(CSV_CONTENT_INVALID_DATETIME)

    df = read_csv(csv_path)

    expected_df = pd.DataFrame({"data_0": [3.0]}, index=pd.to_datetime(["2023-01-02"]))
    expected_df.index.name = "time"

    pd.testing.assert_frame_equal(df, expected_df)


def test_read_csv_no_data_columns(temp_dir):
    csv_path = temp_dir / "no_data_columns.csv"
    csv_path.write_text(CSV_CONTENT_NO_DATA_COLUMNS)

    with pytest.raises(ValueError, match="CSV file must have at least one data column"):
        read_csv(csv_path)
