import traceback

from playwright.sync_api import sync_playwright
import numpy as np
import pandas as pd
import uuid
from pathlib import Path

from loom.spooling.source.universal_scraper import UniversalScraper

pd.set_option('display.max_rows', 10000)
pd.set_option('display.max_columns', 500)
pd.set_option('display.width', 10000)
pd.set_option('display.max_colwidth', None)

tz = "Europe/Berlin"


class SevereWeatherEurope(UniversalScraper):

    path_folder = Path(__file__).parent.resolve()

    url_main = "https://www.severe-weather.eu/"

    def run_scraper(self):
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page1 = browser.new_page()
                page2 = browser.new_page()
                page1.goto(self.url_main)

                elements = page1.locator('[class="excerpt-link"]')

                for el in elements.all():
                    link = el.get_attribute("href")
                    title = el.get_attribute("title")

                    if title is None: continue
                    _uuid = uuid.uuid5(uuid.NAMESPACE_DNS, link)

                    if self.check_if_scrap_already_exists(_uuid):
                        print("Already scraped:", link)
                        continue

                    page2.goto(link)

                    ts_published = pd.NaT
                    _elements = page2.locator('[id="content"] *')
                    _elements.count()

                    for el in _elements.all():
                        ts_str = el.get_attribute("datetime")
                        if ts_str is not None:
                            ts_published = pd.Timestamp(ts_str, tz=tz)
                            break

                    elements = page2.locator('p')
                    count = elements.count()
                    str_elements = []

                    for el in elements.all():
                        str_elements.append( el.inner_text())
                    text = '\n'.join(str_elements)

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

                browser.close()

        except Exception as e:
            print(traceback.format_exc())


if __name__ == "__main__":
    SevereWeatherEurope().run_scraper()
    SevereWeatherEurope().generate_references()

