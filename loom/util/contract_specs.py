import pandas as pd
from pandas._libs.tslibs.offsets import Hour, Week, BusinessDay, MonthBegin, QuarterBegin
from pandas.tseries.offsets import BusinessDay, YearBegin, MonthBegin, Week, Hour
from datetime import  date

from aleph.scrapes.market.keys import Keys


def get_spec_for_contracts(calibration):
    """
        Create contract table (delivery dates)
    """
    _timecurve = pd.date_range(date(2015, 1, 1), pd.Timestamp.today() + YearBegin(2), freq="h", tz="Europe/Berlin")
    timecurve = pd.Series(index=_timecurve, data=_timecurve)

    contracts = calibration[Keys.contracts]
    use_n_front_contracts = calibration[Keys.use_n_front_contracts_to_trade]
    grouped = groupby_hourly_curve_by_contracts(timecurve, calibration)

    if contracts == Keys.CONTRACT_WEEKS:
        contract_data = {
            "delivery_ts_start": grouped.first(),
            "delivery_ts_end": grouped.last() + Hour(1),
            "delivery_hours": grouped.count(),
            "delivery_year": grouped.count().index.get_level_values(0),
            "dt_last_trading_day": (grouped.first() - Week(weekday=4)).dt.tz_localize(None),
            "dt_first_trading_day": (grouped.first() - use_n_front_contracts * Week(weekday=0)).dt.tz_localize(None),
        }
        df_lookup = pd.DataFrame(contract_data)
        df_lookup["key"] = [f"{year}_KW{week:02d}" for year, week in grouped.count().index]
        return df_lookup

    if contracts == Keys.CONTRACT_MONTHS:
        contract_data = {
            "delivery_ts_start": grouped.first(),
            "delivery_ts_end": grouped.last() + Hour(1),
            "delivery_hours": grouped.count(),
            "delivery_year": grouped.count().index.get_level_values(0),
            "dt_last_trading_day": (grouped.first() + BusinessDay() - BusinessDay(2)).dt.tz_localize(None),
            "dt_first_trading_day": (grouped.first() - use_n_front_contracts * MonthBegin() + BusinessDay() - BusinessDay(2)).dt.tz_localize(None),
        }
        df_lookup = pd.DataFrame(contract_data)
        df_lookup["key"] = [f"{year}_M{month:02d}" for year, month in grouped.count().index]
        return df_lookup

    if contracts == Keys.CONTRACT_QUARTERS:
        # TODO: Check the first/last trading day
        contract_data = {
            "delivery_ts_start": grouped.first(),
            "delivery_ts_end": grouped.last() + Hour(1),
            "delivery_hours": grouped.count(),
            "delivery_year": grouped.count().index.get_level_values(0),
            "dt_last_trading_day": (grouped.first() - BusinessDay(2)).dt.tz_localize(None),
            "dt_first_trading_day": (grouped.first() - use_n_front_contracts * QuarterBegin()).dt.tz_localize(None),
        }
        df_lookup = pd.DataFrame(contract_data)
        df_lookup["key"] = [f"{year}_Q{quarter}" for year, quarter in grouped.count().index]
        return df_lookup


def groupby_hourly_curve_by_contracts(curve, calibration):
    contracts = calibration[Keys.contracts]

    if contracts == Keys.CONTRACT_WEEKS:
        iso = curve.index.isocalendar()
        grouped = curve.groupby([iso.year, iso.week])
        return grouped

    if contracts == Keys.CONTRACT_MONTHS:
        grouped = curve.groupby([curve.index.year, curve.index.month])
        return grouped

    if contracts == Keys.CONTRACT_QUARTERS:
        grouped = curve.groupby([curve.index.year, curve.index.quarter])
        return grouped


