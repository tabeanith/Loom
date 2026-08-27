
from loom.spooling.source.severe_weather_europe.run import SevereWeatherEurope
from loom.spooling.source.theguardian.run import TheGuardian
from loom.spooling.source.reuters.run import Reuters

from loom.spooling.topics.t01_weather.topic import T01_Weather
from loom.spooling.topics.t02_gas_fuel.topic import T02_Gas_Fuel

from loom.spooling.ask_and_answer import ask_and_answer

import pandas as pd
from pandas.tseries.offsets import Day
tz = "Europe/Berlin"


if __name__ == "__main__":

    # ------------------------------------------  Work mode  ---------------------------------------------------------
    scrape_for_new_articles = False
   # scrape_for_new_articles = True

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

    topic = T01_Weather()
    topic = T02_Gas_Fuel()

    days_back_in_time = 100

    print("\n Check for new aricles to be processed by AI \n")

    ask_and_answer(TheGuardian(), topic, pd.Timestamp.now(tz=tz) - Day(days_back_in_time), use_ai=use_ai)
    ask_and_answer(Reuters(), topic, pd.Timestamp.now(tz=tz) - Day(days_back_in_time), use_ai=use_ai)
    ask_and_answer(SevereWeatherEurope(), topic, pd.Timestamp.now(tz=tz) - Day(days_back_in_time), use_ai=use_ai)




