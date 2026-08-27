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



def calculate_mtm_from_buy_sell(buy_dirac, sell_dirac, prices):
    buy_dirac = buy_dirac.fillna(0).astype(int)  # Covert floats to integer
    sell_dirac = sell_dirac.fillna(0).astype(int)  # Covert floats to integer

    entries = (-buy_dirac * prices + sell_dirac * prices).cumsum()
    open_volume = (buy_dirac - sell_dirac).cumsum()
    exits = open_volume * prices
    mtm = entries + exits
    return mtm, open_volume


def calculate_mtm_from_open_position(open_position_profile, prices):
    change = open_position_profile.ffill().fillna(0).astype(int).diff()
    change.fillna(open_position_profile, inplace=True)

    buy_dirac = change.clip(lower=0)
    sell_dirac = change.clip(upper=0) * -1
    return calculate_mtm_from_buy_sell(buy_dirac, sell_dirac, prices)

