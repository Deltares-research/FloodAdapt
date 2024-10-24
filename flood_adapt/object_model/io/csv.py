import csv
from pathlib import Path

import pandas as pd


def read_csv(csvpath: Path) -> pd.DataFrame:
    """Read a timeseries file and return a pd.DataFrame.

    Parameters
    ----------
    csvpath : Path
        Path to the CSV file.

    Returns
    -------
    pd.DataFrame
        Dataframe with time as index and (a) data column(s).
    """
    num_columns = None
    has_header = None
    with open(csvpath, "r") as f:
        try:
            # read the first 1024 bytes to determine if there is a header
            has_header = csv.Sniffer().has_header(f.read(1024))
        except csv.Error:
            has_header = False
        f.seek(0)
        reader = csv.reader(f, delimiter=",")
        try:
            first_row = next(reader)
            num_columns = len(first_row) - 1  # subtract 1 for the index column
        except StopIteration:
            raise ValueError(f"The CSV file is empty: {csvpath}.")

    if has_header is None:
        raise ValueError(
            f"Could not determine if the CSV file has a header: {csvpath}."
        )
    if num_columns is None:
        raise ValueError(
            f"Could not determine the number of columns in the CSV file: {csvpath}."
        )
    elif num_columns < 1:
        raise ValueError(f"CSV file must have at least one data column: {csvpath}.")
    columns = [f"data_{i}" for i in range(num_columns)]
    dtype = {name: float for name in columns}

    df = pd.read_csv(
        csvpath,
        index_col=0,
        names=columns,
        header=0 if has_header else None,
        parse_dates=True,
        infer_datetime_format=True,
        dtype=dtype,
    )

    # Any index that cannot be converted to datetime will be NaT
    df.index = pd.to_datetime(df.index, errors="coerce")
    df.index.names = ["time"]
    if len(df.index) > 2:
        df.index.freq = pd.infer_freq(df.index)

    # Drop rows where the index is NaT
    df = df[~df.index.isna()]

    return df
