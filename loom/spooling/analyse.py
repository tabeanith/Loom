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

from loom.spooling.topics.t01_weather.topic import T01_Weather
from loom.spooling.topics.t02_gas_fuel.topic import T02_Gas_Fuel

from loom.data.keys import Keys
from loom.data.curves.get import read_curves_from_onedrive



pio.renderers.default = "browser"
tz = "Europe/Berlin"


def create_plot(list_of_scores, list_of_topics, list_of_colors, prices, implied, ts_forward):
    fig = go.Figure()

    custom_colorscale = [
        [0.0, "#331D75"],
        [0.5, "#FFFFFF"],
        [1.0, "#331D75"],
    ]

    for df_score, topic, topic_color in zip(list_of_scores, list_of_topics, list_of_colors):
        x = df_score["timestamp"].values
        y = df_score[ts_forward].values

        # opens in your default web browser
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

        # prices
        if prices is not None:
            fig.add_trace(go.Scatter(
                x=prices.index,
                y=prices.values,
                mode="lines+markers",
                marker=dict(
                    size=5,
                    color="#331D75",
                )
            ))

        # implied
        if implied is not None:
            fig.add_trace(go.Scatter(
                x=implied.index,
                y=implied.values,
                mode="lines+markers",
                marker=dict(
                    size=5,
                    color="red",
                )
            ))
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
    df_score = list_of_scores[0]
    ts_first = df_score["timestamp"].values[0]
    ts_last = df_score["timestamp"].values[-1]
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

    fig.update_layout(title=f"Forward contract {ts_forward.strftime("%Y %B")} Base")
    fig.show()


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





if __name__ == "__main__":
    curves = {}

    df1 = load_references("severe_weather_europe")
    df2 = load_references("theguardian")
    df3 = load_references("reuters")

    df = pd.concat([df1, df2, df3])
    df = df.sort_values("timestamp", ascending=False)

    topic_weather = T01_Weather()
    topic_gas_fuel = T02_Gas_Fuel()


    df_score1 = topic_weather.calculate_scores(df)
    df_score2 = topic_gas_fuel.calculate_scores(df)
    df_score = pd.concat([df_score1, df_score2]).sort_values("timestamp", ascending=False)


    curves_power = read_curves_from_onedrive(f"data_historical_2024+", Keys.power_germany)


    # Extent curves to today to have the news median today:
    columns = curves_power.columns
    today = pd.Timestamp.today(tz=tz)
    extended_trading_days = pd.bdate_range(columns[-1], today)
    new_columns = columns.append(extended_trading_days).unique()
    curves_power = curves_power.reindex(columns=new_columns)



    def run_test(curves_power, contract_sample, ts_contract, ts_start_trading, n_contracts: int, force_close_delivery=False, show_plot=False):
        n_contracts = max(1, n_contracts)

        # ---------------------- Get historical prices and power price curve -----------------------------
        prices_power = curves_power.resample(contract_sample).mean().T[ts_contract]

        mask1 = prices_power.index.date >= ts_start_trading.date()
        mask2 = prices_power.index.date < ts_contract.date()
        mask_trading = mask1 & mask2


        # ---------------------- Get sentiment scoring -----------------------------

        # For the sentiment, always look ahead slightly (relevant for Weeklies, doesnt affect Months and Quarters)
        ts_ahead = (ts_contract + Day(6))
        ts_contract_for_sentiment = pd.Timestamp(date(ts_ahead.year, ts_ahead.month, 1), tz=tz)

        if ts_contract_for_sentiment in df_score.columns:
            _df_score = df_score[ts_contract_for_sentiment]
            score_reduction = pd.Series(index=prices_power.index, data=np.nan)

            for ts in score_reduction.index:
                ts_from = ts.floor("D") - Day(7)
                ts_to = ts.floor("D") + Hour(16)
                __df_score = _df_score[(_df_score.index >= ts_from) & (_df_score.index <= ts_to)]
                __medianmed = __df_score.median()
                __median1 = __df_score.quantile(0.9)
                __median3 = __df_score.quantile(0.1)

                score_reduction.loc[ts] = (0.333 * __medianmed + 0.333 * __median1 + 0.333 * __median3)

            scores = _df_score
        else:
            scores = pd.Series(index=prices_power.index)
            score_reduction = pd.Series(index=prices_power.index)

        scores = scores.fillna(0)
        score_reduction = score_reduction.reindex(index=prices_power.index).fillna(0)


        # ------------------------------------- Trading -----------------------------------
        upper = (prices_power.rolling(7).quantile(0.75))
        middle = (prices_power.rolling(7).quantile(0.5))
        lower = (prices_power.rolling(7).quantile(0.27))


        # Normal selling and buying
        buy1 = (prices_power < lower).astype(int) * n_contracts
        buys = buy1

        sell1 = (prices_power > upper).astype(int) * n_contracts
        sells = sell1


        # TODO: Bull run. Implement the same for bear run
        past = (prices_power > upper).astype(int).rolling(7).mean() > 0.75
        sellsingular = (prices_power < middle)
        sellX = (past & sellsingular).astype(int) * 6 * n_contracts

        buyX = (prices_power < middle).astype(int) * 3 * n_contracts

        # From buys and sells, weight them based on sentinemt:
        scaled_buy = buys * (1. - score_reduction/100.) + buyX * (score_reduction/100.)
        scaled_sell = sells * (1. - score_reduction/100.) + sellX * (score_reduction/100.)

        scaled_buy = scaled_buy[mask_trading]
        scaled_sell = scaled_sell[mask_trading]
        _traded_prices = prices_power[mask_trading]

        mtm, open_volume = calculate_mtm_from_buy_sell(scaled_buy, scaled_sell, _traded_prices)

        # TODO: Bear run!!!



        # Check boundaries on open_volume and adjust trading:
        maximum = +15 * n_contracts
        minimum = -15 * n_contracts
        ind_sentiment = score_reduction / 100. * n_contracts * 15
        _minimum = ind_sentiment + minimum
        _maximum = ind_sentiment + maximum
        _minimum = _minimum.clip(upper=0)
        _maximum = _maximum.clip(lower=0)

        open_volume2 = open_volume
        mtm2 = mtm

        if len(open_volume) > 0:
            bounded_volume = pd.Series(index=open_volume.index, data=0.)
            open_volume_change = open_volume.diff()
            open_volume_change.iloc[0] = open_volume.iloc[0]

            bounded_volume.iloc[0] = open_volume.iloc[0]
            for i, change in enumerate(open_volume_change.values):
                if i == 0: continue
                prev = bounded_volume.iloc[i-1]
                new = prev + change
                if new > maximum:
                    bounded_volume.iloc[i] = maximum
                elif new < minimum:
                    bounded_volume.iloc[i] = minimum
                else:
                    bounded_volume.iloc[i] = new

            _bounded_volume = bounded_volume.reindex(_traded_prices.index)
            mtm2, open_volume2 = calculate_mtm_from_open_position(_bounded_volume, _traded_prices)


        # TODO: Delivery logic
        open_volume2 = open_volume2.reindex(index=prices_power.index)
        ts_last_trading_days = ts_contract - BDay(5)
        mask_last_trading_week = (open_volume2.index >= ts_last_trading_days) & (open_volume2.index < ts_contract)
        final_positions = open_volume2[mask_last_trading_week]
        final_sentiment = score_reduction[mask_last_trading_week]

        if (not final_positions.empty) and (not final_sentiment.empty):
            x_pos = final_positions.mean()
            x_sen = final_sentiment.mean()
            print(f"Contract {ts_contract} --- Delivery Check: {x_pos} MW, sentiment {x_sen}")

            if (x_pos > 0) & (x_sen > 33) & (not force_close_delivery):  # TODO: pick sensible values
                print(f"Contract {ts_contract}: Take into delivery")
            elif (x_pos < 0) & (x_sen < 0) & (not force_close_delivery):  # TODO: pick sensible values
                print(f"Contract {ts_contract}: Take into delivery")
            else:
                print(f"Contract {ts_contract}: Close positions before delivery")
                # Mismatch: Start closing the position:
                position_at_first = final_positions.iloc[0]
                tdays_left_until_delivery = (final_positions.index - ts_contract).days * -1
                position_target = position_at_first * (tdays_left_until_delivery - 1.) / 5.
                position_target = position_target.astype(int)
                # Start closing
                open_volume2.loc[mask_last_trading_week] = position_target.values
        else:
            print(f"not yet delivered, or sentiment data empty:", final_positions.empty, final_sentiment.empty)

        # Recalculate buys and sells -- Either way the position is unchanged into delivery, or adjusted, but we have to calculate the pnl into delivery anyway
        deliv_open_volume = open_volume2.reindex(index=prices_power.index).ffill().fillna(0)

        mtmfinal, open_volumefinal = calculate_mtm_from_open_position(deliv_open_volume, _traded_prices)
        mtmfinal = mtmfinal.ffill()


        if len(mtmfinal) > 0:
            print(f"Contract {ts_contract} mtm:", mtmfinal.iloc[-1])

        if show_plot:
            fig, (ax1, ax2, ax3) = plt.subplots(nrows=3, sharex=True)


            prices_power.plot(ax=ax1, label="prices", color="black")
            upper.plot(ax=ax1, label="prices0.8")
            middle.plot(ax=ax1, label="prices0.5")
            lower.plot(ax=ax1, label="prices0.2")


            ax2.scatter(x=scores.index, y=scores.values, label="scores", marker='o', linestyle='None')
            ax2.stem(scores.index, scores.values)

            vol = 1
            (vol*open_volumefinal).plot(ax=ax2, label="open_volumefinal", color="black")
            (vol*scaled_buy).plot(ax=ax2, label="scaled_buy", color="green")
            (vol*scaled_sell).plot(ax=ax2, label="scaled_sell", color="red")
            score_reduction.plot(ax=ax2, label="score_reduction", color="orange")

            (vol * mtmfinal * 31 * 24).plot(ax=ax3, label="mtm")
            ax3.axhline(y=0.0, color='r', linestyle='-')

            plt.legend()
            plt.show()

        return mtmfinal, open_volumefinal, score_reduction




    ts_contract = pd.Timestamp(date(2026, 9, 1), tz=tz)
    ts_start_trading = ts_contract - MonthBegin(4)
    n_contracts = 5
    contract_sample = "MS"

    mtm, open_volume, score_reduction = run_test(curves_power, contract_sample, ts_contract, ts_start_trading, n_contracts, force_close_delivery=False, show_plot=True)
    print(mtm.iloc[-1])




    mtm_total = []
    contract_sample = "QS"
    hours = 24 * 30 * 3
    n_contracts = 3
    all_open_volume = []

    for ts_contract in pd.date_range(pd.Timestamp(date(2026, 1, 1), tz=tz), pd.Timestamp(date(2027, 9, 1), tz=tz), freq=contract_sample):
        ts_start_trading = ts_contract - MonthBegin(12)
        print(ts_contract, ts_start_trading)


        mtm, open_volume, score_reduction = run_test(curves_power, contract_sample, ts_contract, ts_start_trading, n_contracts, force_close_delivery=False, show_plot=False)
        mtm.name = ts_contract
        open_volume.name = ts_contract
        mtm_total.append(mtm * hours)
        all_open_volume.append(open_volume)

    _mtm_total = pd.concat(mtm_total, axis=1).ffill(axis=0).fillna(0)
    Q_all_open_volume = pd.concat(all_open_volume, axis=1).fillna(0)
    _mtm_total.plot()
    pnl_allquarters = _mtm_total.sum(axis=1)
    pnl_allquarters.plot(color="black", label="pnl_allquarters")
    print(pnl_allquarters.iloc[-1])
    plt.legend()

    pnl_allquarters[-30:]
    df_relevant_pos = Q_all_open_volume.iloc[-30:, -8:]




    mtm_total = []
    all_open_volume = []
    contract_sample = "MS"
    hours = 24 * 30
    n_contracts = 10

    for ts_contract in pd.date_range(pd.Timestamp(date(2026, 1, 1), tz=tz), pd.Timestamp(date(2027, 12, 1), tz=tz),
                                     freq=contract_sample):
        ts_start_trading = ts_contract - MonthBegin(4)
        mtm, open_volume, score_reduction = run_test(curves_power, contract_sample, ts_contract, ts_start_trading, n_contracts, force_close_delivery=False, show_plot=False)
        mtm.name = ts_contract
        open_volume.name = ts_contract
        mtm_total.append(mtm * hours)
        all_open_volume.append(open_volume)
    _mtm_total = pd.concat(mtm_total, axis=1).ffill(axis=0).fillna(0)
    M_all_open_volume = pd.concat(all_open_volume, axis=1).fillna(0)
    _mtm_total.plot()
    pnl_allmonths = _mtm_total.sum(axis=1)
    pnl_allmonths.plot(color="black", label="pnl_allmonths")
    print(pnl_allmonths.iloc[-1])
    plt.legend()

    pnl_allmonths[-30:]
    df_relevant_pos = M_all_open_volume.iloc[-30:, -8:]

    pnl_total = pnl_allquarters + pnl_allmonths
    pnl_total[-30:]


    pnl_allmonths.plot(color="orange", label="pnl_allmonths")
    pnl_allquarters.plot(color="blue", label="pnl_allquarters")
    (pnl_allquarters + pnl_allmonths).plot(color="black", label="Total")






    mtm_total = []
    contract_sample = 'W-SUN'
    hours = 24 * 7
    n_contracts = 50

    for ts_contract in pd.date_range(pd.Timestamp(date(2024, 1, 1), tz=tz), pd.Timestamp(date(2027, 12, 1), tz=tz),
                                     freq=contract_sample):
        ts_start_trading = ts_contract - Day(14)
        mtm, open_volume, score_reduction = run_test(curves_power, contract_sample, ts_contract, ts_start_trading, n_contracts, force_close_delivery=False, show_plot=False)
        mtm_total.append(mtm * hours)
    _mtm_total = pd.concat(mtm_total, axis=1).ffill(axis=0).fillna(0)
    weeks = _mtm_total.sum(axis=1)
    weeks.plot(color="black", label="weeks")
    plt.legend()

    ts_tradeday = None
    ts_tradeday = pd.Timestamp(date.today(), tz=tz).floor("D") - Day(1)


    print_to_do(M_all_open_volume, ts_tradeday)
    print_to_do(Q_all_open_volume, ts_tradeday)



    def print_to_do(df_open_pos, ts_tradeday=None):
        df_open_pos.index = pd.to_datetime(df_open_pos.index, utc=True).tz_convert(tz).floor("D")

        if ts_tradeday is None:
            ts_tradeday = pd.Timestamp(date.today(), tz=tz).floor("D")

        print("Trade date:", ts_tradeday.date())
        _df_open_pos = df_open_pos[df_open_pos.index <= ts_tradeday.floor("D")]

        currentM = _df_open_pos.iloc[-1]
        diffM = _df_open_pos.iloc[-1] - _df_open_pos.iloc[-2]
        _diffM = diffM[diffM.index > ts_tradeday].iloc[0:6]
        _currentM = currentM[_diffM.index]

        _currentM.name = "Total Position today"
        _diffM.name = "Traded today"
        stack = pd.concat([_currentM, _diffM], axis=1)

        contracts = []
        for ts in stack.index:
            contract_str = f"{ts.year} {ts.month_name()} | M{ts.month} | Q{ts.quarter} "
            contracts.append(contract_str)

        stack.index = contracts

        print(stack)













    print(df_score1)
    print(df_score2)
    ts_contract = pd.Timestamp(date(2026, 9, 1), tz=tz)
    ts_start_trading = ts_contract - MonthBegin(4)
    n_contracts = 5
    contract_sample = "MS"
    mtm, open_volume, score_reduction = run_test(curves_power, contract_sample, ts_contract, ts_start_trading, n_contracts, force_close_delivery=False, show_plot=False)


    # Plotly is for later
    prices_power = curves_power.resample(contract_sample).mean().T[ts_contract]
    create_plot([df_score1, df_score2], [topic_weather, topic_gas_fuel], ["blue", "orange"], prices_power, score_reduction,  ts_contract)








