import traceback

from playwright.sync_api import sync_playwright
import numpy as np
import pandas as pd
import uuid
from pathlib import Path
import os
import json
from loom.spooling.source.universal_scraper import UniversalScraper
import re

pd.set_option('display.max_rows', 10000)
pd.set_option('display.max_columns', 500)
pd.set_option('display.width', 10000)
pd.set_option('display.max_colwidth', None)

tz = "Europe/Berlin"


from datetime import datetime, timezone, timedelta
from time import sleep

class Reuters(UniversalScraper):

    path_folder = Path(__file__).parent.resolve()

    url_main = "https://www.reuters.com"

    sub_pages = [
        # Energy markets
        "https://www.reuters.com/site-search/?query=energy",
        "https://www.reuters.com/site-search/?query=energy&offset=20",
        "https://www.reuters.com/site-search/?query=germany",
        "https://www.reuters.com/site-search/?query=germany&offset=20",
        "https://www.reuters.com/site-search/?query=natural+gas",
        "https://www.reuters.com/site-search/?query=natural+gas&offset=20",
        "https://www.reuters.com/site-search/?query=power+plant",
        "https://www.reuters.com/site-search/?query=power+plant&offset=20",
        "https://www.reuters.com/authors/ron-bousso/",
        "https://www.reuters.com/authors/gavin-maguire/",
        "https://www.reuters.com/authors/mike-dolan/",
        "https://www.reuters.com/authors/forrest-crellin/",
        "https://www.reuters.com/authors/susanna-twidale/",
        "https://www.reuters.com/authors/sharon-kits-kimathi/",
        "https://www.reuters.com/authors/marwa-rashad/",
        "https://www.reuters.com/authors/kate-abnett/",
        "https://www.reuters.com/authors/nina-chestney/",
        "https://www.reuters.com/business/energy",
        "https://www.reuters.com/world/europe/",
        # US Futures
        "https://www.reuters.com/site-search/?query=stocks",
        "https://www.reuters.com/site-search/?query=stocks&offset=20",
        "https://www.reuters.com/site-search/?query=fed",
        "https://www.reuters.com/site-search/?query=fed&offset=20",
        "https://www.reuters.com/site-search/?query=bonds",
        "https://www.reuters.com/site-search/?query=bonds&offset=20",
        "https://www.reuters.com/site-search/?query=trade",
        "https://www.reuters.com/site-search/?query=trade&offset=20",
        "https://www.reuters.com/world/",
        "https://www.reuters.com/markets/us/",
        "https://www.reuters.com/business/",
        "https://www.reuters.com/authors/caroline-valetkevitch/",
        "https://www.reuters.com/authors/niket-nishant/",
        "https://www.reuters.com/authors/saeed-azhar/",
        "https://www.reuters.com/authors/ann-saphir/",
        "https://www.reuters.com/authors/howard-schneider/",
        "https://www.reuters.com/authors/parisa-hafezi/",
        "https://www.reuters.com/authors/david-lawder/",
    ]


    def run_scraper_to_topic_pipeline(self, search_keywords, topic):
        pages = []

        for keyword in search_keywords:
            page1 = f"https://www.reuters.com/site-search/?query={keyword}"
            page2 = f"https://www.reuters.com/site-search/?query={keyword}&offset=20"
            pages.append(page1)
            pages.append(page2)

        all_linked_uuids = self.run_scraper(pages)

        # Copy the scraped articles into the topic folder:
        topic.carry_articles(all_linked_uuids)


    def run_scraper(self, pages_linking_to_articles):
        all_linked_uuids = []

        try:
            with sync_playwright() as p:
                launch_args = [
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                    #"--headless=new",
                    "--no-sandbox",
                ]
                browser = p.chromium.launch(
                    channel="chromium",
                    headless=False,
                    args=launch_args,
                )

                for sub_page in pages_linking_to_articles:
                    page1 = browser.new_page()
                    page1.goto(sub_page)
                    sleep(5)

                    elements = page1.locator('[data-testid="TitleLink"]')
                    elements.count()

                    for el in elements.all():

                        # ------------------------------ Search for article links --------------------------------

                        title = el.inner_text()
                        link = el.get_attribute("href")

                        if link is None: continue
                        if title is None: continue

                        if "https" not in link:
                            link = "https://www.reuters.com" + link

                        _uuid = uuid.uuid5(uuid.NAMESPACE_DNS, link)
                        all_linked_uuids.append(_uuid)

                        if self.check_if_scrap_already_exists(_uuid):
                            print("Already scraped:", _uuid, link)
                            continue

                        # -------------------------------------- Scrap article -----------------------------------------

                        print(link, title)

                        try:
                            author = ""
                            title =  link.split("/")[-2]

                            match_date = re.search(r'(\d{4}.\d{2}.\d{2})(?!.*\d{4}.\d{2}.\d{2})', title)
                            date_str = match_date.group(1)
                            ts_published = pd.Timestamp(datetime.strptime(date_str, "%Y-%m-%d"), tz=tz)

                            title =  title.replace("-", " ")

                            page2 = browser.new_page()
                            page2.goto(link)
                            sleep(5)

                            # --------------- Try article autor ---------------
                            _elements = page2.locator('[data-testid="AuthorCard"]').locator('p')
                            if _elements.count() > 0:
                                author = _elements.nth(0).inner_text()
                                #print(author)

                            # --------------- Try article publish date ---------------
                            _elements = page2.locator('[data-testid="DateLine"]')
                            if _elements.count() > 0:
                                ts_str = _elements.nth(0).get_attribute("datetime")
                                ts_published = pd.Timestamp(ts_str).tz_convert(tz)
                                #print(ts_published)

                            # --------------- Get article content ---------------
                            _article = page2.locator('[data-testid="ArticleBody"] *')
                            _article.count()

                            text = []
                            for el in _article.all():
                                ceck_attr = el.get_attribute("data-testid")
                                if ceck_attr is None:
                                    continue
                                if "paragraph" in ceck_attr:
                                    text.append(el.inner_text())
                            text = "\n".join(text)
                            #print(text)

                            # Directly save scraped content
                            _data = {
                                "uuid": str(_uuid),
                                "title": title,
                                "author": author,
                                "url": link,
                                "posted_url": link,
                                "is_linking_to_external_website": False,
                                "timestamp": pd.Timestamp(ts_published).tz_convert(tz=tz).isoformat(),
                                "source": self.url_main,
                                "crawled_at": pd.Timestamp.now(tz=tz).isoformat(),
                                "text": text,
                                }

                            self.save_scrap(_data)

                            page2.close()  # closes just this page/tab

                        except Exception as e:
                            print("Scraping failed:", link)

                browser.close()

        except Exception as e:
            print(traceback.format_exc())

        return all_linked_uuids


if __name__ == "__main__":
    Reuters().run_scraper()
    df = Reuters().generate_references()


