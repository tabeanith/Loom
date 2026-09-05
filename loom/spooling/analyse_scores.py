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

from loom.spooling.source.references import load_references

from loom.spooling.topics.t01_eu_power.topic import T01_EU_Power
from loom.spooling.topics.t02_weather.topic import T02_Weather
from loom.spooling.topics.t03_gas_fuel.topic import T03_Gas_Fuel
from loom.spooling.topics.t11_us_stocks.topic import T11_US_Stocks

from loom.spooling.source.reuters.run import Reuters

from loom.data.keys import Keys
from loom.data.curves.get import read_curves_from_onedrive
from loom.data.curves.get import extend_snapshot_days_to_today



pio.renderers.default = "browser"
tz = "Europe/Berlin"


def create_plot(
        ts_contract,
        df_prices_power,
        df_scores,
        df_contract_sentiment,
        map_contract_to_score,
        list_of_topics,
        list_of_colors,
        ):
    fig = go.Figure()

    custom_colorscale = [
        [0.0, "#331D75"],
        [0.5, "#FFFFFF"],
        [1.0, "#331D75"],
    ]


    # Score dots
    x = df_scores[ts_contract].index
    y = df_scores[ts_contract].values
    fig.add_trace(go.Scatter(
        x=x,
        y=y,
        mode="markers",
        marker=dict(
            size=7,
            color=y,  # color by value
            colorscale=custom_colorscale,
            showscale=True,
            cmax=100,
            cmin=-100,
        )
    ))


    # Sentiment line
    fig.add_trace(go.Scatter(
        x=df_contract_sentiment[ts_contract].index,
        y=df_contract_sentiment[ts_contract].values,
        mode="lines+markers",
        line=dict(
            width=2.5,
        ),
        marker=dict(
            size=5,
            color="red",
        )
    ))


    # Power prices
    fig.add_trace(go.Scatter(
        x=df_prices_power[ts_contract].index,
        y=df_prices_power[ts_contract].values,
        mode="lines+markers",
        line=dict(
            width=2.5,
        ),
        marker=dict(
            size=5,
            color="#331D75",
        )
    ))


    for topic, topic_color in zip(list_of_topics, list_of_colors):
        data = df_scores[df_scores["topic"] == topic.get_name()]

        x = data["timestamp"].values
        y = data[map_contract_to_score[ts_contract]].values

        # Add vertical lines from 0 to each point
        for xi, yi in zip(x, y):
            fig.add_shape(
                type="line",
                x0=xi, x1=xi,
                y0=0, y1=yi,
                line=dict(color=topic_color,
                          width=1,
                          )
            )

    # Shade weekends (Saturday=5, Sunday=6)
    ts_first = df_prices_power.index[0]
    ts_last = df_prices_power.index[-1]
    days = pd.date_range(pd.Timestamp(ts_last).floor("D"), pd.Timestamp(ts_first).ceil("D"), freq="D")
    for _ts in days:
        _ts = pd.Timestamp(_ts)
        if _ts.dayofweek == 5:  # Saturday: shade Sat + Sun as one block
            fig.add_vrect(
                x0=_ts,
                x1=_ts + pd.Timedelta(days=2),
                fillcolor="#442196",
                opacity=0.2,
                layer="below",  # draw behind the data
                line_width=0  # no border line
            )
        if _ts.day == 1:  # Saturday: shade Sat + Sun as one block
            fig.add_vline(
                x=_ts,
                fillcolor="black",
                opacity=1,
            )

    # Optional: add a horizontal reference line at y=0
    fig.add_hline(y=0, line=dict(color="white", width=3))

    fig.update_layout(title=f"Forward contract {ts_contract.strftime("%Y %B")} Base")
    fig.show()



def calculate_sentiment_vn(df_score, df_out_idx, lookback_days):
    # ---------------------- Get sentiment scoring -----------------------------
    df_contract_sentiment = pd.DataFrame(index=df_out_idx.index, columns=df_out_idx.columns)
    map_contract_to_score = {}
    relevance = df_score["relevance"]

    for ts_contract in df_out_idx.columns:
        # For the sentiment, always look to the next closest contract (relevant for Weeklies, doesnt affect Months and Quarters. Quarters will look at their first month inside)
        ts_ahead = (ts_contract + Day(7))
        _ts_contract_for_sentiment = pd.Timestamp(date(ts_ahead.year, ts_ahead.month, 1), tz=tz)

        if _ts_contract_for_sentiment in df_score.columns:
            _df_score = df_score[_ts_contract_for_sentiment]
            reduction = pd.Series(index=df_out_idx.index, data=np.nan)

            for ts in reduction.index:
                ts_from = ts.floor("D") - Day(lookback_days)
                # TODO: 16 Uhr is snapshot time, but earlier doesnt make a huge difference
                ts_to = ts.floor("D") + Hour(10)
                mask = (_df_score.index >= ts_from) & (_df_score.index <= ts_to)
                __df_score = _df_score[mask]
                __relevance = relevance[mask]
                _s = (__df_score * __relevance).sum()
                _r = __relevance.sum()
                if _r > 0:
                    reduction.loc[ts] = (__df_score * __relevance).sum() / __relevance.sum()

            df_contract_sentiment[ts_contract] = reduction
            map_contract_to_score[ts_contract] = _ts_contract_for_sentiment

    df_contract_sentiment = df_contract_sentiment.fillna(0)

    return df_contract_sentiment, map_contract_to_score



def calculate_sentiment_v1(df_score, df_out_idx, lookback_days):
    # ---------------------- Get sentiment scoring -----------------------------
    sentiment = pd.Series(index=df_out_idx.index, data=np.nan)

    scores = df_score["score"]
    relevance = df_score["relevance"]

    # For the sentiment, always look to the next closest contract (relevant for Weeklies, doesnt affect Months and Quarters. Quarters will look at their first month inside)

    for ts in sentiment.index:
        ts_from = ts.floor("D") - Day(lookback_days)
        ts_to = ts
        mask = (scores.index >= ts_from) & (scores.index <= ts_to)
        __score = scores[mask]
        __relevance = relevance[mask]
        __medianmed = (__score * __relevance).sum() / __relevance.sum()
        sentiment.loc[ts] = __medianmed

    sentiment = sentiment.fillna(0)
    return sentiment



if __name__ == "__main__":
    curves = {}

    topic_eu = T01_EU_Power()
    topic_weather = T02_Weather()
    topic_gas_fuel = T03_Gas_Fuel()


    list_of_topics = [topic_weather, topic_gas_fuel]
    list_of_colors = ["blue", "orange"]

    #df_score0 = topic_eu.calculate_scores(df)
    df_score1 = topic_weather.calculate_scores(topic_weather.generate_references())
    df_score2 = topic_gas_fuel.calculate_scores(topic_gas_fuel.generate_references())

    #for col in df_score1.columns:
    #    if isinstance(col, pd.Timestamp):
    #        df_score0[col] = df_score0["score"]


    df_scores = pd.concat([df_score1, df_score2]).sort_values("timestamp", ascending=False)


    curves_power = read_curves_from_onedrive(f"data_historical_2024+", Keys.power_germany)
    curves_power = extend_snapshot_days_to_today(curves_power)


    # Reduction for Monthlies

    contract_sample = "MS"

    df_prices_power = curves_power.resample(contract_sample).mean().T


    df_contract_sentiment, map_contract_to_score = calculate_sentiment_vn(df_scores, df_prices_power, 7)



    # Plot datat for a single contract
    ts_contract = pd.Timestamp(date(2026, 12, 1), tz=tz)

    create_plot(ts_contract, df_prices_power, df_scores, df_contract_sentiment, map_contract_to_score,list_of_topics, list_of_colors)



    print(df_scores)
    print(df_score1)
    print(df_score2)



