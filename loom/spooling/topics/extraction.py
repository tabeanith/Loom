import os
import re
from pathlib import Path
import json
import pandas as pd
import numpy as np

from pandas.tseries.offsets import MonthBegin
from datetime import datetime, date

pd.set_option('display.max_rows', 10000)
pd.set_option('display.max_columns', 500)
pd.set_option('display.width', 10000)
pd.set_option('display.max_colwidth', None)


tz = "Europe/Berlin"



def extract_answer_yes_no(txt, first_string):
    rows = txt.split("\n")

    for row in rows:
        _row = row.lower()
        #print(_row)

        i_first_string = _row.find(first_string)
        if (i_first_string > -1) and (i_first_string < 15):

            __row = _row.split(":")[1][0:15]
            #print(__row)

            if "yes" in __row:
                return 1
            if "no" in __row:
                return 0
            if "impl" in __row:
                return 0.25

    return np.nan


def extract_answer_int(txt, first_string):
    rows = txt.split("\n")

    for row in rows:
        _row = row.lower()

        i_first_string = _row.find(first_string)
        if (i_first_string > -1) and (i_first_string < 15):

            __row = _row.split(":")[1][0:15]

            mtch = re.findall(r"\d+", row)
            if len(mtch) > 0:
                return int(mtch[0])

    return np.nan



def extract_answer_int_four_season(txt, first_string):
    rows = txt.split("\n")

    for row in rows:
        _row = row.lower()

        i_first_string = _row.find(first_string)
        if (i_first_string > -1) and (i_first_string < 15):

            __row = _row.split(":")[1]

            if ("spring" in __row) and ("summer" in __row) and ("fall" in __row) and ("winter" in __row):

                mtch = re.findall(r"\d+", row)
                if len(mtch) >= 4:
                    return [int(mtch[0]), int(mtch[1]), int(mtch[2]), int(mtch[3])]

    return [np.nan, np.nan, np.nan, np.nan]


def extract_answer_multiple_floats(txt, first_string):
    rows = txt.split("\n")

    for row in rows:
        _row = row.lower()

        i_first_string = _row.find(first_string)
        if (i_first_string > -1) and (i_first_string < 3):

            __row = _row.split(":")[1][0:15]

            mtch = re.findall(r'-?\d+\.\d+', row)
            return [float(x) for x in mtch]

    return []





def extract_q(q_code, txt):
    rows = txt.split("\n")
    data = {
        f"{q_code}_phrase": rows[0],
        f"{q_code}_answer": rows[2],
        f"{q_code}_r" : 0,
    }

    for row in rows:
        row = row.lower()

        if "relevance: " in row:
            if "yes" in row:
                data[f"{q_code}_r"] = 1
            if "implicit" in row:
                data[f"{q_code}_r"] = 0.25
        if "severity score: " in row:
            mtch = re.findall(r"\d+", row)

            if "spring" in row:
                data[f"{q_code}_q1"] = int(mtch[0])
                data[f"{q_code}_q2"] = int(mtch[1])
                data[f"{q_code}_q3"] = int(mtch[2])
                data[f"{q_code}_q4"] = int(mtch[3])
            else:
                data[f"{q_code}_q"] = int(mtch[0])
    return data


def roll_qs_to_months(timestamp, q1, q2, q3, q4, time):
    # spring, summer, fall, winter
    #                  Jan  Feb  Mar  Apr  Mai  Jun  Jul  Aug  Sep  Oct  Nov  Dec
    spring = np.array([0.0, 0.1, 0.8, 1.0, 0.5, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
    summer = np.array([0.0, 0.0, 0.0, 0.0, 0.5, 1.0, 1.0, 1.0, 0.4, 0.0, 0.0, 0.0])
    fall   = np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.6, 1.0, 0.5, 0.0])
    winter = np.array([1.0, 0.9, 0.2, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.5, 1.0])

    total = spring * q1 + summer * q2 + fall * q3 + winter * q4

    the_month_of_publishing = timestamp.month
    months = np.arange(the_month_of_publishing, 12 + 1).tolist() + np.arange(1, the_month_of_publishing).tolist()
    values = [total[i-1] for i in months]

    ts_start = pd.Timestamp(date(timestamp.year, timestamp.month, 1), tz=tz)
    months = pd.date_range(ts_start, freq="MS", periods=12)
    result = pd.Series(values, index=months)
    result.iloc[-3] = np.nan
    result.iloc[-2] = np.nan
    result.iloc[-1] = np.nan
    result = result.ffill()

    # TODO:
    # Factor in a deline for the months M+10, M+11, M+12
    # Consider the factor time to prolonge extreme pattern (maybe increase the values at the front?)

    return result