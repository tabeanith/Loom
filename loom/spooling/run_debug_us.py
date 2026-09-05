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
        prices = _df["open"].resample("5min").first()
        prices = prices.dropna()

        #  ----------------------------------------------  Market sentiment  ---------------------------------------

        #uuid = "4d48a78c-0d3b-5598-b452-d15591ac80d2"
        #ask_and_answer_for_uuid(topic, uuid=uuid, use_ai=True)
        #txt = topic.load_llm_answer(uuid)
        #print(txt)
        df10 = topic10.calculate_scores(topic10.generate_references()).dropna(axis=0)
        df11 = topic11.calculate_scores(topic11.generate_references()).dropna(axis=0)
        df11 = df11[df11["relevance"] == 1.]


        df10["tf"] = df10.index.ceil("5min")
        score10 = df10.groupby(by="tf")["score"].mean()
        score10mean = score10.rolling(15).quantile(0.5)#.reindex(prices.index).ffill()


        df11["tf"] = df11.index.ceil("5min")
        score11 = df11.groupby(by="tf")["score"].mean()
        score11mean = score11.rolling(15).quantile(0.5)#.reindex(prices.index).ffill()




        score10 = score11
        score10mean = score11mean
        scalevol = 3
        scalevol = 3

        #  ----------------------------------------------  Strats  -------------------------------------------------

        pricesQ = numba_rolling_quantile_q_value(prices.to_numpy(dtype=np.float32), 24*2)
        pricesQ = pd.Series(index=prices.index, data=pricesQ)

        _maximum = pd.Series(index=prices.index, data=200)
        _minimum = _maximum * -1.

        buys = ( (pricesQ < 0.3)).astype(int) * 1
        sells = (  (pricesQ > 0.7)).astype(int) * 1

        mtm, open_volume = calculate_mtm_from_buy_sell(buys, sells, prices)
        _open_volume = (open_volume / 1.).astype(int) * 2.
        open_volume_bounded = get_bounded_open_volume(_open_volume, _maximum, _minimum)
        mtm1, open_volume1 = calculate_mtm_from_open_position(open_volume_bounded / 200. * 10., prices)



        buys1 = (score10 - score10mean).clip(lower=0) * scalevol
        sells1 = (score10 - score10mean).clip(upper=0) * -1. * scalevol
        mtm, open_volume = calculate_mtm_from_buy_sell(buys1, sells1, prices)
        open_volume_bounded = get_bounded_open_volume(open_volume, _maximum, _minimum)
        mtm2, open_volume2 = calculate_mtm_from_open_position(open_volume_bounded / 200. * 10., prices)






        result_mtm = mtm2 #  mtm1 + mtm2
        #result_mtm = mtm1 #+ mtm2
        result_open_volume = open_volume2 # open_volume1 + open_volume2
        #result_open_volume = open_volume1 #+ open_volume2
        print("mtm", result_mtm.iloc[-1])
        print("pips trading", result_mtm.iloc[-1] / result_open_volume[result_open_volume != 0].abs().mean())
        print("pips market", prices.iloc[-1] - prices.iloc[0])


        #  ----------------------------------------------  Plot  -------------------------------------------------

        fig, (ax1, ax2, ax3, ax4) = plt.subplots(nrows=4, sharex=True)
        score10 = df10["score"]

        prices.plot(ax=ax1, label="open", color="black")
        ax2.scatter(x=score10.index, y=score10.values, label="score10", marker='o', linestyle='None')
        ax2.stem(score10.index, score10.values)
        score10mean.plot(ax=ax2, label="score10mean", color="blue")
        score10.plot(ax=ax2, label="score10", color="cyan")
       # (-sentiment_bear).plot(ax=ax2, label="sentiment_bear", color="red")
        #sentiment.plot(ax=ax2, label="sentiment", color="orange")
        ax2.axhline(y=0, color='black', linewidth=0.8, linestyle='-')
        #_maximum.plot(ax=ax3, label="mtm", color="blue", linestyle='--')
        #_minimum.plot(ax=ax3, label="mtm", color="blue", linestyle='--')


        result_open_volume.plot(ax=ax3, label="open_volume", color="blue")
        ax3.axhline(y=0, color='black', linewidth=0.8, linestyle='-')

        result_mtm.plot(ax=ax4, label="mtm", color="black")



        plt.legend()
        plt.show()


