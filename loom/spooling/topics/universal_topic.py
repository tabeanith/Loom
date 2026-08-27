from pathlib import Path
import json
import os


class UniversalTopic():

    path_folder: Path = None

    def get_topic(self):
        return self.path_folder.name

    def get_topic_keywords(self):
        raise NotImplementedError()

    def get_topic_question(self, article_title: str, article_content: str):
        raise NotImplementedError()

    def calculate_scores(self, df):
        raise NotImplementedError()

    def save_topic_answer(self, uuid: str, topic_answer: str):
        file_path = self.path_folder / "answers" / f"{uuid}.json"

        data = {
            "text": topic_answer,
        }

        with open(file_path, "w") as f:
            json.dump(data, f)


    def load_topic_answer(self, uuid: str):
        file_path = self.path_folder / "answers" / f"{uuid}.json"

        if self.check_if_topic_already_answered(uuid):
            with open(file_path, "r") as f:
                data = json.load(f)
                text = data.get("text", "")
                return text
        else:
            return ""


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


