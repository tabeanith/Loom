import os
import traceback
import time

from datetime import datetime, date
import numpy as np
import pandas as pd
from pandas.tseries.offsets import Hour, Day, MonthBegin, YearBegin, BusinessDay

from usp.common.data.dbb import DBBConnector, DBBConfig

from catt.utils.time import Timer
from catt.data.dbb.identifiers_OLD import live_curve_fuels


class QueryDBB:
    tz = 'Europe/Berlin'

    def __init__(self, environment="PROD"):
        environment = environment.upper()
        self.config = DBBConfig.from_defaults(
            dict(
                http=
                dict(
                    auth=
                    dict(
                        method="DBB",
                        user=os.environ[f'DBB_{environment}_ACCESS_USER'],
                        secret=os.environ[f'DBB_{environment}_ACCESS_SECRET'],
                        pool_id=os.environ[f'DBB_{environment}_POOL_ID'],
                        client_id=os.environ[f'DBB_{environment}_CLIENT_ID'],
                        pool_region=os.environ[f'DBB_{environment}_POOL_REGION'])
                )
            )
        )
        self.connector = DBBConnector(self.config)

    def get_spot_power_germany(self,
                               start_ts: pd.Timestamp,
                               end_ts_exclusive: pd.Timestamp):
        query_not_done = True

        while query_not_done:
            try:
                _spot = self.connector.read_price('MKN2LD', start_ts, end_ts_exclusive)
                spot = _spot[(_spot.index >= start_ts) & (_spot.index < end_ts_exclusive)]
                spot = spot[~spot.index.duplicated(keep="first")]
                query_not_done = False
            except:
                traceback.print_exc()
                print("Wait 5 seconds...")
                time.sleep(5)
                # Timeout? Wait, try again
        return spot

    def get_spot_gas_the(self,
                         start_ts: pd.Timestamp,
                         end_ts_exclusive: pd.Timestamp):
        _spot = self.connector.read_price('QW6KYL', start_ts, end_ts_exclusive)
        spot = _spot[(_spot.index >= start_ts) & (_spot.index < end_ts_exclusive)]
        spot = spot[~spot.index.duplicated(keep="first")]
        return spot

    def get_fuels_for_dayahead_from_live_curve(self,
                                               start_ts: pd.Timestamp,
                                               end_ts_exclusive: pd.Timestamp,
                                               as_of_ts: pd.Timestamp):
        """
        ToDo: Make this into one per Commodity
        :param start_date:
        :param end_date:
        :return:
        """
        start_ts = start_ts.floor("D")
        end_ts_exclusive = end_ts_exclusive.floor("D")
        with Timer("Query DBB for fuel prices"):
            start = start_ts.tz_convert(QueryDBB.tz) - MonthBegin(1)
            end = end_ts_exclusive.tz_convert(QueryDBB.tz) + MonthBegin(1)

            historical_bd = pd.bdate_range(start_ts - BusinessDay(1), end_ts_exclusive)
            today = as_of_ts.floor("D")
            historical_bd = historical_bd[historical_bd < today] + Hour(10)
            historical_bd = historical_bd.union([as_of_ts])
            _prices = []
            _latest_curves = {}

            print(f"Querying DBB for curves")
            print(f"Oldest issue: {historical_bd[0]}")
            print(f"Newest issue: {historical_bd[-1]}")

            for key, uuid in live_curve_fuels.items():
                with Timer(f"Querying dbb for {key} [{uuid}] (assembled via {len(historical_bd)} requests)"):
                    for dt in historical_bd:
                        data = {}
                        curve = self.connector.read_curve(uuid,
                                                          start=start_ts - MonthBegin(1),
                                                          end=end_ts_exclusive + MonthBegin(3),
                                                          params={"latestReferenceDate": True,
                                                                  "referenceDateTo": dt,
                                                                  "referenceDateFrom": dt - Day(1)})
                        if curve.empty:
                            data["price"] = np.NaN
                        else:
                            _latest_curves[key] = curve
                            data["price"] = curve[0]
                        data["date"] = dt + Day(1)  # DayAhead delivery!
                        data["market"] = key
                        _prices.append(data)

            # TODO: Make FX (rates) more exact, since Coal is at least FrontMonth

            for key, c in _latest_curves.items():
                _latest_curves[key] = c.resample("D").ffill()

            forward_curves = pd.DataFrame(_latest_curves).ffill().bfill()

            # Fill weekends/missing state with ffill
            prices = pd.DataFrame(_prices).set_index(["market", "date"]).unstack("market")
            prices.columns = prices.columns.droplevel(0)
            spot_prices = prices[:-1].resample("D").mean()

            forward_curves = forward_curves[(forward_curves.index > prices.index[-1]) & (forward_curves.index <= end)]

            final_prices = pd.concat([spot_prices, forward_curves], axis="rows")
            final_index = pd.date_range(start, end_ts_exclusive, freq="H", tz="Europe/Berlin", inclusive="left")
            final_prices = final_prices.reindex(final_index).bfill().ffill()

            final_prices = final_prices[(final_prices.index > start_ts) & (final_prices.index <= end_ts_exclusive)]

            final_prices["fx_usd_eur"]  # ToDo: Correct data?

            final_prices["coal_api2_eur"] = final_prices["coal_api2_usd"] * 0.8
            return final_prices

    def _get_curve(self, dbb_id: str, latest_as_of_ts: pd.Timestamp, years: int, search_window: pd.tseries.offsets):
        query_not_done = True

        while query_not_done:
            try:
                latest_date = latest_as_of_ts.tz_convert(QueryDBB.tz)
                end = latest_date + YearBegin(years)

                curve = self.connector.read_curves_df(dbb_id, latest_date, end,
                                                  params={"latestReferenceDate": True,
                                                          "referenceDateTo": latest_as_of_ts,
                                                          "referenceDateFrom": latest_as_of_ts - search_window})
                curve.index = pd.to_datetime(curve["begin"], utc=True).dt.tz_convert(QueryDBB.tz)
                curve = curve["value"]
                curve = curve.resample('H').ffill()  # Hour 2b in October is NaN
                query_not_done = False
            except:
                traceback.print_exc()
                print("Wait 5 seconds...")
                time.sleep(5)
                # Timeout? Wait, try again
        return curve

    def get_power_germany_from_live_curve(self, latest_as_of_ts: pd.Timestamp, years: int):
        """
        First live curve in the morning seems to be available @ 08:02 AM CET
        """
        return self._get_curve('B0IYOQ', latest_as_of_ts, years, Hour(1))

    def get_carbon_eua_from_live_curve(self, latest_as_of_ts: pd.Timestamp, years: int):
        return self._get_curve('B3QFE4', latest_as_of_ts, years + 1, Hour(1))

    def get_gas_the_from_live_curve(self, latest_as_of_ts: pd.Timestamp, years: int):
        return self._get_curve('NJ5EB1', latest_as_of_ts, years, Hour(1))

    def get_coal_api2_eur_from_live_curve(self, latest_as_of_ts: pd.Timestamp, years: int):
        curve = self._get_curve('QI5BL2', latest_as_of_ts, years + 1, Hour(1))
        #curve = self._get_curve('99BAP1', latest_as_of_ts, years + 1, Hour(1))
        curve = curve[curve.index.year < (latest_as_of_ts + YearBegin(years)).year]
        return curve

    def get_fx_usd_eur_from_live_curve(self, latest_as_of_ts: pd.Timestamp, years: int):
        return self._get_curve('9TXA8U', latest_as_of_ts, years, Hour(1))

    def get_power_germany_from_eod_curve(self, latest_as_of_ts: pd.Timestamp, years: int):
        return self._get_curve('L5A2UU', latest_as_of_ts, years, Day(5))


if __name__ == "__main__":
    dbb = QueryDBB()

    # dbb._get_curve('B0IYOQ', pd.Timestamp.now().tz_localize(dbb.tz), 3, Day(15))
    # dbb.get_historical_dayahead_from_live_curve(start_date=datetime(2022, 2, 1), end_date=datetime(2022, 2, 21))

    # testing
    ts_start = pd.Timestamp(date(2021, 6, 3)).tz_localize("Europe/Berlin")
    window = YearBegin(7)
    # window = Day(20)
    curve = QueryDBB()._get_curve('L5A2UU', ts_start, 2, window)

    print(curve)
