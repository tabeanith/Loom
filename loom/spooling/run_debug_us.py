
from loom.spooling.source.severe_weather_europe.run import SevereWeatherEurope
from loom.spooling.source.theguardian.run import TheGuardian
from loom.spooling.source.reuters.run import Reuters

from loom.data.ibkr.api import read_dataframe

from loom.spooling.topics.t01_eu_power.topic import T01_EU_Power
from loom.spooling.topics.t02_weather.topic import T02_Weather
from loom.spooling.topics.t03_gas_fuel.topic import T03_Gas_Fuel
from loom.spooling.topics.t11_us_stocks.topic import T11_US_Stocks

from loom.spooling.llm.ask_and_answer import ask_and_answer
from loom.spooling.llm.ask_and_answer import ask_and_answer_for_uuid

from loom.spooling.source.references import load_references

from loom.spooling.analyse_scores import calculate_sentiment_v1
from loom.spooling.analyse_scores import calculate_sentiment_vn
from loom.spooling.analyse_utils import calculate_mtm_from_buy_sell
from loom.spooling.analyse_utils import calculate_mtm_from_open_position
from loom.utils.kernel import numba_rolling_quantile_q_value


import pandas as pd
import numpy as np
from datetime import date
from pandas.tseries.offsets import Day
tz = "Europe/Berlin"

from matplotlib import pyplot as plt







if __name__ == "__main__":

    topic = T11_US_Stocks()
    scraper = Reuters()

    # For debugging only
    if True:

        #  ----------------------------------------------  Market prices  ------------------------------------------
        ts_go = pd.Timestamp(date(2026, 8, 1), tz=tz)

        symbol = "NQ"
        symbol = "MGC"
        tf = "5min"
        df = read_dataframe(symbol, tf)
        _df = df[df.index > ts_go]
        prices = _df["open"].resample("h").first()


        #  ----------------------------------------------  Market sentiment  ---------------------------------------

        uuid = "fb856271-5499-5b06-95c8-52c51da0728b"
        ask_and_answer_for_uuid(topic, uuid=uuid, use_ai=True)
        txt = topic.load_llm_answer(uuid)
        print(txt)
        df_ref = load_references(scraper.get_folder())
        df_result = topic.calculate_scores(df_ref)

        sentiment = calculate_sentiment_v1(df_result, prices, 7)
        sentiment_bull = calculate_sentiment_v1(df_result[df_result["score"] > 0], prices,  7)
        sentiment_bear = calculate_sentiment_v1(df_result[df_result["score"] < 0], prices,  7)
        sentiment_diff = sentiment_bull.reindex(df_result.index).ffill().diff() + sentiment_bear.reindex(df_result.index).ffill().diff()


        #  ----------------------------------------------  Strats  -------------------------------------------------

        pricesQ = numba_rolling_quantile_q_value(prices.to_numpy(dtype=np.float32), 24*5)
        pricesQ = pd.Series(index=prices.index, data=pricesQ)

        buys = (sentiment < 0) & (pricesQ < 0.2)
        sells = (sentiment < 0) & (pricesQ > 0.8)
        _mtm, _open_volume = calculate_mtm_from_buy_sell(buys, sells, prices)
        _open_volume = (_open_volume / 10.).astype(int)

        mtm, open_volume = calculate_mtm_from_open_position(_open_volume, prices)

        print(mtm.iloc[-1])


        #  ----------------------------------------------  Plot  -------------------------------------------------

        fig, (ax1, ax2, ax3) = plt.subplots(nrows=3, sharex=True)
        scores = df_result["score"]

        prices.plot(ax=ax1, label="open", color="black")
        ax2.scatter(x=scores.index, y=scores.values, label="scores", marker='o', linestyle='None')
        ax2.stem(scores.index, scores.values)
        sentiment_bull.plot(ax=ax2, label="sentiment_bull", color="green")
        (-sentiment_bear).plot(ax=ax2, label="sentiment_bear", color="red")
        sentiment.plot(ax=ax2, label="sentiment", color="orange")

        open_volume.plot(ax=ax2, label="open_volume", color="blue")

        mtm.plot(ax=ax3, label="mtm", color="black")


        plt.legend()
        plt.show()


