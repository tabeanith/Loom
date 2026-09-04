
from loom.spooling.source.severe_weather_europe.run import SevereWeatherEurope
from loom.spooling.source.theguardian.run import TheGuardian
from loom.spooling.source.reuters.run import Reuters

from loom.spooling.topics.t01_eu_power.topic import T01_EU_Power
from loom.spooling.topics.t02_weather.topic import T02_Weather
from loom.spooling.topics.t03_gas_fuel.topic import T03_Gas_Fuel
from loom.spooling.topics.t11_us_stocks.topic import T11_US_Stocks

from loom.spooling.llm.ask_and_answer import ask_and_save_answer
from loom.spooling.llm.ask_and_answer import ask_and_answer_for_uuid

from loom.spooling.source.references import load_references
from loom.spooling.analyse_scores import calculate_sentiment_v1

import pandas as pd
import numpy as np
from pandas.tseries.offsets import Day
tz = "Europe/Berlin"

from matplotlib import pyplot as plt




if __name__ == "__main__":

    df1 = load_references("severe_weather_europe")
    df2 = load_references("theguardian")
    df3 = load_references("reuters")

    df = pd.concat([df1, df2, df3])
    df = df.sort_values("timestamp", ascending=False)

    topic_eu = T01_EU_Power()
    topic_weather = T02_Weather()
    topic_gas_fuel = T03_Gas_Fuel()


    df_score0 = topic_eu.calculate_scores(df)
    #df_score1 = topic_weather.calculate_scores(df)
    #df_score2 = topic_gas_fuel.calculate_scores(df)
    #df_scores = pd.concat([df_score0, df_score1, df_score2]).sort_values("timestamp", ascending=False)
    df_scores = df_score0

    uuid = "79d025c8-b1c9-52c0-a619-3a10498d1cda"
    txt = topic_eu.load_llm_answer(uuid)


    # For debugging only
    if True:
        sentiment = calculate_sentiment_v1(df_scores, 3)


        fig, (ax1, ax2) = plt.subplots(nrows=2, sharex=True)
        scores = df_score0["score"]


        ax2.scatter(x=scores.index, y=scores.values, label="scores", marker='o', linestyle='None')
        ax2.stem(scores.index, scores.values)
        sentiment.plot(ax=ax2, label="sentiment", color="red")

        plt.legend()
        plt.show()


