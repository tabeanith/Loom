import pstats

from loom.spooling.source.severe_weather_europe.run import SevereWeatherEurope
from loom.spooling.source.theguardian.run import TheGuardian
from loom.spooling.source.reuters.run import Reuters

from loom.data.ibkr.api import read_dataframe

from loom.spooling.topics.t01_eu_power.topic import T01_EU_Power
from loom.spooling.topics.t02_weather.topic import T02_Weather
from loom.spooling.topics.t03_gas_fuel.topic import T03_Gas_Fuel
from loom.spooling.topics.t10_us_rates.topic import T10_US_Rates
from loom.spooling.topics.t11_us_stocks.topic import T11_US_Stocks

from loom.spooling.llm.ask_and_answer import TBD_ask_and_save_answer
from loom.spooling.llm.ask_and_answer import ask_and_answer_for_uuid

from loom.spooling.source.references import load_references

from loom.spooling.analyse_scores import calculate_sentiment_v1
from loom.spooling.analyse_scores import calculate_sentiment_vn
from loom.spooling.analyse_utils import calculate_mtm_from_buy_sell
from loom.spooling.analyse_utils import calculate_mtm_from_open_position
from loom.spooling.analyse_utils import get_bounded_open_volume
from loom.spooling.analyse_utils import generate_closing_profile_from_trade_signals
from loom.utils.kernel import numba_rolling_quantile_q_value


import pandas as pd
import numpy as np
from datetime import date
from pandas.tseries.offsets import Day
tz = "Europe/Berlin"

from matplotlib import pyplot as plt




"""
        idxUS = scoreH.index.tz_convert(tz='US/Eastern')
        is_friday_evening = (idxUS.dayofweek == 4) & (idxUS.hour >= 16)   # Friday evening
        sentiment_exposure = (idxUS.hour >= 7) & (idxUS.hour <= 20) & ~is_friday_evening
        sentiment_exposure = idxUS.hour >= 0
"""


if __name__ == "__main__":

    topic10 = T10_US_Rates()
    topic11 = T11_US_Stocks()

    # For debugging only
    if True:

        #  ----------------------------------------------  Market prices  ------------------------------------------
        ts_go = pd.Timestamp(date(2026, 8, 1), tz=tz)

        symbol = "ES"
        #symbol = "MGC"
        tf = "5min"
        df = read_dataframe(symbol, tf)
        _df = df[df.index > ts_go]
        prices = _df["open"].resample("h").first()
        prices = prices.dropna()

        #  ----------------------------------------------  Market sentiment  ---------------------------------------


