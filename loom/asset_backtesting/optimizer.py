import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pandas.tseries.offsets import Day, MonthBegin, Week, QuarterBegin, BusinessDay
import matplotlib.ticker as ticker

from aleph.power_backtesting.asset import Battery, Battery_Colocated, Turbine, MarketSynthTurbine
from aleph.power_backtesting.data.historical import get_price_curves_and_insert_spot_results, fix_snapshot_curves
from aleph.power_backtesting.data.historical import get_schedules_and_valuation_curves_from_filer

from hedge_products import generate_day_products
from hedge_products import generate_week_products
from hedge_products import generate_month_products
from hedge_products import generate_quarter_products

import warnings
warnings.simplefilter(action='ignore', category=pd.errors.PerformanceWarning)

import seaborn as sns
sns.set_theme(style="darkgrid")

tz = "Europe/Berlin"

pd.set_option('display.max_columns', 50)
pd.set_option('display.expand_frame_repr', False)
pd.set_option('display.max_colwidth', None)
pd.set_option('display.width', 1000)


# --------- FIRST calculate asset deltas. We are not trading anything yet, only viewing optimized schedules ----------
def create_view_on_contract_prices_and_positions(data):
    asset = data["asset"]
    price_curves = data["price_curves"]
    valuation_curves = data["valuation_curves"]
    hedge_products = []

    # To optimize the generation of Dataframes:
    ts_start = price_curves.index[0]
    ts_end = price_curves.index[-1]
    #hedge_products += generate_day_products(ts_start - Day(3), ts_end + Day(7), "base")
    #hedge_products += generate_day_products(ts_start - Day(3), ts_end + Day(7), "peak")
    #hedge_products += generate_day_products(ts_start - Day(3), ts_end + Day(7), "offpeak")
    hedge_products += generate_week_products(ts_start - Day(7), ts_end + Day(35), "base")
    hedge_products += generate_week_products(ts_start - Day(7), ts_end + Day(35), "peak")
    hedge_products += generate_week_products(ts_start - Day(7), ts_end + Day(35), "offpeak")
    hedge_products += generate_month_products(ts_start - MonthBegin(1), ts_end + MonthBegin(6), "base")
    hedge_products += generate_month_products(ts_start - MonthBegin(1), ts_end + MonthBegin(6), "peak")
    hedge_products += generate_month_products(ts_start - MonthBegin(1), ts_end + MonthBegin(6), "offpeak")
    hedge_products += generate_quarter_products(ts_start - MonthBegin(1), ts_end + MonthBegin(12), "base")
    hedge_products += generate_quarter_products(ts_start - MonthBegin(1), ts_end + MonthBegin(12), "peak")
    hedge_products += generate_quarter_products(ts_start - MonthBegin(1), ts_end + MonthBegin(12), "offpeak")

    all_contracts = [hp.name for hp in hedge_products]
    all_ts = price_curves.columns

    contract_asset_valuation = pd.DataFrame(index=all_contracts, columns=all_ts, data=np.nan)
    contract_asset_delta = pd.DataFrame(index=all_contracts, columns=all_ts, data=np.nan)
    contract_prices = pd.DataFrame(index=all_contracts, columns=all_ts, data=np.nan)
    contract_hours = pd.DataFrame(index=all_contracts, columns=all_ts, data=np.nan)

    for i, hp in enumerate(hedge_products):
        hp.preload_profile_index(price_curves.index)
        profile_index = hp.preloaded_profile_index

        price = price_curves[profile_index].mean(axis=0)
        mask_small_prices = (price >= -0.1) & (price <= 0.1)
        price[mask_small_prices] = 0.1

        valuation = valuation_curves[profile_index].sum(axis=0)
        hours = valuation_curves[profile_index].count(axis=0)

        contract_prices.loc[hp.name] = price
        contract_asset_valuation.loc[hp.name] = valuation
        contract_asset_delta.loc[hp.name] = (valuation / price.abs() / hours)
        contract_hours.loc[hp.name] = hours

        # Note: Asset delta is removed before delivery (So hedging/PnL stops before delivery)
        last_trading_day = hp.start_date - BusinessDay()
        mask_stop_before_delivery = contract_asset_delta.columns.date > last_trading_day.date()
        contract_asset_delta.loc[hp.name, mask_stop_before_delivery] = np.nan

        # Note: If price close to zero, Delta hedging doesnt work! The positions get way too large
        # Cap the positions to not go overboard with hedging
        mask_small_prices = (price >= -20.) & (price <= 20.)
        contract_asset_delta.loc[hp.name, mask_small_prices] = np.nan


    # ------------------ DELTA HEDGING select tradeable contracts and try Delta Hedging -----------------------------
    contract_asset_valuation = contract_asset_valuation.ffill(axis=1)
    contract_asset_delta = contract_asset_delta.ffill(axis=1)
    contract_prices = contract_prices.ffill(axis=1)
    contract_hours = contract_hours.ffill(axis=1)

    data["contract_asset_valuation"] = contract_asset_valuation
    data["contract_asset_delta"] = contract_asset_delta
    data["contract_prices"] = contract_prices
    data["contract_hours"] = contract_hours


def calculate_hedge_volumes(data, n_front_contracts: int=3):
    # TODO: Make selection of hedge products to be configurable
    price_curves = data["price_curves"]

    contract_asset_valuation = data["contract_asset_valuation"]
    contract_asset_delta = data["contract_asset_delta"]
    contract_prices = data["contract_prices"]

    _df_open_hedge = pd.DataFrame(index=contract_prices.index, columns=contract_prices.columns, data=np.nan)
    # _df_asset_hedgestart = pd.DataFrame(index=contract_prices.index, columns=contract_prices.columns, data=np.nan)
    # _df_asset_valuation_change = pd.DataFrame(index=contract_prices.index, columns=contract_prices.columns,data=np.nan)
    data_points = []

    # ------------------ FINALLY calculate the pnl of these hedges -----------------------------
    for ts_prev, ts in zip(price_curves.columns[:-1], price_curves.columns[1:]):
        spot_date = (ts + Day(1)).date()
        ts_spot_start = pd.Timestamp(spot_date, tz=tz)
        hedge_products = []

        # ----------------------------- Contract selection -----------------------------
        # Which contracts do we even look at?

        if ts.hour > 11:
            # Next 2 days after spot day
            pass
            #hedge_products += generate_day_products(ts_spot_start + Day(1), ts_spot_start + Day(n_front_contracts + 1), "base")
            #hedge_products += generate_day_products(ts_spot_start + Day(1), ts_spot_start + Day(n_front_contracts + 1), "peak")
            #hedge_products += generate_day_products(ts_spot_start + Day(1), ts_spot_start + Day(n_front_contracts + 1), "offpeak")
        else:
            pass
            # If its early in the morning, include the spot day
            #hedge_products += generate_day_products(ts_spot_start, ts_spot_start + Day(n_front_contracts), "base")
            #hedge_products += generate_day_products(ts_spot_start, ts_spot_start + Day(n_front_contracts), "peak")
            #hedge_products += generate_day_products(ts_spot_start, ts_spot_start + Day(n_front_contracts), "offpeak")

        # TODO: Add weeklies, Add weekends
        ts_next_monday = (ts_spot_start + Week(weekday=0)).round('D')  # Monday
        ts_next_month = (ts_spot_start + MonthBegin()).round('D')  # Monday
        hedge_products += generate_week_products(ts_next_monday, ts_next_monday + Day(n_front_contracts * 7), "base")
        hedge_products += generate_week_products(ts_next_monday, ts_next_monday + Day(n_front_contracts * 7), "peak")
        hedge_products += generate_week_products(ts_next_monday, ts_next_monday + Day(n_front_contracts * 7), "offpeak")

        # ts_next_saturday = (ts_spot_start - Week(weekday=5)).round('D')  # Saturday
        # hedge_products += generate_weekend_products(ts_next_saturday, ts_next_saturday + Day(8))

        ts_last_month = ts_next_month + MonthBegin(n_front_contracts)
        ts_next_quarter = ts_last_month + QuarterBegin()
        if n_front_contracts == 1: ts_last_quarter = ts_next_quarter + Day(1)
        if n_front_contracts > 1: ts_last_quarter = ts_next_quarter + QuarterBegin(n_front_contracts - 1)
        hedge_products += generate_month_products(ts_next_month, ts_last_month, "base")
        hedge_products += generate_month_products(ts_next_month, ts_last_month, "peak")
        hedge_products += generate_month_products(ts_next_month, ts_last_month, "offpeak")
        hedge_products += generate_quarter_products(ts_next_quarter, ts_last_quarter, "base")
        hedge_products += generate_quarter_products(ts_next_quarter, ts_last_quarter, "peak")
        hedge_products += generate_quarter_products(ts_next_quarter, ts_last_quarter, "offpeak")


        for hp in hedge_products:
            # If prev hedge position is still empty, then we are starting with this new contract
            _hedgestart = _df_open_hedge.loc[hp.name, ts_prev]
            starting_with_new_contract = np.isnan(_hedgestart)

            # if starting_with_new_contract:
            #    _df_asset_hedgestart.loc[hp.name, ts_prev] = contract_asset_delta.loc[hp.name, ts_prev]

            delta_change = contract_asset_delta.loc[hp.name, ts] - contract_asset_delta.loc[hp.name, ts_prev]
            price_change = contract_prices.loc[hp.name, ts] - contract_prices.loc[hp.name, ts_prev]

            # _df_open_hedge.loc[hp.name, ts] = int(delta_change)

            _df_open_hedge.loc[hp.name, ts] = delta_change
            # _df_asset_valuation_change.loc[hp.name, ts] = contract_asset_valuation.loc[hp.name, ts] - contract_asset_valuation.loc[hp.name, ts_prev]

            data_points.append(
                pd.Series({
                    "ts": ts,
                    "hp": hp.name,
                    "delta_change": delta_change,
                    "price_change": price_change,
                })
            )
            #print(ts, hp.name, delta_change, price_change)

    df_stats = pd.concat(data_points, axis=1)

    data["to_be_hedged_volume"] = _df_open_hedge
    data["chg_stats"] = df_stats


def plot_prices(data):
    contract_prices = data["contract_prices"]
    spot_curve = data["spot_curve"]
    _spot_curve = spot_curve[spot_curve.index.year >= 2024]

    select_contracts = contract_prices.index.str.contains("Q_base_")
    contract_prices = contract_prices[select_contracts].T
    _contract_prices = contract_prices.iloc[:, 0:18]

    if False:
        f, ax = plt.subplots()
        ax.set_title(f"Spot Market")
        _spot_curve.plot(ax=ax, label="spot_curve")

    f, ax = plt.subplots()
    _contract_prices.plot(ax=ax, legend=False)
    ax.set(xlabel="trading day", ylabel="Contract Price", title="Forward Market Contracts: Quarterly Base")

    # 3. Iterate through the lines and label them
    for line, name in zip(ax.lines, _contract_prices.columns):
        # Get the last point of each line
        y_last = line.get_ydata()[-1]
        x_last = line.get_xdata()[-1]
        ax.text(x_last, y_last, f' {name}',
                 color=line.get_color(),
                 va='center',)



def plot_schedules(data):
    asset = data["asset"]
    spot_curve = data["spot_curve"]

    _spot_curve = spot_curve[spot_curve.index.year >= 2026]
    _spot_curve = _spot_curve[_spot_curve.index.month == 5]
    _schedule, _ = asset.optimize(_spot_curve.index[0], _spot_curve)

    f, ax = plt.subplots()
    _spot_curve.plot(ax=ax, label="Hourly price forward curve [EUR/MWh]", color="black")
    _schedule.plot(ax=ax, label="Optimized schedule [MW]", color="cornflowerblue")
    ax.set(title=f"{asset.name}", ylabel="", xlabel="")
    plt.legend()
    plt.show()


def check_statistics(data):
    asset = data["asset"]
    df_stats = data["chg_stats"].copy()

    df_stats.columns = df_stats.loc["ts", :].values
    df_stats = df_stats.T
    df_stats = df_stats.drop("ts", axis=1)
    df_stats["contract"] = ""
    df_stats.loc[df_stats["hp"].str.contains("D_base"), "contract"] = "D_base"
    df_stats.loc[df_stats["hp"].str.contains("W_base"), "contract"] = "W_base"
    df_stats.loc[df_stats["hp"].str.contains("M_base"), "contract"] = "M_base"
    df_stats.loc[df_stats["hp"].str.contains("Q_base"), "contract"] = "Q_base"
    df_stats.loc[df_stats["hp"].str.contains("D_peak"), "contract"] = "D_peak"
    df_stats.loc[df_stats["hp"].str.contains("W_peak"), "contract"] = "W_peak"
    df_stats.loc[df_stats["hp"].str.contains("M_peak"), "contract"] = "M_peak"
    df_stats.loc[df_stats["hp"].str.contains("Q_peak"), "contract"] = "Q_peak"
    df_stats.loc[df_stats["hp"].str.contains("D_offpeak"), "contract"] = "D_offpeak"
    df_stats.loc[df_stats["hp"].str.contains("W_offpeak"), "contract"] = "W_offpeak"
    df_stats.loc[df_stats["hp"].str.contains("M_offpeak"), "contract"] = "M_offpeak"
    df_stats.loc[df_stats["hp"].str.contains("Q_offpeak"), "contract"] = "Q_offpeak"

    n_contracts = df_stats["contract"].unique().shape[0]

    correlation = df_stats.groupby(by="contract")[['price_change','delta_change']].corr()



    f, axes = plt.subplots(nrows=3, ncols=int(n_contracts / 3.), figsize=(16, 12))
    f.suptitle(f"{asset.name} correlations: linear regression per contract family")

    df_print_data = pd.DataFrame()

    for i, contract in enumerate(df_stats["contract"].unique()):
        c = correlation.loc[(contract, "price_change")]["delta_change"]

        str_c, str_profile = contract.split("_")
        df_print_data.loc[str_c, str_profile] = c

        df_data = df_stats[df_stats["contract"] == contract]

        # Remove outlier (e.g. pfc error for 1st May)
        df_data = df_data[df_data["delta_change"] < df_data["delta_change"].quantile(0.995)]
        df_data = df_data[df_data["delta_change"] > df_data["delta_change"].quantile(0.005)]
        df_data["delta_change"] = df_data["delta_change"].astype(float)
        df_data["price_change"] = df_data["price_change"].astype(float)

        ax = axes.T.flatten()[i]
        sns.regplot(
                    x=df_data["price_change"],
                    y=df_data["delta_change"],
                    ax=ax,
                    line_kws={"color": "red"},
                    )
        ax.legend(loc="upper right", title=f"{contract} contracts", title_fontsize=12)
        ax.set(xlabel="price_change [EUR/MWh]", ylabel="delta_change [MW]")

    plt.tight_layout()
    plt.show()

    print(f"Asset: {asset.name}")
    print(f"Correlation between price_change and delta_change:")
    print(f"{df_print_data}")



# ------------------ FINALLY calculate the pnl of these hedges -----------------------------
def calculate_delta_hedging_pnl___only_base(data):
    # Harmonize index
    asset = data["asset"]
    df_open_hedge = data["to_be_hedged_volume"].copy()
    contract_hours = data["contract_hours"]
    contract_prices = data["contract_prices"]

    select_days = contract_prices.index.str.contains("D_")
    select_weeks = contract_prices.index.str.contains("W_")
    select_months = contract_prices.index.str.contains("M_")
    select_quarters = contract_prices.index.str.contains("Q_")

    select_base_contracts = contract_prices.index.str.contains("_base_")
    df_open_hedge.loc[~select_base_contracts, :] = np.nan

    # IMPORTANT: We are not calculating t
    existing_hedge = df_open_hedge.cumsum(axis=1).fillna(0)
    newly_added_hedge = df_open_hedge
    contract_prices_chng = contract_prices.diff(axis=1)

    # TODO: Spread! marker
    def _calculate_pnl(spread_multiplier=0.):
        tc_days = 1.0 * spread_multiplier
        tc_weeks = 0.5 * spread_multiplier
        tc_months = 0.25 * spread_multiplier
        tc_quarters = 0.25 * spread_multiplier

        market_friction = newly_added_hedge.abs() * contract_hours
        market_friction.loc[select_days, :] *= tc_days
        market_friction.loc[select_weeks, :] *= tc_weeks
        market_friction.loc[select_months, :] *= tc_months
        market_friction.loc[select_quarters, :] *= tc_quarters

        # pnl change of existing positions
        # IMPORTANT: Invert the PnL! We are looking at the asset position here, but at the market we would trade of course the opposit position
        pnl_change = -1 * existing_hedge.shift(axis=1) * contract_prices_chng * contract_hours - market_friction  #- (df_asset_hedgestart * contract_prices_chng * contract_hours)
        # penalty of newly opened positions (bid/ask)

        pnl_cumulated = pnl_change.cumsum(axis=1).ffill(axis=1)
        pnl_cumulated_all_contracts = pnl_cumulated.sum(axis=0)
       # pnl_cumulated_all_contracts.plot(label="PnL DeltaHedge contracts")
        #pnl_cumulated[select_days].sum(axis=0).plot(label="Days")
        return pnl_change, pnl_cumulated

    fig, axes = plt.subplots(ncols=2, sharey=True, figsize=(16, 4))
    for ax, spread_multiplier, title in zip(axes, [1., 2.], [f"{asset.name}: Transaction costs 1", f"{asset.name}: Transaction costs 2"]):
        pnl_change, pnl_cumulated = _calculate_pnl(spread_multiplier)
        data[f"pnl_cumulated___base___with_spread_multiplier{spread_multiplier}"] = pnl_cumulated

        sns.lineplot(x=pnl_cumulated.T.index, y=pnl_cumulated[select_days].sum(axis=0), ax=ax, label=f"D contracts (Transaction {1.0 * spread_multiplier} EUR/MWh)")
        sns.lineplot(x=pnl_cumulated.T.index, y=pnl_cumulated[select_weeks].sum(axis=0), ax=ax, label=f"W contracts (Transaction {0.5 * spread_multiplier} EUR/MWh)")
        sns.lineplot(x=pnl_cumulated.T.index, y=pnl_cumulated[select_months].sum(axis=0), ax=ax, label=f"M contracts (Transaction {0.25 * spread_multiplier} EUR/MWh)")
        sns.lineplot(x=pnl_cumulated.T.index, y=pnl_cumulated[select_quarters].sum(axis=0), ax=ax, label=f"Q contracts (Transaction {0.25 * spread_multiplier} EUR/MWh)")
        sns.lineplot(x=pnl_cumulated.T.index, y=pnl_cumulated.sum(axis=0), color="k", ax=ax, label="Total", alpha=1)
        ax.axhline(y=0, color='red', linestyle='--')
        ax.set(xlabel="trading day", ylabel="PnL [EUR]", title=title)
        ax.yaxis.set_major_formatter(ticker.StrMethodFormatter('{x:,.0f}'))
        ax.legend(loc='upper left')

    plt.tight_layout()
    plt.show()

    pnl_change, pnl_cumulated = _calculate_pnl(0)
    data["pnl_change"] = pnl_change
    data["pnl_cumulated"] = pnl_cumulated






# ------------------ FINALLY calculate the pnl of these hedges -----------------------------
def calculate_delta_hedging_pnl___only_profile(data, profile: str):
    # Harmonize index
    asset = data["asset"]
    df_open_hedge = data["to_be_hedged_volume"].copy()
    contract_hours = data["contract_hours"]
    contract_prices = data["contract_prices"]

    select_days = contract_prices.index.str.contains("D_")
    select_weeks = contract_prices.index.str.contains("W_")
    select_months = contract_prices.index.str.contains("M_")
    select_quarters = contract_prices.index.str.contains("Q_")

    select_profile_contracts = contract_prices.index.str.contains(profile)
    df_open_hedge.loc[~select_profile_contracts, :] = np.nan

    # IMPORTANT: We are not calculating t
    existing_hedge = df_open_hedge.cumsum(axis=1).fillna(0)
    newly_added_hedge = df_open_hedge
    contract_prices_chng = contract_prices.diff(axis=1)

    # TODO: Spread! marker
    def _calculate_pnl(spread_multiplier=0.):
        tc_days = 1.0 * spread_multiplier
        tc_weeks = 0.5 * spread_multiplier
        tc_months = 0.25 * spread_multiplier
        tc_quarters = 0.25 * spread_multiplier

        market_friction = newly_added_hedge.abs() * contract_hours
        market_friction.loc[select_days, :] *= tc_days
        market_friction.loc[select_weeks, :] *= tc_weeks
        market_friction.loc[select_months, :] *= tc_months
        market_friction.loc[select_quarters, :] *= tc_quarters

        # pnl change of existing positions
        # IMPORTANT: Invert the PnL! We are looking at the asset position here, but at the market we would trade of course the opposit position
        pnl_change = -1 * existing_hedge.shift(axis=1) * contract_prices_chng * contract_hours - market_friction  #- (df_asset_hedgestart * contract_prices_chng * contract_hours)
        # penalty of newly opened positions (bid/ask)

        pnl_cumulated = pnl_change.cumsum(axis=1).ffill(axis=1)
        pnl_cumulated_all_contracts = pnl_cumulated.sum(axis=0)
       # pnl_cumulated_all_contracts.plot(label="PnL DeltaHedge contracts")
        #pnl_cumulated[select_days].sum(axis=0).plot(label="Days")
        return pnl_change, pnl_cumulated

    fig, axes = plt.subplots(ncols=2, sharey=True, figsize=(16, 4))
    for ax, spread_multiplier, title in zip(axes, [1., 2.], [f"{asset.name}: Transaction costs 1", f"{asset.name}: Transaction costs 2"]):
        pnl_change, pnl_cumulated = _calculate_pnl(spread_multiplier)
        data[f"pnl_cumulated___base___with_spread_multiplier{spread_multiplier}"] = pnl_cumulated

        sns.lineplot(x=pnl_cumulated.T.index, y=pnl_cumulated[select_days].sum(axis=0), ax=ax, label=f"D contracts (Transaction {1.0 * spread_multiplier} EUR/MWh)")
        sns.lineplot(x=pnl_cumulated.T.index, y=pnl_cumulated[select_weeks].sum(axis=0), ax=ax, label=f"W contracts (Transaction {0.5 * spread_multiplier} EUR/MWh)")
        sns.lineplot(x=pnl_cumulated.T.index, y=pnl_cumulated[select_months].sum(axis=0), ax=ax, label=f"M contracts (Transaction {0.25 * spread_multiplier} EUR/MWh)")
        sns.lineplot(x=pnl_cumulated.T.index, y=pnl_cumulated[select_quarters].sum(axis=0), ax=ax, label=f"Q contracts (Transaction {0.25 * spread_multiplier} EUR/MWh)")
        sns.lineplot(x=pnl_cumulated.T.index, y=pnl_cumulated.sum(axis=0), color="k", ax=ax, label="Total", alpha=1)
        ax.axhline(y=0, color='red', linestyle='--')
        ax.set(xlabel="trading day", ylabel="PnL [EUR]", title=title)
        ax.yaxis.set_major_formatter(ticker.StrMethodFormatter('{x:,.0f}'))
        ax.legend(loc='upper left')

    plt.tight_layout()
    plt.show()

    pnl_change, pnl_cumulated = _calculate_pnl(0)
    data["pnl_change"] = pnl_change
    data["pnl_cumulated"] = pnl_cumulated









# ------------------ FINALLY calculate the pnl of these hedges -----------------------------
def calculate_delta_hedging_pnl___base_onpeak_split(data):
    # Harmonize index
    asset = data["asset"]
    df_open_hedge = data["to_be_hedged_volume"].copy()
    contract_hours = data["contract_hours"]
    contract_prices = data["contract_prices"]
    contract_asset_valuation = data["contract_asset_valuation"]

    select_days = contract_prices.index.str.contains("D_")
    select_weeks = contract_prices.index.str.contains("W_")
    select_months = contract_prices.index.str.contains("M_")
    select_quarters = contract_prices.index.str.contains("Q_")

    select_base_contracts = contract_prices.index.str.contains("_base_")
    select_peak_contracts = contract_prices.index.str.contains("_peak_")
    select_offpeak_contracts = contract_prices.index.str.contains("_offpeak_")

    df_open_hedge.loc[select_offpeak_contracts, :] = np.nan

    # Calculate the correct positions in Peak and in Offpeak, from Base and Peak position
    newly_added_hedge_peak = df_open_hedge.copy()
    newly_added_hedge_peak = newly_added_hedge_peak[select_peak_contracts]
    newly_added_hedge_peak.index = newly_added_hedge_peak.index.str.replace("_peak_", "_")

    df_total_valuation = contract_asset_valuation[select_base_contracts]
    df_base_hours = contract_hours[select_base_contracts]
    df_base_prices = contract_prices[select_base_contracts]
    df_total_valuation.index = df_total_valuation.index.str.replace("_base_", "_")
    df_base_hours.index = df_base_hours.index.str.replace("_base_", "_")
    df_base_prices.index = df_base_prices.index.str.replace("_base_", "_")

    df_peak_valuation = contract_asset_valuation[select_peak_contracts]
    df_peak_hours = contract_hours[select_peak_contracts]
    df_peak_prices = contract_prices[select_peak_contracts]
    df_peak_valuation.index = df_peak_valuation.index.str.replace("_peak_", "_")
    df_peak_hours.index = df_peak_hours.index.str.replace("_peak_", "_")
    df_peak_prices.index = df_peak_prices.index.str.replace("_peak_", "_")

    df_offpeak_valuation = df_total_valuation - df_peak_valuation
    df_offpeak_hours = df_base_hours - df_peak_hours
    df_offpeak_prices = (df_base_prices * df_base_hours - df_peak_prices.fillna(0.) * df_peak_hours) / df_offpeak_hours

    contract_asset_delta_offpeak = df_offpeak_valuation / df_offpeak_prices / df_offpeak_hours
    newly_added_hedge_offpeak = contract_asset_delta_offpeak.diff(axis=1)
    #Note: Make sure the Offpeak Deltas are only in the cells that also have the Peak Deltas. Otherwise the hedge positions start way too early
    newly_added_hedge_offpeak[newly_added_hedge_peak.isna()] = np.nan


    newly_added_hedge_base = newly_added_hedge_offpeak
    newly_added_hedge_onpeak = newly_added_hedge_peak - newly_added_hedge_base


    # Hedging Base & OnPeak
    df_open_hedge.loc[select_base_contracts] = newly_added_hedge_base.values
    df_open_hedge.loc[select_peak_contracts] = newly_added_hedge_onpeak.values

    if False:
        index = df_open_hedge.T.index
        mask = (index >= pd.Timestamp("2026-01-24 16:00:00+01:00")) & (index <= pd.Timestamp("2026-07-28 16:00:00+02:00"))
        ct = 'D_peak_2024_05_09'
        ct  = 'M_peak_2026_04'
        data["to_be_hedged_volume"].T[ct][mask].plot()
        df_open_hedge.T[ct][mask].plot()
        existing_hedge.T[ct][mask].plot()
        existing_hedge.T['M_base_2026_04'][mask].plot()
        prices_base_minus_peak.T['M_2026_04'][mask].plot(label ="prices_base_minus_peak")
        contract_prices.T['M_2026_04'][mask].plot(label ="prices_base_minus_peak")
        contract_prices.T['M_peak_2026_04'][mask].plot(label ="contract_prices")


        (1/8000*(pnl_cumulated.T[ct] + pnl_cumulated.T['M_base_2026_04'])).plot()
        (1/8000*(pnl_cumulated.T[ct])).plot()
        plt.legend()


        contract_hours.T[ct][mask]
        market_friction[select_days].T
        contract_asset_delta = data["contract_asset_delta"]
        contract_asset_valuation = data["contract_asset_valuation"]


        contract_prices.loc['M_peak_2024_11', pd.Timestamp("2024-07-24 16:00:00+01:00", tz=tz)]
        contract_prices[pd.Timestamp("2024-07-31 16:00:00+02:00")]

        price_curves[pd.Timestamp("2024-07-30 16:00:00+02:00")].plot()
        price_curves[pd.Timestamp("2024-07-31 16:00:00+02:00")].plot()

        t = market_friction[select_months]

        pnl_change.T[mask][ct2]
        contract_prices.T[mask][ct2]
        pnl_cumulated.T[mask][ct2]
        df_open_hedge.T[mask][ct2]
        contract_asset_valuation.T[mask][ct2]
        contract_asset_valuation.T[mask]['M_base_2024_11']

        check = pnl_cumulated[select_months].T[mask]   #.sum(axis=1)    #.dropna(axis=0, how='all')
        check.loc[:, ~check.isna().all(axis=0)]


        newly_added_hedge_base[newly_added_hedge_base.index.str.contains("M_")].T[mask]


        ct2 = 'M_base_2024_05'
        pnl_cumulated.T[ct2].plot()
        ct2 = 'M_peak_2024_05'
        pnl_cumulated.T[ct2].plot()

        ct3 = 'Q_base_2024_4'
        contract_hours.T[ct3].plot()
        ct4 = 'Q_peak_2024_4'
        contract_hours.T[ct4].plot()


        newly_added_hedge_peak.T[ct2][mask].dropna()
        newly_added_hedge_onpeak.T[ct2][mask].dropna()
        newly_added_hedge_base.T[ct2][mask].dropna()
        newly_added_hedge_onpeak.T[ct2][mask].dropna()
        newly_added_hedge_offpeak.T[ct2][mask].dropna()



    # TODO: three things happen in this method:
    # 1. Calculating the Base & OnPeak volumes from Naive Delta Hedge
    # 2. Then apply some extra logic and filtering

    # 3. Then calculate the PnL from that hedging logic
    # 4. And then, plot the results

    # 3. ------------------------------------------------------------------  Then apply some extra logic and filtering
    adjusted_hedge_base = newly_added_hedge_base.copy()
    adjusted_hedge_onpeak = newly_added_hedge_onpeak.copy()

    prices_base_minus_peak = df_base_prices - df_peak_prices
    prices_base_minus_peak_changes = prices_base_minus_peak.diff(axis=1).fillna(0)
    prices_base_minus_peak_rollmean = prices_base_minus_peak.rolling(10, axis=1).mean()

    price_treshold = 1.0
    price_treshold = 1.0


    if True:
        adjusted_hedge_base[:] = 0
        adjusted_hedge_onpeak[:] = 0

        for ctc in prices_base_minus_peak.index:
            _price_change_cumulative = 0
            _hedge_base_cumulative = 0
            _hedge_onpeak_cumulative = 0

            for ts in prices_base_minus_peak.columns:

                if prices_base_minus_peak.loc[ctc, ts] > prices_base_minus_peak_rollmean.loc[ctc, ts]:
                    continue

                # Base/Peak spread needs to have made a big move to above the threshold
                _price_change_cumulative += prices_base_minus_peak_changes.loc[ctc, ts]
                _hedge_base_cumulative += newly_added_hedge_base.loc[ctc, ts]
                _hedge_onpeak_cumulative += newly_added_hedge_onpeak.loc[ctc, ts]
                filter_hedge_ok = True

                adjusted_hedge_base.loc[ctc, ts] = 0
                adjusted_hedge_onpeak.loc[ctc, ts] = 0

                if np.abs(_price_change_cumulative) >= price_treshold:

                    # In summer: If Base/Peak spread moves up, do NOT sell
                    if (ts.month >= 3) and (ts.month <= 8):
                        if _price_change_cumulative > 0:
                            filter_hedge_ok = False

                    # In summer: If Base/Peak spread moves up, do NOT sell
                    if (ts.month < 3) or (ts.month > 8):
                        pass
                        if _price_change_cumulative > 0:
                            filter_hedge_ok = False

                    if filter_hedge_ok:
                        adjusted_hedge_base.loc[ctc, ts] = _hedge_base_cumulative
                        adjusted_hedge_onpeak.loc[ctc, ts] = _hedge_onpeak_cumulative

                    _price_change_cumulative = 0.
                    _hedge_base_cumulative = 0.
                    _hedge_onpeak_cumulative = 0.




    # Hedging Base & OnPeak
    df_open_hedge.loc[select_base_contracts] = adjusted_hedge_base.values
    df_open_hedge.loc[select_peak_contracts] = adjusted_hedge_onpeak.values



    # IMPORTANT: df_open_hedge still shows the asset Delta change. For the PnL, we trade the opposite in the market
    existing_hedge = -1 * df_open_hedge.fillna(0).cumsum(axis=1)
    # Falls nicht delivery:
    mask_delivery = data["to_be_hedged_volume"].isna()
    if False:
        existing_hedge[mask_delivery] = 0
    # Falls mit delivery
    else:
        existing_hedge[mask_delivery] = np.nan
        existing_hedge = existing_hedge.ffill(axis=1).bfill(axis=1)

    #existing_hedge = -1 * df_open_hedge.fillna(0).cumsum(axis=1)  # Take into delivery
    newly_added_hedge = -1 * df_open_hedge.fillna(0)
    contract_prices_chng = contract_prices.diff(axis=1)

    contract_hours_constant_delivery = contract_hours.copy()
    for ctc in contract_hours_constant_delivery.index:
        contract_hours_constant_delivery.loc[ctc, :] = contract_hours_constant_delivery.loc[ctc, :].max()

    # TODO: Spread! marker
    def _calculate_pnl(spread_multiplier=0.):
        tc_days = 1.0 * spread_multiplier
        tc_weeks = 0.5 * spread_multiplier
        tc_months = 0.25 * spread_multiplier
        tc_quarters = 0.25 * spread_multiplier

        market_friction = newly_added_hedge.abs() * contract_hours_constant_delivery
        market_friction.loc[select_days, :] *= tc_days
        market_friction.loc[select_weeks, :] *= tc_weeks
        market_friction.loc[select_months, :] *= tc_months
        market_friction.loc[select_quarters, :] *= tc_quarters

        # pnl change of existing positions
        pnl_change = existing_hedge.shift(axis=1) * contract_prices_chng * contract_hours_constant_delivery - market_friction  #- (df_asset_hedgestart * contract_prices_chng * contract_hours)
        # penalty of newly opened positions (bid/ask)

        pnl_cumulated = pnl_change.cumsum(axis=1).ffill(axis=1)
        pnl_cumulated_all_contracts = pnl_cumulated.sum(axis=0)
       # pnl_cumulated_all_contracts.plot(label="PnL DeltaHedge contracts")
        #pnl_cumulated[select_days].sum(axis=0).plot(label="Days")
        return pnl_change, pnl_cumulated

    # Just for plotting! contract_hours is decreasing into delivery
    existing_hedge_mwh = existing_hedge * contract_hours

    fig, axes = plt.subplots(nrows=2, ncols=2, figsize=(16, 4), sharex='col', sharey='row')
    for i, (spread_multiplier, title) in enumerate(zip([1., 2.], [f"{asset.name}: Transaction costs 1", f"{asset.name}: Transaction costs 2"])):
        pnl_change, pnl_cumulated = _calculate_pnl(spread_multiplier)
        ax = axes[0][i]
        axpos = axes[1][i]

        data[f"pnl_cumulated___base_onpeak_split___with_spread_multiplier{spread_multiplier}"] = pnl_cumulated

        sns.lineplot(x=pnl_cumulated.T.index, y=pnl_cumulated[select_days].sum(axis=0), ax=ax, label=f"D contracts (Transaction {1.0 * spread_multiplier} EUR/MWh)")
        sns.lineplot(x=pnl_cumulated.T.index, y=pnl_cumulated[select_weeks].sum(axis=0), ax=ax, label=f"W contracts (Transaction {0.5 * spread_multiplier} EUR/MWh)")
        sns.lineplot(x=pnl_cumulated.T.index, y=pnl_cumulated[select_months].sum(axis=0), ax=ax, label=f"M contracts (Transaction {0.25 * spread_multiplier} EUR/MWh)")
        sns.lineplot(x=pnl_cumulated.T.index, y=pnl_cumulated[select_quarters].sum(axis=0), ax=ax, label=f"Q contracts (Transaction {0.25 * spread_multiplier} EUR/MWh)")
        sns.lineplot(x=pnl_cumulated.T.index, y=pnl_cumulated.sum(axis=0), color="k", ax=ax, label="Total", alpha=1)

        sns.lineplot(x=existing_hedge_mwh.T.index, y=existing_hedge_mwh[select_quarters & select_base_contracts].sum(axis=0), ax=axpos, label=f"Q Base MWh")
        sns.lineplot(x=existing_hedge_mwh.T.index, y=existing_hedge_mwh[select_quarters & select_peak_contracts].sum(axis=0), ax=axpos, label=f"Q Peak MWh")
        sns.lineplot(x=existing_hedge_mwh.T.index, y=existing_hedge_mwh[select_months & select_base_contracts].sum(axis=0), ax=axpos, label=f"M Base MWh")
        sns.lineplot(x=existing_hedge_mwh.T.index, y=existing_hedge_mwh[select_months & select_peak_contracts].sum(axis=0), ax=axpos, label=f"M Peak MWh")
        sns.lineplot(x=existing_hedge_mwh.T.index, y=existing_hedge_mwh[select_weeks & select_base_contracts].sum(axis=0), ax=axpos, label=f"W Base MWh")
        sns.lineplot(x=existing_hedge_mwh.T.index, y=existing_hedge_mwh[select_weeks & select_peak_contracts].sum(axis=0), ax=axpos, label=f"W Peak MWh")

        ax.axhline(y=0, color='red', linestyle='--')
        ax.set(xlabel="trading day", ylabel="PnL [EUR]", title=title)
        axpos.set(xlabel="trading day", ylabel="Open position of this hedge in the market", title=title)
        ax.yaxis.set_major_formatter(ticker.StrMethodFormatter('{x:,.0f}'))
        ax.legend(loc='upper left')

    plt.tight_layout()
    plt.show()

    pnl_change, pnl_cumulated = _calculate_pnl(0)
    data["pnl_change"] = pnl_change
    data["pnl_cumulated"] = pnl_cumulated



def calculate_intrinsic_and_evaluate(multiple_data):
    # Compare initial valuation vs realized:

    df_print_results = pd.DataFrame()

    for data in multiple_data:
        asset = data["asset"]
        spot_curve = data["spot_curve"]
        price_curves = data["price_curves"]
        pnl_cumulated = data["pnl_cumulated"]
        schedule_curves = data["schedule_curves"]

        _spot_curve = spot_curve.dropna()
        opt_schedule_perfect_hindsight, opt_storage = asset.optimize(_spot_curve.index[0], _spot_curve)
        valuation_perfect_hindsight = asset.valuate(_spot_curve, opt_schedule_perfect_hindsight)

        # Stuckelung right before spot delivery
        _schedule_curves = schedule_curves.ffill(axis=1)
        intersect = _spot_curve.index.intersection(_schedule_curves.index)

        last_schedule_before_dayahead = _schedule_curves.iloc[:, -1]
        valuation_estimated = asset.valuate(_spot_curve.reindex(intersect), last_schedule_before_dayahead.reindex(intersect))
        valuation_estimated = valuation_estimated.fillna(0.)

        #_valuation_perfect_hindsight = valuation_perfect_hindsight.reindex(intersect)
        #_valuation_estimated = valuation_estimated.reindex(intersect)
        #_valuation_perfect_hindsight.cumsum().plot(label="Perfect Hindsight")
        #_valuation_estimated.cumsum().plot(label="Estimated")

        val1 = valuation_perfect_hindsight.reindex(intersect).sum()
        val2 = valuation_estimated.reindex(intersect).sum()

        val4 = data[f"pnl_cumulated___base___with_spread_multiplier1.0"].sum(axis=0).iloc[-1]
        val5 = data[f"pnl_cumulated___base___with_spread_multiplier2.0"].sum(axis=0).iloc[-1]

        val7 = data[f"pnl_cumulated___base_onpeak_split___with_spread_multiplier1.0"].sum(axis=0).iloc[-1]
        val8 = data[f"pnl_cumulated___base_onpeak_split___with_spread_multiplier2.0"].sum(axis=0).iloc[-1]

        __spot_curve = _spot_curve.reindex(intersect)
        __last_schedule_before_dayahead = last_schedule_before_dayahead.reindex(intersect)

        asset_name = f"{asset.name}"

        df_print_results.loc["REALIZED INTRINSIC VALUE ------------------------------------------------", asset_name] = ""
        df_print_results.loc["Spot delivery days", asset_name] = round(intersect.shape[0] / 24)
        df_print_results.loc["Intr with perfect hindsight knowledge of DayAhead results", asset_name] = f"{val1:,.0f} EUR"
        df_print_results.loc["Intr of last optimization before DayAhead", asset_name] = f"{val2:,.0f} EUR"
        df_print_results.loc["Capture of perfect hindsight Intr", asset_name] = f"{val2 / val1 * 100:.2f} %"
        df_print_results.loc["REALIZED EXTRINSIC VALUE ------------------------------------------------", asset_name] = ""
        df_print_results.loc["Forward Trading days", asset_name] = pnl_cumulated.shape[1]
        df_print_results.loc["a: Extr with trading Base positions, Low transaction costs", asset_name] = f"{val4:,.0f} EUR"
        df_print_results.loc["a: Extr with higher transaction costs", asset_name] = f"{val5:,.0f} EUR"
        df_print_results.loc["a: Extr / Intr", asset_name] = f"{val5 / val2 * 100:.2f} % to {val4 / val2 * 100:.2f} %"
        df_print_results.loc["b: Extr with trading Peak & Offpeak positions, Low transaction costs", asset_name] = f"{val7:,.0f} EUR"
        df_print_results.loc["b: Extr with higher transaction costs", asset_name] = f"{val8:,.0f} EUR"
        df_print_results.loc["b: Extr / Intr", asset_name] = f"{val8 / val2 * 100:.2f} % to {val7 / val2 * 100:.2f} %"
        df_print_results.loc["REALIZED CAPTURE RATES --------------------------------------------------", asset_name] = ""

        for year in [2024, 2025, 2026]:
            mask_year = __spot_curve.index.year == year
            positive_schedule = __spot_curve[mask_year][last_schedule_before_dayahead.fillna(0) > 0]
            negative_schedule = __spot_curve[mask_year][last_schedule_before_dayahead.fillna(0) < 0]

            ratio_positive_schedule = positive_schedule.mean() / __spot_curve[mask_year].mean()
            ratio_negative_schedule = negative_schedule.mean() / __spot_curve[mask_year].mean()

            df_print_results.loc[f"{year} Avg production price / Calendar Spot", asset_name] = f"{ratio_positive_schedule:,.3f}"
            df_print_results.loc[f"{year} Avg charging   price / Calendar Spot", asset_name] = f"{ratio_negative_schedule:,.3f}"

    print(df_print_results)



def run_optimizer(data, store_results_to_filer=False):
    price_curves = data["price_curves"]
    asset = data["asset"]

    schedule_curves = {}
    storage_curves = {}
    valuation_curves = {}

    prev_ts_start_optimization = None

    for ts_prev, ts in zip(price_curves.columns[:-1], price_curves.columns[1:]):
        spot_date = (ts + Day(1)).floor("D")

        # Only optimize tomorrow if Spot not yet delivered
        if ts.hour <= 11:
            ts_start_optimization = spot_date  # Start tomorrow
        else:
            ts_start_optimization = spot_date + Day(1)  # Start day after tomorrow

        # If the start time of optimization changed, we have to update the start value of the optimizer
        if (prev_ts_start_optimization is not None) and (ts_start_optimization != prev_ts_start_optimization):
            last_known_schedule = schedule_curves[ts_prev]
            # Lookup the previous known optimized storage result
            mask = last_known_schedule.index >= ts_start_optimization
            start_value_mwh = last_known_schedule[mask].iloc[0]
            asset.set_start_value_mwh(start_value_mwh)
            print(ts, "start_value_mwh", start_value_mwh)

        # ----------------------------- Run the optimizer -----------------------------
        print(f"Optimize ts {ts}, starting optimization at {ts_start_optimization}")
        prices = price_curves[ts].dropna()
        #

        #prices = prices[prices.index <= ts_start_optimization + MonthBegin(5)]  # For performance curtail data
        opt_schedule, opt_storage, valuation = asset.optimize(ts_start_optimization, prices)

        schedule_curves[ts] = opt_schedule
        storage_curves[ts] = opt_storage
        valuation_curves[ts] = valuation

        print(f"opt_schedule first row:", opt_schedule.index[0])
        print(f"valuation first value at:", valuation.dropna().index[0])

        prev_ts_start_optimization = ts_start_optimization


    schedule_curves = pd.DataFrame(schedule_curves)
    storage_curves = pd.DataFrame(storage_curves)
    valuation_curves = pd.DataFrame(valuation_curves)

    # Harmonize index
    schedule_curves = schedule_curves.reindex(price_curves.index).reindex(columns=price_curves.columns)
    storage_curves = storage_curves.reindex(price_curves.index).reindex(columns=price_curves.columns)
    valuation_curves = valuation_curves.reindex(price_curves.index).reindex(columns=price_curves.columns)

    data["schedule_curves"] = schedule_curves
    data["storage_curves"] = storage_curves
    data["valuation_curves"] = valuation_curves

    # Store results just in case
    if store_results_to_filer:
        schedule_curves.to_csv(f"schedule_optimzied_{asset.name}.csv.gz", compression="gzip")
        valuation_curves.to_csv(f"valuation_{asset.name}.csv.gz", compression="gzip")



# 1. Data and Parameters


# 1. Data and Parameters


# 1. Data and Parameters


if __name__ == "__main__":

    asset_turbine = Turbine(
            max_produce_mw=64,
            strike=75.,
        )

    asset_battery = Battery(
            max_produce_mw=64,
            max_storage_mwh=255,
            efficiency=0.85,
        )

    asset_battery_colocated = Battery_Colocated(
            max_produce_mw=64,
            max_storage_mwh=255,
            efficiency=0.85,
        )

    # ---------------------- Get historical prices -----------------------------
    spot_curve, _price_curves = get_price_curves_and_insert_spot_results("data/power_germany_snapshot_2024+.csv.gz")
    #spot_curve, _price_curves = get_price_curves_and_insert_spot_results("data/power_germany.csv.gz")
    _price_curves = fix_snapshot_curves(_price_curves)
    _price_curves = _price_curves.loc[:, _price_curves.columns.year >= 2020]




    price_curves = _price_curves#.copy()
    #price_curves = price_curves.loc[:, (price_curves.columns.dayofweek == 4)]  # Tuesday




    data_asset_battery = {}
    data_asset_turbine = {}
    data_asset_battery_colocated = {}
    data = data_asset_battery

    data_asset_battery["asset"] = asset_battery
    data_asset_battery["spot_curve"] = spot_curve
    data_asset_battery["price_curves"] = price_curves

    data_asset_turbine["asset"] = asset_turbine
    data_asset_turbine["spot_curve"] = spot_curve
    data_asset_turbine["price_curves"] = price_curves

    data_asset_battery_colocated["asset"] = asset_battery_colocated
    data_asset_battery_colocated["spot_curve"] = spot_curve
    data_asset_battery_colocated["price_curves"] = price_curves

    # ---------------------- Run optimizer -----------------------------
    if False: run_optimizer(data_asset_battery_colocated, True)
    if False: run_optimizer(data_asset_battery, True)
    if False: run_optimizer(data_asset_turbine, True)

    get_schedules_and_valuation_curves_from_filer(data_asset_turbine)
    get_schedules_and_valuation_curves_from_filer(data_asset_battery)
    #get_schedules_and_valuation_curves_from_filer(data_asset_battery_colocated)


    # ----------------- Create contract prices --------------------------
    create_view_on_contract_prices_and_positions(data_asset_battery)
    create_view_on_contract_prices_and_positions(data_asset_turbine)
    #create_view_on_contract_prices_and_positions(data_asset_battery_colocated)

    #plot_schedules(data_asset_battery)
    #plot_schedules(data_asset_battery_colocated)

    # ----------------- Calculate Hedge Volumes --------------------------
    #calculate_hedge_volumes(data_asset_battery_colocated)
    calculate_hedge_volumes(data_asset_battery)
    calculate_hedge_volumes(data_asset_turbine)

    # ----------------- Calculate PnL --------------------------
    calculate_delta_hedging_pnl___only_base(data_asset_turbine)
    calculate_delta_hedging_pnl___only_base(data_asset_battery)
    #calculate_delta_hedging_pnl___only_base(data_asset_battery_colocated)

    calculate_delta_hedging_pnl___base_onpeak_split(data_asset_turbine)
    calculate_delta_hedging_pnl___base_onpeak_split(data_asset_battery)
    #calculate_delta_hedging_pnl___base_onpeak_split(data_asset_battery_colocated)



    # GOOD
    calculate_hedge_volumes(data_asset_turbine, n_front_contracts=3)
    data_asset_turbine["to_be_hedged_volume"] = data_asset_turbine["to_be_hedged_volume"] * 1

    calculate_delta_hedging_pnl___only_profile(data_asset_turbine, "base")



    # MAYBE
    calculate_hedge_volumes(data_asset_battery, n_front_contracts=1)
    data_asset_battery["to_be_hedged_volume"] = data_asset_battery["to_be_hedged_volume"] * 10

    calculate_delta_hedging_pnl___base_onpeak_split(data_asset_battery)
    calculate_delta_hedging_pnl___only_profile(data_asset_battery, "base")
    calculate_delta_hedging_pnl___only_profile(data_asset_battery, "peak")
    calculate_delta_hedging_pnl___only_profile(data_asset_battery, "offpeak")



    # Stats: Check average trade size
    contracts = data_asset_battery["to_be_hedged_volume"]
    select_days = contracts.index.str.contains("D_")
    select_weeks = contracts.index.str.contains("W_")
    select_weekends = contracts.index.str.contains("WEnd_")
    select_months = contracts.index.str.contains("M_")
    select_quarters_base = contracts.index.str.contains("Q_base")
    select_quarters_peak = contracts.index.str.contains("Q_peak")

    print("Average Quarterly Base trade in MW:", contracts[select_quarters_base].abs().mean().mean())
    print("Average Quarterly Peak trade in MW:", contracts[select_quarters_peak].abs().mean().mean())



    # ----------------- Evaluate realization --------------------------
    calculate_intrinsic_and_evaluate([data_asset_turbine, data_asset_battery, data_asset_battery_colocated])


    check_statistics(data_asset_turbine)
    check_statistics(data_asset_battery)
    check_statistics(data_asset_battery_colocated)

    contract_prices = data_asset_battery["contract_prices"]
    select_days = contract_prices.index.str.contains("D_")
    select_weeks = contract_prices.index.str.contains("W_")
    select_weekends = contract_prices.index.str.contains("WEnd_")
    select_months = contract_prices.index.str.contains("M_")
    select_quarters = contract_prices.index.str.contains("Q_")




    # TODO: Calculate some variation, like...
    # 1, 2, 3 top contracts
    # close every second day, every third, every Monday
    # Algo trading:
    # Monitor liquidity pockets, and if deemed suitable, run the optimization (dirty model)
    # If no liquidity found, carry positions over to the day...
    # Not that against this Delta Hedge there is still the asset PnL! So total PnL (Asset + Delta Hedge) will cover each other to a degree
    # A dirty model is enough, optimizing curve until end of 2026 i can do in 5ms



    # For debugging individual data points
    if False:
        data = data_asset_battery
        data.keys()


        ct = "D_base_2026_05_01"
        ct = "Q_base_2024_3"

        df_open_hedge = data["to_be_hedged_volume"]
        pnl_change = data["pnl_change"]
        pnl_cumulated = data["pnl_cumulated"]
        contract_prices = data["contract_prices"]
        contract_asset_valuation = data["contract_asset_valuation"]
        schedule_curves = data["schedule_curves"]
        existing_hedge = df_open_hedge.cumsum(axis=1).fillna(0).shift(axis=1)


        index = df_open_hedge.T.index
        mask = (index >= pd.Timestamp("2024-04-05 16:00:00+01:00")) & (index <= pd.Timestamp("2024-05-05 16:00:00+02:00"))

        print("Show individual PnLs")
        results = pnl_cumulated[select_days].T[mask]
        results = results.loc[:, ~results.isna().all(axis=0)]
        print(results)
        pnl_cumulated.T[ct][mask].dropna()

        print("df_open_hedge: This is the latest volume to be hedged in the market")
        df_open_hedge.T[ct][mask]

        print("existing_hedge: This is the sum of market hedges (already including the latest volume). This data stops before delivery!")
        existing_hedge.T[ct][mask]

        print("pnl_cumulated: This is the pnl of all market hedges. This data stops before delivery!")
        pnl_change.T[ct][mask]

        print("pnl_cumulated: This is the pnl of all market hedges. This data stops before delivery!")
        newly_added_hedge.T[ct][mask]

        print("contract_prices: Current contract market price")
        contract_prices.T[ct][mask]

        print("contract_asset_valuation: Current asset valuation")
        contract_asset_valuation.T[ct][mask]

        print("contract_asset_delta: Current asset Delta position")
        contract_asset_delta.T[ct][mask]

        schedule_curves[pd.Timestamp("2024-12-11 16:00:00+01:00")].plot()


        #2026-03-26 09:00:00+01:00
        price_curves[pd.Timestamp("2024-12-11 16:00:00+01:00")].plot()
        price_curves[pd.Timestamp("2026-03-31 16:00:00+02:00")].plot()
        price_curves[pd.Timestamp("2026-04-01 16:00:00+02:00")].plot()
        price_curves[pd.Timestamp("2026-04-02 16:00:00+02:00")].plot()



