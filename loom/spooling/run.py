
from loom.spooling.source.severe_weather_europe.run import SevereWeatherEurope
from loom.spooling.source.theguardian.run import TheGuardian
from loom.spooling.source.reuters.run import Reuters

from loom.spooling.topics.t01_eu_power.topic import T01_EU_Power
from loom.spooling.topics.t02_weather.topic import T02_Weather
from loom.spooling.topics.t03_gas_fuel.topic import T03_Gas_Fuel
from loom.spooling.topics.t10_us_rates.topic import T10_US_Rates
from loom.spooling.topics.t11_us_stocks.topic import T11_US_Stocks

from loom.spooling.llm.ask_and_answer import ask_and_save_answer
from loom.spooling.llm.ask_and_answer import TBD_ask_and_save_answer
from loom.spooling.llm.ask_and_answer import ask_and_answer_for_uuid

from loom.spooling.source.references import load_references

import pandas as pd
from pandas.tseries.offsets import Day
tz = "Europe/Berlin"


if __name__ == "__main__":

    # ------------------------------------------  Work mode  ---------------------------------------------------------
    scrape_for_new_articles = True
    scrape_for_new_articles = False

    use_ai = True
    #use_ai = False

    topic1 = T01_EU_Power()
    topic2 = T02_Weather()
    topic3 = T03_Gas_Fuel()
    topic10 = T10_US_Rates()
    topic11 = T11_US_Stocks()


    # ----------------------------  Check for new links appearing on websites ----------------------------------------
    if scrape_for_new_articles:

        # US Interest Rates
        Reuters().run_scraper_to_topic_pipeline(["fed", "hawkish", "dovish"], topic10)

        # EU weather
        SevereWeatherEurope().run_scraper_to_topic_pipeline(topic2)
        Reuters().run_scraper_to_topic_pipeline(["europe weather", "europe climate change"], topic2)

        # Gas market
        Reuters().run_scraper_to_topic_pipeline(["natural gas", "germany natural gas", "europe lng", "germany lng", "germany power prices"], topic3)



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

    days_back_in_time = 5

    print("\n Check for new aricles to be processed by AI \n")

    for topic in [topic10]:
        ask_and_save_answer(topic, pd.Timestamp.now(tz=tz) - Day(days_back_in_time), use_ai=True, ignore_existing_answer=True)

    # Go through all topics
    for topic in [topic2, topic3]:
        ask_and_save_answer(topic, pd.Timestamp.now(tz=tz) - Day(days_back_in_time), use_ai=True, ignore_existing_answer=False)



