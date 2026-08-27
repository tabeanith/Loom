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
from loom.data.curves.get import extend_snapshot_days_to_today

from loom.spooling.analyse_scores import calculate_sentiment_v1



pio.renderers.default = "browser"
tz = "Europe/Berlin"



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


def run_trade_strategy(ts_contract, ts_start_trading, mw_sizing: int, df_prices_power, df_contract_sentiment, df_scores, map_contract_to_score, force_close_delivery=False, show_plot=False):
    n_contracts = max(1, mw_sizing)

    # ---------------------- Get prices and sentiment -----------------------------
    prices_power = df_prices_power[ts_contract]
    idx_sentiment = df_contract_sentiment[ts_contract]

    mask1 = prices_power.index.date >= ts_start_trading.date()
    mask2 = prices_power.index.date < ts_contract.date()
    mask_trading = mask1 & mask2


    # ------------------------- Trading price structure -----------------------------------
    upper = (prices_power.rolling(7).quantile(0.75))
    middle = (prices_power.rolling(7).quantile(0.5))
    lower = (prices_power.rolling(7).quantile(0.27))


    # ------------------------------------- Trading -----------------------------------
    # Normal selling and buying
    buys = (prices_power < lower).astype(int) * n_contracts
    sells = (prices_power > upper).astype(int) * n_contracts

    # TODO: Bull run on sentiment. Implement the same for bear run

    past = (prices_power > upper).astype(int).rolling(7).mean() > 0.75
    sellsingular = (prices_power < middle)
    sellX = (past & sellsingular).astype(int) * 6 * n_contracts

    buyX = (prices_power < middle).astype(int) * 3 * n_contracts

    # From buys and sells, weight them based on sentinemt:
    scaled_buy = buys * (1. - idx_sentiment/100.) + buyX * (idx_sentiment/100.)
    scaled_sell = sells * (1. - idx_sentiment/100.) + sellX * (idx_sentiment/100.)

    scaled_buy = scaled_buy[mask_trading]
    scaled_sell = scaled_sell[mask_trading]
    _traded_prices = prices_power[mask_trading]

    mtm, open_volume = calculate_mtm_from_buy_sell(scaled_buy, scaled_sell, _traded_prices)

    # TODO: Bear run on sentiment!!!



    # Check boundaries on open_volume and adjust trading:
    maximum = +15 * n_contracts
    minimum = -15 * n_contracts
    ind_sentiment = idx_sentiment / 100. * n_contracts * 15
    _minimum = ind_sentiment + minimum
    _maximum = ind_sentiment + maximum
    _minimum = _minimum.clip(upper=0)
    _maximum = _maximum.clip(lower=0)


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
        mtm2, open_volume_tbc = calculate_mtm_from_open_position(_bounded_volume, _traded_prices)
    else:
        open_volume_tbc = open_volume

    # TODO: Delivery logic
    open_volume_tbc = open_volume_tbc.reindex(index=prices_power.index)
    ts_last_trading_days = ts_contract - BDay(5)
    mask_last_trading_week = (open_volume_tbc.index >= ts_last_trading_days) & (open_volume_tbc.index < ts_contract)
    final_positions = open_volume_tbc[mask_last_trading_week]
    final_sentiment = idx_sentiment[mask_last_trading_week]

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
            open_volume_tbc.loc[mask_last_trading_week] = position_target.values
    else:
        print(f"Contract {ts_contract}: Too far away from delivery (or no sentiment avail)", final_positions.empty, final_sentiment.empty)


    # Recalculate buys and sells -- Either way the position is unchanged into delivery, or adjusted, but we have to calculate the pnl into delivery anyway
    open_volume_tbfin = open_volume_tbc.ffill().fillna(0)

    result_mtm, result_open_position = calculate_mtm_from_open_position(open_volume_tbfin, _traded_prices)
    result_mtm = mtm.ffill()

    result_mtm.name = ts_contract
    result_open_position.name = ts_contract


    if len(result_mtm) > 0:
        print(f"Contract {ts_contract} MtM:   ", result_mtm.iloc[-1])

    if show_plot:
        fig, (ax1, ax2, ax3) = plt.subplots(nrows=3, sharex=True)


        prices_power.plot(ax=ax1, label="prices", color="black")
        upper.plot(ax=ax1, label="prices0.8")
        middle.plot(ax=ax1, label="prices0.5")
        lower.plot(ax=ax1, label="prices0.2")

        scores = df_scores[map_contract_to_score[ts_contract]]
        ax2.scatter(x=scores.index, y=scores.values, label="scores", marker='o', linestyle='None')
        ax2.stem(scores.index, scores.values)

        vol = 1
        (vol*result_open_position).plot(ax=ax2, label="result_open_position", color="black")
        (vol*scaled_buy).plot(ax=ax2, label="scaled_buy", color="green")
        (vol*scaled_sell).plot(ax=ax2, label="scaled_sell", color="red")
        idx_sentiment.plot(ax=ax2, label="score_reduction", color="orange")

        (vol * result_mtm * 31 * 24).plot(ax=ax3, label="result_mtm")
        ax3.axhline(y=0.0, color='r', linestyle='-')

        plt.legend()
        plt.show()

    return result_mtm, result_open_position



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

    _currentM.name = "Total Position ending td"
    _diffM.name = "Traded in td"
    stack = pd.concat([_currentM, _diffM], axis=1)

    contracts = []
    for ts in stack.index:
        contract_str = f"{ts.year} {ts.month_name()} | M{ts.month} | Q{ts.quarter} "
        contracts.append(contract_str)

    stack.index = contracts
    print(stack)






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
    df_scores = pd.concat([df_score1, df_score2]).sort_values("timestamp", ascending=False)




    curves_power = read_curves_from_onedrive(f"data_historical_2024+", Keys.power_germany)
    curves_power = extend_snapshot_days_to_today(curves_power)


    # Reduction for Monthlies --- TESTING

    contract_sample = "MS"
    df_prices_power = curves_power.resample(contract_sample).mean().T
    df_contract_sentiment, map_contract_to_score = calculate_sentiment_v1(df_scores, df_prices_power)

    ts_contract = pd.Timestamp(date(2026, 10, 1), tz=tz)
    ts_start_trading = ts_contract - MonthBegin(4)
    mw_sizing = 5

    mtm, open_volumefinal = run_trade_strategy(ts_contract, ts_start_trading, mw_sizing, df_prices_power, df_contract_sentiment, df_scores, map_contract_to_score, force_close_delivery=False, show_plot=False)


    # All monthlies, All quarterlies

    def run(contract_sampling, start_n_month_before_del, hours, mw_sizing):
        all_mtm = []
        all_open_volume = []

        df_prices_power = curves_power.resample(contract_sampling).mean().T
        df_contract_sentiment, map_contract_to_score = calculate_sentiment_v1(df_scores, df_prices_power)

        for ts_contract in pd.date_range(pd.Timestamp(date(2026, 1, 1), tz=tz), pd.Timestamp(date(2027, 12, 1), tz=tz), freq=contract_sampling):
            ts_start_trading = ts_contract - MonthBegin(start_n_month_before_del)

            mtm, open_volume = run_trade_strategy(ts_contract, ts_start_trading, mw_sizing, df_prices_power,
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




    contract_sampling = "MS"
    start_n_month_before_del = 4
    hours = 24 * 30
    mw_sizing = 10

    total_mtm_months, df_all_open_volume_months = run(contract_sampling, start_n_month_before_del, hours, mw_sizing)




    contract_sampling = "QS"
    start_n_month_before_del = 12
    hours = 24 * 30 * 3
    mw_sizing = 3

    total_mtm_quarters, df_all_open_volume_quarters = run(contract_sampling, start_n_month_before_del, hours, mw_sizing)






    total_mtm_months.plot(color="orange", label="total_mtm_months")
    total_mtm_quarters.plot(color="blue", label="total_mtm_quarters")
    (total_mtm_months + total_mtm_quarters).plot(color="black", label="total_mtm_quarters")



    prev_td = pd.Timestamp.now(tz=tz).floor("D") - BDay(1)
    print_to_do(df_all_open_volume_months, prev_td)
    print_to_do(df_all_open_volume_quarters, prev_td)

























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








