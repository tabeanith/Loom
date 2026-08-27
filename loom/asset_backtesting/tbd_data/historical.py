import numpy as np
import pandas as pd
from pandas._libs.tslibs.offsets import Hour
from pandas.tseries.offsets import Day

from pathlib import Path

def get_price_curves_and_insert_spot_results(file_name: str):
    #file_name = "power_germany_live_curves.csv.gz"
    file = Path(__file__).parent.resolve() / file_name

    spot_curve = get_spot_curve()
    price_curves = get_curves(file)
    # ---------------------- Combine forward prices and spot results -----------------------------
    # Forward fill data
    price_curves = price_curves.ffill(axis=0)

    # Backwards fill in spot result:
    for ts in price_curves.columns:
        # ----------------------------- Last price observed before Spot -----------------------------
        spot_date = (ts + Day(1)).date()
        # We only optimize the current day until 11am. Afterwards, the prices are "frozen" to the last view we have before spot market
        mask_spot_day = price_curves.index.date == spot_date
        mask_after_spot = price_curves.columns.hour > 11
        price_curves.loc[mask_spot_day, mask_after_spot] = np.nan

        mask_past = price_curves.index.date < spot_date
        price_curves.loc[mask_past, ts] = np.nan

    # Backwards fill in spot result:
    latest_ts = price_curves.columns[-1]
    price_curves[latest_ts] = price_curves[latest_ts].combine_first(spot_curve)
    price_curves = price_curves.bfill(axis=1)  # Fill spot value back in time
    return spot_curve, price_curves


def get_spot_curve():
    file = Path(__file__).parent.resolve() / "spot_curve.csv.gz"

    spot_curve = pd.read_csv(file)
    _ts_column = "DBBMDDAttribute.period_begin_dt"
    spot_curve.index = spot_curve[_ts_column]

    spot_curve.index = pd.to_datetime(spot_curve.index, utc=True).tz_convert(tz="Europe/Berlin")
    spot_curve = spot_curve.drop(_ts_column, axis=1)
    spot_curve = spot_curve.iloc[:, 0]

    return spot_curve




def get_curves(file: Path):
    # file_name = "power_germany_live_curves.csv.gz"
    file_str = str(file)

    if "snapshot" in file_str:
        price_curves = pd.read_csv(f"{file_str}", sep=";", decimal=",")
    else:
        price_curves = pd.read_csv(f"{file_str}")

    _ts_column = price_curves.columns[0]
    price_curves.index = price_curves[_ts_column]

    price_curves.index = pd.to_datetime(price_curves.index, utc=True).tz_convert(tz="Europe/Berlin")
    price_curves = price_curves.drop(_ts_column, axis=1)

    price_curves.columns = pd.to_datetime(price_curves.columns, utc=True).tz_convert(tz="Europe/Berlin")

    return price_curves


def get_schedules_and_valuation_curves_from_filer(data):
    asset = data["asset"]
    price_curves = data["price_curves"]

    try:
        schedule_curves = get_curves(f"schedule_optimzied_{asset.name}.csv.gz")

        if asset.name in ["turbine", "battery", "battery_colocated"]:
            valuation_curves = []
            for ts in price_curves.columns:
                valuation_curves.append(asset.valuate(price_curves[ts], schedule_curves[ts]))

            valuation_curves = pd.concat(valuation_curves, axis=1)
        else:
            valuation_curves = get_curves(f"valuation_{asset.name}.csv.gz")

        schedule_curves = schedule_curves.reindex(price_curves.index).reindex(columns=price_curves.columns)
        valuation_curves = valuation_curves.reindex(price_curves.index).reindex(columns=price_curves.columns)


    except Exception as ex:
        schedule_curves = pd.DataFrame()
        valuation_curves = pd.DataFrame()

    data["schedule_curves"] = schedule_curves
    data["valuation_curves"] = valuation_curves


def fix_snapshot_curves(price_curves):
    # Since its snapshots, add Hour 16:
    price_curves.columns = [x.floor("D") + Hour(16) for x in price_curves.columns]

    #contract_prices.loc['M_peak_2024_11', pd.Timestamp("2024-07-24 16:00:00+01:00", tz=tz)]

    # Fix a snpshot price error
    ts_snapshot = pd.Timestamp("2024-07-31 16:00:00+02:00")
    # There is some weird shaping effect, drop this date:
    price_curves = price_curves.loc[:, price_curves.columns != ts_snapshot]

    return price_curves
