from datetime import date, datetime
import pandas as pd
import os, glob
from pathlib import Path
import numpy as np
from pandas.tseries.offsets import BusinessDay, Day, YearBegin, MonthBegin, Hour


from loom.data.keys import Keys


def save_data_compressed(data, save_folder):
    if not os.path.exists(save_folder):
        os.makedirs(save_folder)
    for key, df in data.items():
        print(f"Compress/Store dataframe {key} in {save_folder} (takes time for large datasets)")
        df.to_csv(f"{save_folder}/{key}.csv.gz", sep=";", decimal=",", compression="gzip")
        print(f"Compress/Store dataframe {key} in {save_folder}: done")


def fix_data_issues(curves):
    print("fix_index_issues")
    # For coal curves, there is a string value in 2018
    # ValueError: could not convert string to float: '55,4488'
    # Quick fix by using index of gas curves instead
    coal = curves[Keys.coal].replace(',', '.', regex=True)
    # Sanity check: data is now floats only
    coal.loc[:] = np.float32(coal.values)
    curves[Keys.coal] = coal



if __name__ == "__main__":


    dates_found = []

    curves = read_curves_from_files(f"data_historical_2024+")








