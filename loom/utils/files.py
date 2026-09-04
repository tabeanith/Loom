import json
import os
from pathlib import Path


def find_scraped_article_filepath(uuid: str):
    path = Path(__file__).parent.parent.resolve() / "spooling" / "source"
    subdirectories = [item for item in os.listdir(path) if os.path.isdir(path)]

    for subdir in subdirectories:
        file_path = path / subdir / "scraps" / f"{uuid}.json"

        if file_path.is_file():
            return file_path

    return None


def find_scraped_article_content(uuid: str):
    file_path = find_scraped_article_filepath(uuid)

    if file_path is not None:
        with open(file_path, "r") as f:
            data = json.load(f)
            return data.get("text", "")

    return ""


def print_link(file_path: Path):
    print(f"file:///{file_path.__str__()}".replace('\\', '/'))
