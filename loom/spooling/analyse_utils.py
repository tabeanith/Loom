import os
import re
from pathlib import Path
import json
import pandas as pd
import numpy as np
from datetime import date
import matplotlib.pyplot as plt

import plotly.io as pio
import plotly.graph_objects as go

from pandas.tseries.offsets import MonthBegin, Day, Hour, Week, BDay


pd.set_option('display.max_rows', 10000)
pd.set_option('display.max_columns', 500)
pd.set_option('display.width', 10000)
pd.set_option('display.max_colwidth', None)


def get_bounded_open_volume(open_volume, maximum_pos, minimum_neg):
    """
        Make sure that open volume is inside max and min boundaries
    :param open_volume:
    :param maximum_pos:
    :param minimum_neg:
    :return:
    """
    if open_volume.empty:
        return open_volume

    bounded_volume = pd.Series(index=open_volume.index, data=0.)
    open_volume_change = open_volume.diff()
    open_volume_change.iloc[0] = open_volume.iloc[0]
    _minimum = minimum_neg.reindex(open_volume.index)
    _maximum = maximum_pos.reindex(open_volume.index)

    bounded_volume.iloc[0] = open_volume.iloc[0]
    for i, change in enumerate(open_volume_change.values):
        if i == 0: continue
        prev = bounded_volume.iloc[i - 1]
        new = prev + change
        maxval = _maximum.iloc[i]
        minval = _minimum.iloc[i]
        if new > maxval:
            bounded_volume.iloc[i] = maxval
        elif new < minval:
            bounded_volume.iloc[i] = minval
        else:
            bounded_volume.iloc[i] = new

    _, _open_volume = calculate_mtm_from_open_position(bounded_volume)
    return _open_volume


def get_delivery_adjusted_open_volume(ts_contract, open_volume, sentiment, force_close_delivery: bool = False):
    _open_volume = open_volume.copy()
    ts_last_trading_days = ts_contract - BDay(5)
    mask_last_trading_week = (open_volume.index >= ts_last_trading_days) & (open_volume.index < ts_contract)
    final_positions = open_volume[mask_last_trading_week]
    final_sentiment = sentiment[mask_last_trading_week]

    if (not final_positions.empty) and (not final_sentiment.empty):
        x_pos = final_positions.mean()
        x_sen = final_sentiment.mean()
        print(f"Contract {ts_contract} --- Delivery Check: {x_pos} MW, sentiment {x_sen}")

        if (x_pos > 0) & (x_sen > 33) & (not force_close_delivery):  # TODO: pick sensible values
            print(f"Contract {ts_contract}: Take into delivery")
        elif (x_pos < 0) & (x_sen < -33) & (not force_close_delivery):  # TODO: pick sensible values
            print(f"Contract {ts_contract}: Take into delivery")
        else:
            print(f"Contract {ts_contract}: Close positions before delivery")
            # Mismatch: Start closing the position:
            position_at_first = final_positions.iloc[0]
            tdays_left_until_delivery = (final_positions.index - ts_contract).days * -1
            position_target = position_at_first * (tdays_left_until_delivery - 1.) / 5.
            position_target = position_target.astype(int)
            # Start closing
            _open_volume.loc[mask_last_trading_week] = position_target.values
    else:
        print(f"Contract {ts_contract}: Too far away from delivery (or no sentiment avail)", final_positions.empty,
              final_sentiment.empty)

    return _open_volume


def calculate_mtm_from_buy_sell(buy_dirac, sell_dirac, prices: pd.Series=None):
    buy_dirac = buy_dirac.reindex(prices.index)
    sell_dirac = sell_dirac.reindex(prices.index)

    buy_dirac = buy_dirac.fillna(0).astype(int)  # Covert floats to integer
    sell_dirac = sell_dirac.fillna(0).astype(int)  # Covert floats to integer

    open_volume = (buy_dirac - sell_dirac).cumsum()
    mtm = pd.Series(index=open_volume.index, data=np.nan)

    if prices is not None:
        entries = (-buy_dirac * prices + sell_dirac * prices).cumsum()
        exits = open_volume * prices
        mtm = entries + exits

    return mtm, open_volume


def calculate_mtm_from_open_position(open_position_profile, prices: pd.Series=None):
    change = open_position_profile.ffill().fillna(0).astype(int).diff()
    change.fillna(open_position_profile, inplace=True)

    buy_dirac = change.clip(lower=0)
    sell_dirac = change.clip(upper=0) * -1
    return calculate_mtm_from_buy_sell(buy_dirac, sell_dirac, prices)

