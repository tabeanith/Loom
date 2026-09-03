import pstats

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
from loom.spooling.analyse_utils import get_bounded_open_volume
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
        ts_go = pd.Timestamp(date(2026, 5, 1), tz=tz)

        symbol = "ES"
        #symbol = "MGC"
        tf = "5min"
        df = read_dataframe(symbol, tf)
        _df = df[df.index > ts_go]
        prices = _df["open"].resample("h").first()
        prices = _df["open"]#.resample("h").first()


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

        pricesQ = numba_rolling_quantile_q_value(prices.to_numpy(dtype=np.float32), 12*24*3)
        pricesQ = pd.Series(index=prices.index, data=pricesQ)

        buys = (sentiment < 0) & (pricesQ < 0.4)
        sells = ((sentiment < 0) & (pricesQ > 0.6))

        mtm, open_volume = calculate_mtm_from_buy_sell(buys, sells, prices)
        _open_volume = (open_volume / 10.).astype(int) * 2.
        mtm, open_volume = calculate_mtm_from_open_position(_open_volume, prices)


        # Check boundaries on open_volume and adjust trading:
        roof = 12.
        _idx_sentiment = sentiment / 100.
        maximum =   _idx_sentiment
        minimum =   _idx_sentiment
        ind_sentiment = _idx_sentiment * roof
        _minimum = ind_sentiment #+ minimum
        _maximum = ind_sentiment #+ maximum
        _minimum = _minimum.clip(upper=0).clip(lower=-roof)
        _maximum = _maximum.clip(lower=0).clip(upper=+roof)
        _maximum = pd.Series(index=sentiment.index, data=200)
        _minimum = _maximum * -1.

        open_volume_bounded = get_bounded_open_volume(open_volume, _maximum, _minimum)
        mtm, open_volume = calculate_mtm_from_open_position(open_volume_bounded / 200. * 10., prices)

        print("mtm", mtm.iloc[-1])
        print("pips trading", mtm.iloc[-1] / open_volume[open_volume != 0].abs().mean())
        print("pips market", prices.iloc[-1] - prices.iloc[0])


        #  ----------------------------------------------  Plot  -------------------------------------------------

        fig, (ax1, ax2, ax3) = plt.subplots(nrows=3, sharex=True)
        scores = df_result["score"]

        prices.plot(ax=ax1, label="open", color="black")
        ax2.scatter(x=scores.index, y=scores.values, label="scores", marker='o', linestyle='None')
        ax2.stem(scores.index, scores.values)
        sentiment_bull.plot(ax=ax2, label="sentiment_bull", color="green")
        (-sentiment_bear).plot(ax=ax2, label="sentiment_bear", color="red")
        sentiment.plot(ax=ax2, label="sentiment", color="orange")
        ax2.axhline(y=0, color='black', linewidth=0.8, linestyle='-')

        open_volume.plot(ax=ax2, label="open_volume", color="blue")
        _maximum.plot(ax=ax2, label="mtm", color="blue", linestyle='--')
        _minimum.plot(ax=ax2, label="mtm", color="blue", linestyle='--')


        mtm.plot(ax=ax3, label="mtm", color="black")



        plt.legend()
        plt.show()


