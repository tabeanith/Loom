from pathlib import Path
import pandas as pd
import traceback

from loom.utils.files import print_link
import os
import numpy as np
import glob

tz = "Europe/Berlin"
save_dir = Path(os.path.dirname(os.path.realpath(__file__)))


def _save_dataframe(df, full_path: Path=None):
    try:
        df.to_csv(full_path, sep=";", decimal=".", compression="gzip")  # ENGLISH CSV

        print(f"df saved: {full_path}")
        print_link(full_path)

    except Exception:
        print(traceback.format_exc())

    return full_path


def save_dataframe_continuous(df, symbol: str, tf: str):
    full_path = save_dir / f"{symbol}_{tf}" / f"continuous.csv.gz"
    _save_dataframe(df, full_path)


def save_dataframe(df, symbol: str, tf: str, tenor: str):
    full_path = save_dir / f"{symbol}_{tf}" / f"{tenor}.csv.gz"
    _save_dataframe(df, full_path)


def _read_dataframe(file_path, tz="UTC", header=[0]):
    #_df = pd.read_csv(file_path, sep=";", decimal=",", index_col=0, header=header)  # German CSV
    try:
        _df = pd.read_csv(file_path, sep=";", decimal=".", index_col=0, header=header, compression="gzip")  # English CSV

        _df.index = pd.to_datetime(_df.index.values, utc=True)
        df = _df.tz_convert(tz)

        for key, dtype in df.dtypes.items():
            if dtype == object: df = df.drop(columns=[key])

        df = df.astype(np.float32)
        print(f"Dataframe read from csv: {file_path}")

    except:
        print(traceback.format_exc())
        df = pd.DataFrame()

    return df


def read_dataframe(symbol: str, tf: str):
    folder_path = Path(__file__).parent.parent.parent.parent.parent.resolve() / "Aleph" / "aleph" / "data" / "db"

    full_path = folder_path / f"{symbol}_{tf}" / f"*.csv.gz"

    # Stitching Futures
    file_list = glob.glob(full_path.__str__())
    file_list.sort()

    df = pd.DataFrame()
    continuous_file = [f for f in file_list if "continuous" in f]
    tenor_files = [f for f in file_list if not "continuous" in f]
    tenor_files.sort()

    for f in continuous_file:
        _df = _read_dataframe(f)
        df = df.combine_first(_df)

    for f in tenor_files:
        _df = _read_dataframe(f)

        # Stitch together price jumps
        if not df.empty:
            ts_stitch = df.index[-1]
            _df = _df[_df.index >= ts_stitch]

            if not _df.empty:
                stitch_jump = _df.iloc[0] - df.iloc[-1]
                stitch_jump = stitch_jump["open"]

                df = df + stitch_jump  # IMPORTANT: Only use the Open to shift all Bars
                df = df.combine_first(_df)

    df.index = pd.to_datetime(df.index, utc=True).tz_convert(tz=tz)

    return df


def read_dataframe_of_single_tenor(symbol: str, tf: str, tenor: str):
    full_path = save_dir / f"{symbol}_{tf}" / f"{tenor}.csv.gz"
    df = _read_dataframe(full_path, tz="UTC", header=[0])
    return df


if __name__ == "__main__":
    symbol = "ES"
    tf = "5min"
    df = read_dataframe(symbol, tf)

