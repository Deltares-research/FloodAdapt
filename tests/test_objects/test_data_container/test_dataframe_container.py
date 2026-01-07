import pandas as pd
import pytest

from flood_adapt.objects.data_container import (
    DataFrameContainer,
)


@pytest.fixture
def sample_dataframe() -> pd.DataFrame:
    return pd.DataFrame({"a": [1, 2, 3], "b": [4.0, 5.0, 6.0]})


def test_dataframe_read_write_csv(tmp_path, sample_dataframe):
    csv_path = tmp_path / "data.csv"
    sample_dataframe.to_csv(csv_path, index=False)

    ref = DataFrameContainer(path=csv_path)
    ref.read()

    assert ref.has_data()
    pd.testing.assert_frame_equal(ref.data, sample_dataframe)

    # Test write to a new file
    out_path = tmp_path / "data_copy.csv"
    ref.path = out_path
    ref.write()
    assert out_path.exists()

    df_copy = pd.read_csv(out_path)
    pd.testing.assert_frame_equal(df_copy, sample_dataframe)


def test_dataframe_read_write_parquet(tmp_path, sample_dataframe):
    path = tmp_path / "data.parquet"
    sample_dataframe.to_parquet(path)

    ref = DataFrameContainer(path=path)
    ref.read()

    pd.testing.assert_frame_equal(ref.data, sample_dataframe)

    out_path = tmp_path / "copy.parquet"
    ref.path = out_path
    ref.write()

    df_copy = pd.read_parquet(out_path)
    pd.testing.assert_frame_equal(df_copy, sample_dataframe)


def test_dataframe_read_write_feather(tmp_path, sample_dataframe):
    path = tmp_path / "data.feather"
    sample_dataframe.to_feather(path)

    ref = DataFrameContainer(path=path)
    ref.read()

    pd.testing.assert_frame_equal(ref.data, sample_dataframe)

    out_path = tmp_path / "copy.feather"
    ref.path = out_path
    ref.write()

    df_copy = pd.read_feather(out_path)
    pd.testing.assert_frame_equal(df_copy, sample_dataframe)


def test_dataframe_extension_controls_behavior(tmp_path, sample_dataframe):
    path = tmp_path / "data.csv"
    sample_dataframe.to_csv(path, index=False)

    # Rename to .parquet but keep CSV content
    bad_path = tmp_path / "data.parquet"
    path.rename(bad_path)

    ref = DataFrameContainer(path=bad_path)

    with pytest.raises(Exception):
        ref.read()


def test_dataframe_equality(sample_dataframe, tmp_path):
    path1 = tmp_path / "a.csv"
    sample_dataframe.to_csv(path1, index=False)
    ref1 = DataFrameContainer(path=path1)
    ref2 = DataFrameContainer(path=path1)

    # Reading loads data and equality should hold
    ref1.read()
    ref2.read()
    assert ref1 == ref2


def test_dataframe_unsupported_format(tmp_path):
    bad_path = tmp_path / "data.txt"
    bad_path.write_text("test")

    ref = DataFrameContainer(path=bad_path)
    with pytest.raises(ValueError, match="Unsupported DataFrame format"):
        ref.read()
