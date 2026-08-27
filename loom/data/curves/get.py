from datetime import date, datetime
import pandas as pd
import os, glob
from pathlib import Path
import numpy as np
from pandas.tseries.offsets import BusinessDay, Day, YearBegin, MonthBegin, Hour


from loom.data.keys import Keys


tz = "Europe/Berlin"


def read_curves_from_repository(folder, key):
    path_file = Path(__file__).parent.resolve() / folder / f"{key}.csv.gz"

    df = pd.read_csv(path_file, sep=";", decimal=",", index_col=0, header=0)
    df.index = pd.to_datetime(df.index, utc=True).tz_convert(tz)
    df.columns = pd.to_datetime(df.columns, errors="coerce").tz_localize(tz)

    return df


def read_curves_from_onedrive(folder, key):
    path_file = Path(r"C:\Users\Lena\OneDrive\Dokumente\EnBW") / folder / f"{key}.csv.gz"

    df = pd.read_csv(path_file, sep=";", decimal=",", index_col=0, header=0)
    df.index = pd.to_datetime(df.index, utc=True).tz_convert(tz)
    df.columns = pd.to_datetime(df.columns, errors="coerce").tz_localize(tz)

    return df



if __name__ == "__main__":

    curves = read_curves_from_onedrive(f"data_historical_2024+", Keys.power_germany)
    curves = read_curves_from_repository(f"data_historical_2015+", Keys.power_germany)





