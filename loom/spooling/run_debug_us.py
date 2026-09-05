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







if __name__ == "__main__":

    topic = T10_US_Rates()

    # For debugging only
    if True:

        #  ----------------------------------------------  Market prices  ------------------------------------------
        ts_go = pd.Timestamp(date(2026, 8, 20), tz=tz)

        symbol = "NQ"
        #symbol = "MGC"
        tf = "5min"
        df = read_dataframe(symbol, tf)
        _df = df[df.index > ts_go]
        prices = _df["open"].resample("5min").first()
        prices = _df["open"].resample("5min").first()
        prices = prices.dropna()


        #  ----------------------------------------------  Market sentiment  ---------------------------------------

        uuid = "4d48a78c-0d3b-5598-b452-d15591ac80d2"
        #ask_and_answer_for_uuid(topic, uuid=uuid, use_ai=True)
        txt = topic.load_llm_answer(uuid)
        print(txt)
        df_ref = topic.generate_references()
        df_result = topic.calculate_scores(df_ref)
        df_result = df_result.dropna(axis=0)

        df_result["hours"] = df_result.index.ceil("5min")
        scoreH = df_result.groupby(by="hours")["score"].mean()
        sentimentH = df_result.groupby(by="hours")["sentiment"].mean()

        scoreHmean = scoreH.rolling(10).mean()#.reindex(prices.index).ffill()
        sentimentHmean = sentimentH.rolling(10).mean()#.reindex(prices.index).ffill()

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



        buys1 = (scoreH - scoreHmean).clip(lower=0)
        sells1 = (scoreH - scoreHmean).clip(upper=0) * -1.
        mtm, open_volume = calculate_mtm_from_buy_sell(buys1, sells1, prices)
        #_open_volume = (open_volume / 1.).astype(int) * 5.
        open_volume_bounded = get_bounded_open_volume(open_volume, _maximum, _minimum)
        mtm2, open_volume2 = calculate_mtm_from_open_position(open_volume_bounded / 200. * 10., prices)






        result_mtm =  mtm1 + mtm2
        result_open_volume = open_volume1 + open_volume2
        print("mtm", result_mtm.iloc[-1])
        print("pips trading", result_mtm.iloc[-1] / result_open_volume[result_open_volume != 0].abs().mean())
        print("pips market", prices.iloc[-1] - prices.iloc[0])


        #  ----------------------------------------------  Plot  -------------------------------------------------

        fig, (ax1, ax2, ax3, ax4) = plt.subplots(nrows=4, sharex=True)
        scores = df_result["score"]

        prices.plot(ax=ax1, label="open", color="black")
        ax2.scatter(x=scores.index, y=scores.values, label="scores", marker='o', linestyle='None')
        ax2.stem(scores.index, scores.values)
        scoreHmean.plot(ax=ax2, label="scoreHmean", color="blue")
        sentimentH.plot(ax=ax2, label="sentimentH", color="cyan")
       # (-sentiment_bear).plot(ax=ax2, label="sentiment_bear", color="red")
        #sentiment.plot(ax=ax2, label="sentiment", color="orange")
        ax2.axhline(y=0, color='black', linewidth=0.8, linestyle='-')

        _maximum.plot(ax=ax2, label="mtm", color="blue", linestyle='--')
        _minimum.plot(ax=ax2, label="mtm", color="blue", linestyle='--')


        result_open_volume.plot(ax=ax3, label="open_volume", color="blue")
        ax3.axhline(y=0, color='black', linewidth=0.8, linestyle='-')

        result_mtm.plot(ax=ax4, label="mtm", color="black")



        plt.legend()
        plt.show()


