from pathlib import Path
import json
import os
import shutil
from loom.utils.files import find_scraped_article_filepath
import pandas as pd

tz = "Europe/Berlin"


class UniversalTopic():

    path_folder: Path = None

    def get_name(self):
        return self.path_folder.name

    def get_content_keywords(self):
        raise NotImplementedError()

    def get_llm_system(self):
        raise NotImplementedError()

    def get_llm_question(self, article_title: str, article_content: str):
        raise NotImplementedError()

    def calculate_scores(self, df):
        raise NotImplementedError()

    def save_llm_answer(self, uuid: str, topic_answer: str):
        if topic_answer is None: return

        file_path = self.path_folder / "answers" / f"{uuid}.json"

        data = {
            "text": topic_answer,
        }

        with open(file_path, "w") as f:
            json.dump(data, f)


    def load_llm_answer(self, uuid: str):
        file_path = self.path_folder / "answers" / f"{uuid}.json"

        if self.check_if_topic_already_answered(uuid):
            with open(file_path, "r") as f:
                data = json.load(f)
                text = data.get("text", "")
                return text
        else:
            return ""


    def carry_articles(self, list_of_uuids):
        for uuid in list_of_uuids:
            file_path_dest = self.path_folder / "articles" / f"{uuid}.json"
            file_path_orig = find_scraped_article_filepath(uuid)

            if file_path_orig is not None:
                try:
                    shutil.copy(file_path_orig, file_path_dest)
                except:
                    print("Failed to copy:", uuid)


    def check_if_topic_already_answered(self, uuid: str):
        file_path = self.path_folder / "answers" / f"{uuid}.json"
        return file_path.is_file()


    def get_all_topic_answers(self):
        search_path = self.path_folder / "answers"

        all_topic_answers = {}

        for dirpath, dirnames, filenames in os.walk(search_path):
            for filename in filenames:
                with open(search_path / filename, "r") as f:
                    data = json.load(f)
                    text = data.get("text", "")
                    uuid = filename.split(".")[0]
                    all_topic_answers[uuid] = text

        return all_topic_answers


    def generate_references(self):
        path_existing_scrapes = self.path_folder / "articles"
        all_data = []

        for dirpath, dirnames, filenames in os.walk(path_existing_scrapes):

            for filename in filenames:
                found_file_path = Path(dirpath) / filename

                with open(found_file_path, "r") as f:
                    data = json.load(f)
                    data.pop("text")
                    all_data.append(data)

        df = pd.DataFrame(all_data)
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce").dt.tz_convert(tz)
        df = df.sort_values("timestamp", ascending=False)

        return df
