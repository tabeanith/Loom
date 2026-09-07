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

from loom.spooling.topics.t01_eu_power.topic import T01_EU_Power

pd.set_option('display.max_rows', 10000)
pd.set_option('display.max_columns', 500)
pd.set_option('display.width', 10000)
pd.set_option('display.max_colwidth', None)

from loom.spooling.source.references import load_references

from loom.spooling.topics.t02_weather.topic import T02_Weather
from loom.spooling.topics.t03_gas_fuel.topic import T03_Gas_Fuel

from loom.data.keys import Keys
from loom.data.curves.get import read_curves_from_onedrive
from loom.data.curves.get import extend_snapshot_days_to_today

from loom.spooling.analyse_scores import calculate_sentiment_vn
from loom.spooling.analyse_utils import calculate_mtm_from_buy_sell
from loom.spooling.analyse_utils import calculate_mtm_from_open_position
from loom.spooling.analyse_utils import get_bounded_open_volume
from loom.spooling.analyse_utils import get_delivery_adjusted_open_volume
from loom.spooling.analyse_utils import generate_closing_profile_from_trade_signals



pio.renderers.default = "browser"
tz = "Europe/Berlin"




def run_trade_strategy(ts_contract, ts_start_trading, mw_sizing: int, mw_maximum: int, df_prices_power, df_contract_sentiment, df_scores, map_contract_to_score, force_close_delivery=False, show_plot=False):
    n_contracts = max(1, mw_sizing)

    # ---------------------- Get prices and sentiment -----------------------------
    prices_power = df_prices_power[ts_contract]
    idx_sentiment = df_contract_sentiment[ts_contract]

    mask1 = prices_power.index.date >= ts_start_trading.date()
    mask2 = prices_power.index.date < ts_contract.date()
    mask_trading = mask1 & mask2


    # ------------------------- Trading price structure -----------------------------------
    upper = (prices_power.rolling(5).quantile(0.75))
    middle = (prices_power.rolling(5).quantile(0.5))
    lower = (prices_power.rolling(5).quantile(0.25))


    # ------------------------------------------------------- Trading -----------------------------------------------


    # -------------------- STRAT1   Buy/Sell based on price quantiles, weighted with sentiment  ---------------------
    buys = (prices_power < lower).astype(int) * n_contracts
    sells = (prices_power > upper).astype(int) * n_contracts

    # ---------------- STRAT2   Buy/Sell based on strong price extensions, weighted with sentiment ------------------
    # STRAT --- Buying on positive sentiment
    past = (prices_power > upper).astype(int).rolling(5).mean() > 0.75
    sellsingular = (prices_power < middle).astype(int).diff() > 0
    sellX = (past & sellsingular).astype(int) * 5 * n_contracts
    buyX = (prices_power < middle).astype(int) * 2 * n_contracts

    # STRAT --- Selling on negative sentiment
    past = (prices_power < lower).astype(int).rolling(5).mean() > 0.75
    buysingular = (prices_power > middle).astype(int).diff() > 0
    buyY = (past & buysingular).astype(int) * 5 * n_contracts
    sellY = (prices_power > middle).astype(int) * 2 * n_contracts

    scores = pd.Series(index=idx_sentiment.index, data=np.nan)
    impulse_buy = pd.Series(index=idx_sentiment.index, data=0)
    impulse_sell = pd.Series(index=idx_sentiment.index, data=0)
    buys_closing = pd.Series(index=idx_sentiment.index, data=0)
    sells_closing = pd.Series(index=idx_sentiment.index, data=0)

    # -------------------- STRAT3   Buy/Sell based on only data jumps in sentiment  ---------------------
    if ts_contract in map_contract_to_score.keys():
        _scores = df_scores[[map_contract_to_score[ts_contract], "relevance"]]
        _scores["day"] = [x.floor("D") if x.hour < 15 else x.ceil("D") for x in df_scores.index]
        _scores["val"] = _scores[map_contract_to_score[ts_contract]] * _scores["relevance"]

        scores = _scores.groupby("day")["val"].sum() / _scores.groupby("day")["relevance"].sum()
        scores = scores.reindex(idx_sentiment.index).ffill()

        impulse_buy = (scores > idx_sentiment.rolling(10).quantile(0.9)).astype(int) * 10
        impulse_sell = (scores < idx_sentiment.rolling(10).quantile(0.1)).astype(int) * 10
        rw = 5
        buys_closing = generate_closing_profile_from_trade_signals(rw, impulse_buy)
        sells_closing = generate_closing_profile_from_trade_signals(rw, impulse_sell)


    # From buys and sells, weight them based on sentiment:
    idx_sentiment_abs = idx_sentiment.abs() / 100.
    idx_sentiment_bull_abs = idx_sentiment.clip(lower=0).abs() / 100.
    idx_sentiment_bear_abs = idx_sentiment.clip(upper=0).abs() / 100.

    total_buy = buys * (1. - idx_sentiment_abs) + buyX * idx_sentiment_bull_abs + buyY * idx_sentiment_bear_abs + impulse_buy + sells_closing
    total_sell = sells * (1. - idx_sentiment_abs) + sellX * idx_sentiment_bull_abs + sellY * idx_sentiment_bear_abs + buys_closing + impulse_sell

    total_buy = total_buy[mask_trading]
    total_sell = total_sell[mask_trading]
    _traded_prices = prices_power[mask_trading]

    _, open_volume = calculate_mtm_from_buy_sell(total_buy, total_sell)


    # Check boundaries on open_volume and adjust trading:
    maximum = pd.Series(index=idx_sentiment.index, data=100)
    minimum = maximum * -1.
    _idx_sentiment = (idx_sentiment * 2).clip(lower=-100).clip(upper=100)
    _minimum = minimum + _idx_sentiment  # -200
    _maximum = maximum + _idx_sentiment  # 200
    _minimum = _minimum.clip(upper=0)
    _maximum = _maximum.clip(lower=0)
    _minimum = _minimum / 200. * mw_maximum
    _maximum = _maximum / 200. * mw_maximum


    open_volume_bounded = get_bounded_open_volume(open_volume, _maximum, _minimum)
    open_volume_bounded = open_volume_bounded.reindex(index=prices_power.index).ffill().fillna(0)

    # Recalculate buys and sells -- Either way the position is unchanged into delivery, or adjusted, but we have to calculate the pnl into delivery anyway
    open_volume_delived = get_delivery_adjusted_open_volume(ts_contract, open_volume_bounded, idx_sentiment, force_close_delivery=force_close_delivery)
    open_volume_delived = open_volume_delived.ffill().fillna(0)

    result_mtm, result_open_position = calculate_mtm_from_open_position(open_volume_delived, _traded_prices)
    result_mtm = result_mtm.reindex(index=prices_power.index).ffill().fillna(0)

    result_mtm.name = ts_contract
    result_open_position.name = ts_contract


    if len(result_mtm) > 0:
        print(f"Contract {ts_contract} MtM:   ", result_mtm.iloc[-1])

    if show_plot:
        fig, (ax1, ax2, ax3, ax4) = plt.subplots(nrows=4, sharex=True)


        prices_power.plot(ax=ax1, label="prices", color="black")
        upper.plot(ax=ax1, label="prices0.8")
        middle.plot(ax=ax1, label="prices0.5")
        lower.plot(ax=ax1, label="prices0.2")

        # Sentiment
        ax2.scatter(x=scores.index, y=scores.values, label="scores", marker='o', linestyle='None')
        ax2.stem(scores.index, scores.values)

        idx_sentiment.plot(ax=ax2, label="score_reduction", color="orange")
        (idx_sentiment_bull_abs*100.).plot(ax=ax2, label="idx_sentiment_bull_abs", color="lime")
        (idx_sentiment_bear_abs*100.).plot(ax=ax2, label="idx_sentiment_bear_abs", color="red")

        # Positions
        vol = 1
        result_open_position = result_open_position.reindex(prices_power.index).ffill()
        total_buy = total_buy.reindex(prices_power.index).ffill()
        total_sell = total_sell.reindex(prices_power.index).ffill()
        (vol*result_open_position).plot(ax=ax3, label="result_open_position", color="black")#
        (vol*total_buy).plot(ax=ax3, label="total_buy", color="green")
        (vol*total_sell).plot(ax=ax3, label="total_sell", color="red")
        (vol*_maximum).plot(ax=ax3, label="open_pos_maximum", color="black", linestyle="dotted")
        (vol*_minimum).plot(ax=ax3, label="open_pos_minimum", color="black", linestyle="dotted")
        ax3.axhline(y=0.0, color='k', linestyle='-')

        # PnL
        (vol * result_mtm * 31 * 24).plot(ax=ax4, label="result_mtm")
        ax4.axhline(y=0.0, color='k', linestyle='-')

        plt.legend()
        plt.show()

    return result_mtm, result_open_position



def print_to_do(df_open_pos, contract_class: str, ts_tradeday=None):
    df_open_pos.index = pd.to_datetime(df_open_pos.index, utc=True).tz_convert(tz).floor("D")

    if ts_tradeday is None:
        ts_tradeday = pd.Timestamp(date.today(), tz=tz).floor("D")

    print("Trade date:", ts_tradeday.date())
    _df_open_pos = df_open_pos[df_open_pos.index <= ts_tradeday.floor("D")]

    currentM = _df_open_pos.iloc[-1]
    diffM = _df_open_pos.iloc[-1] - _df_open_pos.iloc[-2]
    _diffM = diffM[diffM.index > ts_tradeday].iloc[0:6]
    _currentM = currentM[_diffM.index]

    _currentM.name = "Total Position ending td"
    _diffM.name = "Traded in td"
    stack = pd.concat([_currentM, _diffM], axis=1)

    contracts = []
    for ts in stack.index:
        if contract_class == "M":
            contract_str = f"{ts.year} | M{ts.month}"
        if contract_class == "Q":
            contract_str = f"{ts.year} | Q{ts.quarter} "
        contracts.append(contract_str)

    stack.index = contracts
    return stack





if __name__ == "__main__":
    curves = {}

    df1 = load_references("severe_weather_europe")
    df2 = load_references("theguardian")
    df3 = load_references("reuters")

    df = pd.concat([df1, df2, df3])
    df = df.sort_values("timestamp", ascending=False)

    topic_eu = T01_EU_Power()
    topic_weather = T02_Weather()
    topic_gas_fuel = T03_Gas_Fuel()

    df_score0 = topic_eu.calculate_scores(df)
    df_score1 = topic_weather.calculate_scores(df)
    df_score2 = topic_gas_fuel.calculate_scores(df)
    df_scores = pd.concat([df_score1, df_score2]).sort_values("timestamp", ascending=False)


    curves_power = read_curves_from_onedrive(f"data_historical_2024+", Keys.power_germany)
    curves_power = extend_snapshot_days_to_today(curves_power)


    # TESTING --- Reduction for Monthlies
    if False:
        contract_sample = "MS"
        df_prices_power = curves_power.resample(contract_sample).mean().T
        df_contract_sentiment, map_contract_to_score = calculate_sentiment_vn(df_scores, df_prices_power, lookback_days=7)

        ts_contract = pd.Timestamp(date(2026, 10, 1), tz=tz)
        ts_start_trading = ts_contract - MonthBegin(4)
        mw_sizing = 5
        mw_maximum = 50

        mtm, open_volumefinal = run_trade_strategy(ts_contract, ts_start_trading, mw_sizing, mw_maximum, df_prices_power, df_contract_sentiment, df_scores, map_contract_to_score, force_close_delivery=False, show_plot=True)



    def run(contract_sampling, start_n_month_before_del, hours, mw_sizing, mw_maximum):
        all_mtm = []
        all_open_volume = []

        df_prices_power = curves_power.resample(contract_sampling).mean().T
        df_contract_sentiment, map_contract_to_score = calculate_sentiment_vn(df_scores, df_prices_power, lookback_days=7)

        for ts_contract in pd.date_range(pd.Timestamp(date(2026, 1, 1), tz=tz), pd.Timestamp(date(2027, 12, 1), tz=tz), freq=contract_sampling):
            ts_start_trading = ts_contract - MonthBegin(start_n_month_before_del)

            mtm, open_volume = run_trade_strategy(ts_contract, ts_start_trading, mw_sizing, mw_maximum, df_prices_power,
                                             df_contract_sentiment, df_scores, map_contract_to_score,
                                             force_close_delivery=False, show_plot=False)
            all_mtm.append(mtm * hours)
            all_open_volume.append(open_volume)

        df_all_mtm = pd.concat(all_mtm, axis=1).ffill(axis=0).fillna(0)
        df_all_open_volume = pd.concat(all_open_volume, axis=1).fillna(0)
        df_all_mtm.plot()
        total_mtm = df_all_mtm.sum(axis=1)
        total_mtm.plot(color="black", label="total_mtm")
        plt.legend()

        print("Total MtM", total_mtm.iloc[-1])
        return total_mtm, df_all_open_volume


    # All monthlies, All quarterlies



    contract_sampling = "MS"
    start_n_month_before_del = 4
    hours = 24 * 30
    mw_sizing = 5
    mw_maximum = 50
    total_mtm_months, df_all_open_volume_months = run(contract_sampling, start_n_month_before_del, hours, mw_sizing, mw_maximum)



    contract_sampling = "QS"
    start_n_month_before_del = 9
    hours = 24 * 30 * 3
    mw_sizing = 3
    mw_maximum = 25
    total_mtm_quarters, df_all_open_volume_quarters = run(contract_sampling, start_n_month_before_del, hours, mw_sizing, mw_maximum)




    total_mtm_months.plot(color="orange", label="total_mtm_months")
    total_mtm_quarters.plot(color="blue", label="total_mtm_quarters")
    (total_mtm_months + total_mtm_quarters).plot(color="black", label="total_mtm_quarters")


    df_all_open_volume_months.plot()
    df_all_open_volume_quarters.plot()
    df_all_open_volume_months.sum(axis=1).plot(color="orange", label="total_mtm_months")
    df_all_open_volume_quarters.sum(axis=1).plot(color="blue", label="total_mtm_quarters")
    (df_all_open_volume_months.sum(axis=1) + df_all_open_volume_quarters.sum(axis=1)).plot(color="black", label="total_mtm_quarters")




    today = pd.Timestamp.now(tz=tz).floor("D")
    tds = [
        today - BDay(7),
        today - BDay(6),
        today - BDay(5),
        today - BDay(4),
        today - BDay(3),
        today - BDay(2),
        today - BDay(1),
        today,
        ]
    _total_pos = []
    for td in tds:
        df_M = print_to_do(df_all_open_volume_months, "M", td)
        df_Q = print_to_do(df_all_open_volume_quarters, "Q", td)
        
        total = (pd.concat([df_M, df_Q], axis=0))["Total Position ending td"]
        _total_pos.append(total)


    df_total_pos = pd.concat(_total_pos, axis=1)
    df_total_pos = df_total_pos.ffill(axis=1)
    df_total_pos.columns = tds
    df_to_be_traded = df_total_pos.diff(axis=1)

    print(df_total_pos)


    print(df_to_be_traded)


