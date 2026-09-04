import pandas as pd
from pathlib import Path
import os
import json

from loom.spooling.source.references import load_references
from loom.spooling.source.references import save_references

from loom.utils.analyse_strings import count_words

pd.set_option('display.max_rows', 10000)
pd.set_option('display.max_columns', 500)
pd.set_option('display.width', 10000)
pd.set_option('display.max_colwidth', None)

tz = "Europe/Berlin"


class UniversalScraper(object):

    path_folder: Path = None
    url_main = ""

    def get_folder(self):
        return self.path_folder.name


    def save_html(self, page):
        full_html = page.content()
        with open('./saving.html', "w+", encoding="utf-8") as f:
            f.write(full_html)

    def save_scrap(self, data):
        uuid = data["uuid"]
        url = data["url"]

        file_path = self.path_folder / "scraps" / f"{uuid}.json"

        with open(file_path, "w") as f:
            json.dump(data, f)

        print(f"New scrap {url} to {file_path}")


    def check_if_scrap_already_exists(self, uuid: str):
        file_path = self.path_folder / "scraps" / f"{uuid}.json"
        return file_path.is_file()


    def generate_references(self):
        path_existing_scrapes = self.path_folder / "scraps"
        all_data = []

        for dirpath, dirnames, filenames in os.walk(path_existing_scrapes):

            for filename in filenames:
                found_file_path = Path(dirpath) / filename

                with open(found_file_path, "r") as f:
                    data = json.load(f)
                    data.pop("text")
                    all_data.append(data)

        df = pd.DataFrame(all_data)

        save_references(df, self.path_folder.name)
        #update_references(self.path_folder.name, df)


    def run_scraper(self):
        pass


    def get_scraped_article_content(self, uuid: str):
        data = self.get_scrap(uuid)
        return data.get("text", "")


    def get_scrap(self, uuid: str):
        file_path = self.path_folder / "scraps" / f"{uuid}.json"

        if self.check_if_scrap_already_exists(uuid):
            with open(file_path, "r") as f:
                data = json.load(f)
                return data

        return {}


    def sanity_check_references(self):
        df = load_references(self.path_folder)

        # Check for uuid duplicates
        found_duplicates = (df.groupby("uuid").count() > 1).iloc[:, 0].any()
        if found_duplicates: print(f"{self.path_folder}: Found duplicate uuids")

        for _, row in df.iterrows():
            uuid = row["uuid"]
            url = str(row["url"])
            title = str(row["title"])
            timestamp = row["timestamp"]
            text = self.get_scraped_article_content(uuid)

            check1 = count_words(text) < 10
            check2 = len(title.replace(" ", "")) < 10
            check3 = pd.isnull(timestamp)
            check4 = len(url) < 10

            if check1 or check2 or check3:
                if check1: print(f"{self.path_folder} | {uuid} | scraped content empty | {url}")
                if check2: print(f"{self.path_folder} | {uuid} | article title empty | {url}")
                if check3: print(f"{self.path_folder} | {uuid} | published timestamp broken | {url}")
                if check4: print(f"{self.path_folder} | {uuid} | url broken | {url}")

            """
                if check3:
                    try:
                        file_path = self.path_folder / "scraps" / f"{uuid}.json"
                        os.remove(file_path)
                    except Exception as e:
                        pass
            """


