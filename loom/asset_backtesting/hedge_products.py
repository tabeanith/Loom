from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List

import numpy as np
import pandas as pd

from pandas.tseries.offsets import Hour, Day, Week, MonthBegin, QuarterBegin, YearBegin, Week


@dataclass()
class HedgeProduct:
    name: str
    start_date: datetime
    end_date: datetime
    profile: str = "base"
    preloaded_profile_index: np.ndarray = None

    def aggregate(self, data_series: pd.DataFrame):
        """
        Take dataSeries and sum up some segment depending on given hedgeProduct
        """
        return self.view(data_series).sum(axis=0, min_count=1)

    def average(self, data_series: pd.DataFrame):
        """
        Take dataSeries and average some segment depending on given hedgeProduct
        """
        return self.view(data_series).mean(axis=0)

    def view(self, data_series: pd.DataFrame) -> pd.DataFrame:
        """
        Take dataSeries and sum up some segment depending on given hedgeProduct
        """
        index_filtered = self.get_index(data_series.index)
        return data_series[index_filtered]

    def get_hours(self, index: pd.DatetimeIndex):
        index_filtered = self.get_index(index)
        return np.sum(index_filtered)

    def get_index(self, index: pd.DatetimeIndex):
        # To optimize runtime, this filter can be preloaded
        if self.preloaded_profile_index is None:
            _profile_filter = _select_profile.get(self.profile)
            mask1 = _profile_filter(index)
            mask2 = (index >= self.start_date) & (index < self.end_date)
            return mask1 & mask2
        else:
            return self.preloaded_profile_index

    def preload_profile_index(self, index: pd.DatetimeIndex):
        _profile_filter = _select_profile.get(self.profile)
        mask1 = _profile_filter(index)
        mask2 = (index >= self.start_date) & (index < self.end_date)
        self.preloaded_profile_index = mask1 & mask2


def create_base_filter(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    return index.year > 0


def create_peak_filter(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    return (index.hour >= 8) & (index.hour < 20) & (index.dayofweek < 5)


def create_weekday_filter(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    return index.dayofweek < 5


def create_weekend_filter(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    return index.dayofweek > 4


def create_offpeak_filter(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    return ~create_peak_filter(index)


def create_offpeak_1_filter(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    return (index.hour >= 0) & (index.hour < 8)


def create_offpeak_2_filter(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    return index.hour >= 20


def create_mon_sun_00_06_filter(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    return (index.hour < 6)


def create_mon_fri_06_22_filter(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    return (index.dayofweek < 5) & (index.hour >= 6) & (index.hour < 22)


def create_mon_fri_16_20_filter(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    return (index.dayofweek < 5) & (index.hour >= 16) & (index.hour < 20)


def create_mon_fri_20_24_filter(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    return (index.dayofweek < 5) & (index.hour >= 20)


def create_mon_fri_16_20_filter(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    return (index.dayofweek < 5) & (index.hour >= 16) & (index.hour < 20)


def create_mon_fri_16_20_filter(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    return (index.dayofweek < 5) & (index.hour >= 16) & (index.hour < 20)


def create_mon_fri_06_10_filter(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    return (index.dayofweek < 5) & (index.hour >= 6) & (index.hour < 10)


def create_mon_fri_18_22_filter(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    return (index.dayofweek < 5) & (index.hour >= 18) & (index.hour < 22)


def create_mon_sun_08_20_filter(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    return (index.hour >= 8) & (index.hour < 20)


_select_profile = {
    "base": create_base_filter,
    "peak": create_peak_filter,
    "offpeak": create_offpeak_filter,
    "weekday": create_weekday_filter,
    "weekend": create_weekend_filter,
    "offpeak_1": create_offpeak_1_filter,
    "offpeak_2": create_offpeak_2_filter,
    "mon_sun_00_06": create_mon_sun_00_06_filter,
    "mon_fri_06_22": create_mon_fri_06_22_filter,
    "mon_fri_16_20": create_mon_fri_16_20_filter,
    "mon_fri_20_24": create_mon_fri_20_24_filter,
    "mon_fri_06_10": create_mon_fri_06_10_filter,
    "mon_fri_18_22": create_mon_fri_18_22_filter,
    "mon_sun_08_20": create_mon_sun_08_20_filter,
}


def select_profile(idx: pd.DatetimeIndex, profile: str):
    if isinstance(idx, pd.DataFrame):
        idx = idx.index
    if isinstance(idx, pd.Series):
        idx = idx.index

    filter = _select_profile.get(profile, None)

    if filter:
        return filter(idx)

    raise Exception(f"profile {profile} is unknown")


def calculate_products(series, hedge_products, method="aggregate") -> pd.DataFrame:
    profiles = {}

    for key, filter_index in _select_profile.items():
        profiles[key] = series[filter_index(series.index)]

    _profiles = pd.DataFrame(profiles)
    if method == "aggregate":
        _products = {hp.name: hp.aggregate(_profiles) for hp in hedge_products}
    elif method == "average":
        _products = {hp.name: hp.average(_profiles) for hp in hedge_products}
    else:
        raise NotImplemented

    df = pd.DataFrame(index=pd.Index(_products.keys(), name="product"),
                      data=_products.values(),
                      columns=_profiles.columns)
    return df


def calculate_products_2(series, hedge_products, method="aggregate") -> pd.DataFrame:
    profiles = {
        "base": series,
        "peak": series[create_peak_filter(series.index)],
        "offpeak": series[create_offpeak_filter(series.index)],
        "offpeak I": series[create_offpeak_1_filter(series.index)],
        #"peak everyday": series[create_peak_everyday_filter(series.index)],
        "offpeak II": series[create_offpeak_2_filter(series.index)],
        "weekday base": series[create_weekday_filter(series.index)],
        "weekday offpeak": series[create_weekday_filter(series.index) & create_offpeak_filter(series.index)],
    }
    _profiles = pd.DataFrame(profiles)
    if method == "aggregate":
        _products = {hp.name: hp.aggregate(_profiles) for hp in hedge_products}
    elif method == "average":
        _products = {hp.name: hp.average(_profiles) for hp in hedge_products}
    else:
        raise NotImplemented
    df = pd.DataFrame(index=pd.Index(_products.keys(), name="product"),
                      data=_products.values(),
                      columns=_profiles.columns)
    return df


def generate_weeks(dt: pd.Timestamp) -> List[HedgeProduct]:
    """
    :return: List of default HedgeProduct objects

    NOTE: Needs to be in the correct timezone!
    """
    hedge_products = []
    dt = dt.round('D')
    days_start_ts = (dt + Week(weekday=0) - Week(weekday=0)).round('D')  # Monday
    days_end_ts = (days_start_ts + Week(20)).round('D')  # Monday
    weeks_end_ts = (days_start_ts + Week(20)).round('D')

    # Generate smaller products covering current and FrontMonth (Required for Risk reporting the asset PnL)
    #hedge_products += generate_day_products(days_start_ts, days_end_ts)
    #hedge_products += generate_weekend_products(days_start_ts, weeks_end_ts)
    hedge_products += generate_week_products(days_start_ts, weeks_end_ts)

    return hedge_products


def generate_for_tiwag_vs_500gwh(dt: pd.Timestamp) -> List[HedgeProduct]:
    """
    :return: List of default HedgeProduct objects

    NOTE: Needs to be in the correct timezone!
    """
    hedge_products = []

    dt = dt.round('D')
    start_date = dt - YearBegin(3)
    end_date = dt + YearBegin(4)
    hedge_products += generate_month_products(start_date, end_date)
    hedge_products += generate_quarter_products(start_date, end_date)
    hedge_products += generate_year_products(start_date, end_date)

    return hedge_products


def generate_disjunct_quotes_for_pnl_explanation(dt: pd.Timestamp) -> List[HedgeProduct]:
    """
    :return: List of default HedgeProduct objects

    NOTE: Only look at current year!!
    """
    hedge_products = []
    dt = dt.round('D')
    end_of_year = dt + YearBegin()

    # DAYS
    days_start_ts = dt
    days_end_ts = (days_start_ts + Day(3)).round('D')  # Monday
    days_end_ts = min(days_end_ts, end_of_year)

    # WEEKS
    weeks_start_ts = days_end_ts + Week(weekday=0) - Week(weekday=0)
    weeks_end_ts = (days_end_ts + Week(weekday=0) + Week(1)).round('D')  # Balance of Week, Week+1, Week+2
    weeks_end_ts = min(weeks_end_ts, end_of_year)

    # Generate smaller products covering current and FrontMonth
    hedge_products += generate_day_products(days_start_ts, days_end_ts)
    hedge_products += generate_weekend_products(weeks_start_ts, weeks_end_ts)
    hedge_products += generate_weekday_products(weeks_start_ts, weeks_end_ts, start_cutoff=days_end_ts + Week(weekday=0))


    weeks_start_ts = (days_end_ts + Week(weekday=0) + Week(1)).round('D')
    weeks_end_ts = (days_end_ts + Week(weekday=0) + Week(4)).round('D')
    hedge_products += generate_week_products(weeks_start_ts, weeks_end_ts,)

    # MONTHS & QUARTERS
    start_date_month = dt - MonthBegin()  # Balance of Month
    end_date_month = start_date_month + MonthBegin(4)
    hedge_products += generate_month_products(start_date_month, end_date_month, start_cutoff=weeks_end_ts)

    start_date_q = start_date_month + QuarterBegin()
    end_date_q = end_of_year + YearBegin()
    hedge_products += generate_quarter_products(start_date_q, end_date_q, start_cutoff=end_date_month)

    return hedge_products


def generate_for_historical_prices(dt: pd.Timestamp) -> List[HedgeProduct]:
    """
    :return: List of default HedgeProduct objects

    NOTE: Needs to be in the correct timezone!
    """
    hedge_products = []

    dt = dt.round('D')
    hedge_products += generate_month_products(dt, dt + MonthBegin(6))
    hedge_products += generate_quarter_products(dt, dt + QuarterBegin(5))
    hedge_products += generate_year_products(dt, dt + YearBegin(4))

    return hedge_products


def generate_m_q_y(dt) -> List[HedgeProduct]:
    """
    :return: List of default HedgeProduct objects

    NOTE: Needs to be in the correct timezone!
    """
    hedge_products = []
    dt = dt.round('D')
    start_date = dt - YearBegin()
    end_date = dt + YearBegin()
    hedge_products += generate_month_products(start_date, end_date)
    hedge_products += generate_quarter_products(start_date, end_date)
    hedge_products += generate_year_products(start_date, end_date)

    return hedge_products


def generate_day_products(start_date, end_date, profile: str):
    """
    Note: Naming convention is affected by the timezones of method inputs
    """
    start_dates = pd.date_range(start_date, end_date, freq='D', inclusive='left')
    end_dates = pd.DatetimeIndex([(dt + Day(1)).round('D') for dt in start_dates])  # Ensure wall-time 0'clock

    names = [f'D_{profile}_{start_date:%Y_%m_%d}' for start_date in start_dates]
    profiles = [profile for _ in names]

    return generate_products(names, start_dates, end_dates, profiles)


def generate_weekend_products(start_date, end_date, profile:str):
    """
    Note: Naming convention is affected by the timezones of method inputs
    """
    # Move start_date to latest Saturday
    start_date = (start_date + Week(weekday=5)).round('D')

    start_dates = pd.date_range(start_date, end_date, freq='W-SAT', inclusive='left')
    end_dates = pd.DatetimeIndex([(dt + Day(2)).round('D') for dt in start_dates])  # Ensure wall-time 0'clock
    if end_dates.shape[0] == 0: end_dates = end_dates.tz_localize("Europe/Berlin")

    mask = (start_dates < end_date) & (end_dates >= start_date)
    start_dates = start_dates[mask]
    end_dates = end_dates[mask]

 # TODO: use isocalendar?
    #names = [f'W_{profile}_{start_date.isocalendar().year}_{start_date.isocalendar().week}' for start_date in start_dates]
    names = [f'WEnd_{profile}_{start_date:%Y}_{start_date:%V}_{start_date:%d}-{start_date+Hour(25):%d/%m/%y}' for start_date in start_dates]
    profiles = [profile for _ in names]

    return generate_products(names, start_dates, end_dates, profiles)


def generate_week_products(start_date, end_date, profile: str, start_cutoff=None, end_cutoff=None):
    """
    Note: Naming convention is affected by the timezones of method inputs
    """
    # Move start_date to latest Monday
    start_dates = pd.date_range(start_date, end_date, freq='W-MON', inclusive='left')
    end_dates = pd.DatetimeIndex([(dt + Day(7)).round('D') for dt in start_dates])  # Ensure wall-time 0'clock
    mask = (start_dates < end_date) & (end_dates >= start_date)
    start_dates = start_dates[mask]
    end_dates = end_dates[mask]

    if start_cutoff:
        start_dates = list(start_dates[start_dates > start_cutoff])
        start_dates = [start_cutoff] + start_dates
        select = len(start_dates)
        end_dates = end_dates[-select:]
    if end_cutoff:
        end_dates = list(end_dates[end_dates < end_cutoff])
        end_dates = end_dates + [end_cutoff]
        select = len(end_dates)
        start_dates = start_dates[select:]

    names = [f'W_{profile}_{start_date.isocalendar().year}_{start_date.isocalendar().week}' for start_date in start_dates]
    profiles = [profile for _ in names]

    return generate_products(names, start_dates, end_dates, profiles)





def generate_weekday_products(start_date, end_date, profile: str, start_cutoff=None, end_cutoff=None):
    """
    Note: Naming convention is affected by the timezones of method inputs
    """
    # Move start_date to latest Monday
    start_dates = pd.date_range(start_date, end_date, freq='W-MON', inclusive='left')
    end_dates = pd.DatetimeIndex([(dt + Day(5)).round('D') for dt in start_dates])  # Ensure wall-time 0'clock
    mask = (start_dates < end_date) & (end_dates >= start_date)
    start_dates = start_dates[mask]
    end_dates = end_dates[mask]

    if start_cutoff:
        start_dates = list(start_dates[start_dates > start_cutoff])
        start_dates = [start_cutoff] + start_dates
        select = len(start_dates)
        end_dates = end_dates[-select:]
    if end_cutoff:
        end_dates = list(end_dates[end_dates < end_cutoff])
        end_dates = end_dates + [end_cutoff]
        select = len(end_dates)
        start_dates = start_dates[select:]

    names = [f'Weekdays_{profile}_{start_date:%Y}_{start_date:%V}' for start_date in start_dates]
    profiles = [profile for _ in names]

    return generate_products(names, start_dates, end_dates, profiles)



def generate_month_products(start_date, end_date, profile: str, start_cutoff=None, end_cutoff=None):
    """
    Note: Naming convention is affected by the timezones of method inputs
    """

    # Move start_date to latest MonthBegin
    start_date = start_date + MonthBegin(1) - MonthBegin(1)

    start_dates = pd.date_range(start_date, end_date, freq='MS', inclusive='left')
    end_dates = start_dates + MonthBegin(1)

    if start_cutoff:
        start_dates = list(start_dates[start_dates > start_cutoff])
        start_dates = [start_cutoff] + start_dates
        select = len(start_dates)
        end_dates = end_dates[-select:]
    if end_cutoff:
        end_dates = list(end_dates[end_dates < end_cutoff])
        end_dates = end_dates + [end_cutoff]
        select = len(end_dates)
        start_dates = start_dates[select:]

    names = [f'M_{profile}_{start_date:%Y_%m}' for start_date in start_dates]
    profiles = [profile for _ in names]

    return generate_products(names, start_dates, end_dates, profiles)





def generate_quarter_products(start_date, end_date, profile:str, start_cutoff=None, end_cutoff=None):
    """
    Note: Naming convention is affected by the timezones of method inputs
    """
    # Move start_date to latest QuarterBegin
    if start_date == end_date:
        return []

    start_date = start_date + QuarterBegin(startingMonth=1) - QuarterBegin(startingMonth=1)

    start_dates = pd.date_range(start_date, end_date, freq='QS', inclusive='left')
    end_dates = start_dates + QuarterBegin(startingMonth=1)

    if start_cutoff:
        start_dates = list(start_dates[start_dates > start_cutoff])
        start_dates = [start_cutoff] + start_dates
        select = len(start_dates)
        end_dates = end_dates[-select:]
    if end_cutoff:
        end_dates = list(end_dates[end_dates < end_cutoff])
        end_dates = end_dates + [end_cutoff]
        select = len(end_dates)
        start_dates = start_dates[select:]

    names = [f'Q_{profile}_{start_date:%Y}_{start_date.quarter:d}' for start_date in start_dates]
    profiles = [profile for _ in names]

    return generate_products(names, start_dates, end_dates, profiles)




def generate_year_products(start_date, end_date, profile:str, start_cutoff=None, end_cutoff=None):
    """
    Note: Naming convention is affected by the timezones of method inputs
    """
    # Move start_date to latest YearBegin
    start_date = start_date + YearBegin(1) - YearBegin(1)

    start_dates = pd.date_range(start_date, end_date, freq='YS', inclusive='left')
    end_dates = start_dates + YearBegin(1)

    if start_cutoff:
        start_dates = list(start_dates[start_dates > start_cutoff])
        start_dates = [start_cutoff] + start_dates
        select = len(start_dates)
        end_dates = end_dates[-select:]
    if end_cutoff:
        end_dates = list(end_dates[end_dates < end_cutoff])
        end_dates = end_dates + [end_cutoff]
        select = len(end_dates)
        start_dates = start_dates[select:]

    names = [f'Y_{profile}_{start_date:%Y}' for start_date in start_dates]
    profiles = [profile for _ in names]

    return generate_products(names, start_dates, end_dates, profiles)


def generate_products(names, start_dates, end_dates, profiles):
    result = [HedgeProduct(*args) for args in zip(names, start_dates, end_dates, profiles)]
    return result
