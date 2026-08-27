import traceback

import numpy as np
import pandas as pd
import uuid
import os
import json
from pathlib import Path

from loom.spooling.source.universal_scraper import UniversalScraper
from loom.spooling.source.reddit.run_reddhog import run_reddhog
from loom.spooling.source.references import update_references


pd.set_option('display.max_rows', 10000)
pd.set_option('display.max_columns', 500)
pd.set_option('display.width', 10000)
pd.set_option('display.max_colwidth', None)

tz = "Europe/Berlin"


class Reddit(UniversalScraper):

    path_folder = Path(__file__).parent.resolve()

    url_main = "https://www.reddit.com/"

    def extract_subreddit(self, filepath: str):
        """Extract subreddit name from a Reddit URL."""
        return filepath.split("\\")[-2]


    def find_json_files(self, root_dir: Path):
        """Find all JSON files in root_dir and its subfolders."""
        json_files = []
        for dirpath, dirnames, filenames in os.walk(root_dir):
            for filename in filenames:
                if filename.lower().endswith(".json"):
                    json_files.append(os.path.join(dirpath, filename))
        return json_files


    def is_linking_to_external_website(self, posted_url: str) -> bool:
        check1 = posted_url.startswith("https://www.reddit.com")
        check2 = posted_url.startswith("https://i.redd.it")
        check3 = posted_url.startswith("https://v.redd.it")
        check4 = posted_url.startswith("/r/")
        is_inside_reddit = check1 or check2 or check3 or check4
        return not is_inside_reddit


    def run_scraper(self, _run_reddhog: bool=True):
        if _run_reddhog:
            run_reddhog()

        path = Path(__file__).resolve().parent / "data"

        store_all_subreddit = []

        results = self.find_json_files(path)  # change "." to your target directory
        print(f"Found {len(results)} JSON file(s):")
        for filepath in results:
            print(filepath)

            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

                for post in data:
                    _uuid = uuid.uuid5(uuid.NAMESPACE_DNS, post["posted_url"])

                    store_all_subreddit.append(
                        {
                            "uuid": str(_uuid),
                            "title": post["title"],
                            "author": post["author"],
                            "url": post["url"],
                            "subreddit": self.extract_subreddit(filepath),
                            "posted_url": post["posted_url"],
                            "is_linking_to_external_website": self.is_linking_to_external_website(post["posted_url"]),
                            "timestamp": post["timestamp"],
                            "source": self.url_main,
                            "crawled_at": post["crawled_at"],
                        }
                    )

            df = pd.DataFrame(store_all_subreddit)
            df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.tz_convert("Europe/Berlin")
            df["crawled_at"] = pd.to_datetime(df["crawled_at"]).dt.tz_convert("Europe/Berlin")
            df = df.sort_values("timestamp", ascending=False)

        update_references("reddit", df)


if __name__ == "__main__":
    Reddit().run_scraper(_run_reddhog=True)

