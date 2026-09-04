import os
import re
from pathlib import Path
import json
import pandas as pd
import numpy as np
from datetime import date
import matplotlib.pyplot as plt
from pandas.tseries.offsets import MonthBegin, Day, Hour, Week, BDay

import uuid
from rich.console import Console
from rich.markdown import Markdown


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

from loom.spooling.source.universal_scraper import find_scraped_article_content

tz = "Europe/Berlin"




if __name__ == "__main__":
    console = Console()

    link = ""
    _uuid = uuid.uuid5(uuid.NAMESPACE_DNS, link)

    txt = find_scraped_article_content(_uuid)

    txtai = T11_US_Stocks.load_llm_answer(_uuid)




    md_txt = Markdown(txt)
    md_txtai = Markdown(txtai)

    console.print(md_txt)
    console.print(md_txtai)

