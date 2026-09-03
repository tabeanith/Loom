
from loom.spooling.source.severe_weather_europe.run import SevereWeatherEurope
from loom.spooling.source.theguardian.run import TheGuardian
from loom.spooling.source.reuters.run import Reuters

from loom.spooling.topics.t01_eu_power.topic import T01_EU_Power
from loom.spooling.topics.t02_weather.topic import T02_Weather
from loom.spooling.topics.t03_gas_fuel.topic import T03_Gas_Fuel
from loom.spooling.topics.t11_us_stocks.topic import T11_US_Stocks

from loom.spooling.llm.ask_and_answer import ask_and_answer
from loom.spooling.llm.ask_and_answer import ask_and_answer_for_uuid

from loom.spooling.source.references import load_references

import pandas as pd
from pandas.tseries.offsets import Day
tz = "Europe/Berlin"


if __name__ == "__main__":

    # ------------------------------------------  Work mode  ---------------------------------------------------------
    scrape_for_new_articles = True
    scrape_for_new_articles = True

    use_ai = True
    #use_ai = False


    # ----------------------------  Check for new links appearing on websites ----------------------------------------
    if scrape_for_new_articles:

        if True:
            SevereWeatherEurope().run_scraper()
            SevereWeatherEurope().generate_references()
        if True:
            Reuters().run_scraper()
            Reuters().generate_references()
        if True:
            TheGuardian().run_scraper()
            TheGuardian().generate_references()

        TheGuardian().sanity_check_references()
        Reuters().sanity_check_references()
        SevereWeatherEurope().sanity_check_references()


    # -------------------------  Check relevant topics and reviewing -------------------------------------------------

    topic1 = T01_EU_Power()
    topic2 = T02_Weather()
    topic3 = T03_Gas_Fuel()
    topic11 = T11_US_Stocks()

    days_back_in_time = 25

    print("\n Check for new aricles to be processed by AI \n")

    # EU Power
    for topic in [topic2, topic3]:
        ask_and_answer(TheGuardian(), topic, pd.Timestamp.now(tz=tz) - Day(days_back_in_time), use_ai=use_ai)
        ask_and_answer(Reuters(), topic, pd.Timestamp.now(tz=tz) - Day(days_back_in_time), use_ai=use_ai)
        ask_and_answer(SevereWeatherEurope(), topic, pd.Timestamp.now(tz=tz) - Day(days_back_in_time), use_ai=use_ai)

    # US Stocks
    for topic in [topic11]:
        ask_and_answer(Reuters(), topic, pd.Timestamp.now(tz=tz) - Day(days_back_in_time), use_ai=True)




