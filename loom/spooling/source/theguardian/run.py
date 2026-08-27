import traceback

from playwright.sync_api import sync_playwright
import numpy as np
import pandas as pd
import uuid
from pathlib import Path
import os
import json
from loom.spooling.source.universal_scraper import UniversalScraper

pd.set_option('display.max_rows', 10000)
pd.set_option('display.max_columns', 500)
pd.set_option('display.width', 10000)
pd.set_option('display.max_colwidth', None)

tz = "Europe/Berlin"


from datetime import datetime, timezone, timedelta

TZ_OFFSETS = {
    "CET": timedelta(hours=1),
    "CEST": timedelta(hours=2),
    "UTC": timedelta(hours=0),
    "GMT": timedelta(hours=0),
    "BST": timedelta(hours=1),
    "EST": timedelta(hours=-5),
    "EDT": timedelta(hours=-4),
    # add more as needed
}

def parse_timestamp(s: str) -> datetime:
    naive_part, tz_abbr = s.rsplit(" ", 1)
    dt_naive = datetime.strptime(naive_part, "%a %d %b %Y %H.%M")

    if tz_abbr not in TZ_OFFSETS:
        raise ValueError(f"Unknown timezone abbreviation: {tz_abbr}")

    tz = timezone(TZ_OFFSETS[tz_abbr])
    to_ts = dt_naive.replace(tzinfo=tz)
    return pd.Timestamp(to_ts)


class TheGuardian(UniversalScraper):

    path_folder = Path(__file__).parent.resolve()

    url_main = "https://www.theguardian.com"

    sub_pages = [
        "https://www.theguardian.com/world/strait-of-hormuz",
        "https://www.theguardian.com/world/strait-of-hormuz?page=2",
        "https://www.theguardian.com/world/us-israel-war-on-iran",
        "https://www.theguardian.com/world/us-israel-war-on-iran?page=2",
        "https://www.theguardian.com/environment/series/weather-tracker",
        "https://www.theguardian.com/environment/series/weather-tracker",
        "https://www.theguardian.com/environment/series/weather-tracker?page=2",
        "https://www.theguardian.com/world/germany",
        "https://www.theguardian.com/world",
        "https://www.theguardian.com/world/europe-news",
        "https://www.theguardian.com/us-news",
        "https://www.theguardian.com/global-development",
        "https://www.theguardian.com/environment/climate-crisis",
        "https://www.theguardian.com/environment",
    ]


    def run_scraper(self):
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)

                for sub_page in self.sub_pages:
                    page1 = browser.new_page()
                    page1.goto(sub_page)

                    elements = page1.locator("body [href]")

                    for el in elements.all():

                        # ------------------------------ Search for article links --------------------------------

                        link = el.get_attribute("href")
                        title = el.get_attribute("aria-label")
                        if link is None: continue
                        if title is None: continue

                        if "https" not in link:
                            link = "https://www.theguardian.com" + link

                        _uuid = uuid.uuid5(uuid.NAMESPACE_DNS, link)
                        if self.check_if_scrap_already_exists(_uuid):
                            print("Already scraped:", link)
                            continue

                        # -------------------------------------- Scrap article -----------------------------------------

                        print(link, title)

                        try:
                            page2 = browser.new_page()
                            page2.goto(link)

                            _elements = page2.locator('[data-gu-name="dateline"]')
                            for el in _elements.all():
                                ts_str = el.inner_text()
                                ts_str = ts_str.split("First published on")[0]
                                ts_published = parse_timestamp(ts_str)

                            _elements = page2.locator('[data-gu-name="headline"]')
                            for el in _elements.all():
                                title = el.inner_text()

                            _elements = page2.locator('[id="maincontent"] p')

                            text = []
                            for el in _elements.all():
                                text.append(el.inner_text())
                            text = "\n".join(text)

                            # Directly save scraped content
                            _data = {
                                "uuid": str(_uuid),
                                "title": title,
                                "author": "",
                                "url": link,
                                "posted_url": link,
                                "is_linking_to_external_website": False,
                                "timestamp": pd.Timestamp(ts_published).tz_convert(tz=tz).isoformat(),
                                "source": self.url_main,
                                "crawled_at": pd.Timestamp.now(tz=tz).isoformat(),
                                "text": text,
                                }

                            self.save_scrap(_data)

                        except Exception as e:
                            #print(traceback.format_exc())
                            print("Scraping failed:", link)

                browser.close()

        except Exception as e:
            print(traceback.format_exc())


if __name__ == "__main__":
    TheGuardian().run_scraper()
    TheGuardian().generate_references()

