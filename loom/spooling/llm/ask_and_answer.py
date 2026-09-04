import pandas as pd
import json
import os
from pathlib import Path


from loom.spooling.source.references import load_references

from loom.spooling.source.universal_scraper import UniversalScraper
from loom.spooling.topics.universal_topic import UniversalTopic

from loom.spooling.llm.claude import ask_claude

from loom.utils.analyse_strings import count_words, count_keywords

tz = "Europe/Berlin"



# Look in all possible files
def get_scrap(uuid: str):
    search_path = Path(__file__).parent.parent.resolve() / "source"
    list_subfolders = [f.name for f in os.scandir(search_path) if f.is_dir()]

    for subfolder in list_subfolders:
        search_file = search_path / subfolder / "scraps" / f"{uuid}.json"
        if search_file.is_file():
            with open(search_file, "r") as f:
                data = json.load(f)
                return data
    return {}


def TBD_ask_and_save_answer(scraper: UniversalScraper, topic: UniversalTopic, ts_start_reviewing: pd.Timestamp, use_ai: bool=False):
    folder = scraper.get_folder()

    df = load_references(folder)
    df = df.sort_values("crawled_at", ascending=False)

    _df = df[df["timestamp"] > ts_start_reviewing]

    for ix, row in _df.iterrows():
        uuid = row["uuid"]
        answer = ask_and_answer_for_uuid(topic, uuid, use_ai=use_ai)
        topic.save_llm_answer(uuid, answer)


def ask_and_save_answer(topic: UniversalTopic, ts_start_reviewing: pd.Timestamp, use_ai: bool=False, ignore_existing_answer: bool=False):
    df = topic.generate_references()
    df = df.sort_values("crawled_at", ascending=False)

    _df = df[df["timestamp"] > ts_start_reviewing]

    for ix, row in _df.iterrows():
        uuid = row["uuid"]
        answer = ask_and_answer_for_uuid(topic, uuid, use_ai=use_ai, ignore_existing_answer=ignore_existing_answer)
        topic.save_llm_answer(uuid, answer)


def ask_and_answer_for_uuid(topic: UniversalTopic, uuid: str, use_ai: bool=False, ignore_existing_answer: bool=False):
    topic_keywords = topic.get_content_keywords()
    scrap = get_scrap(uuid)

    # First open scraped article
    url = scrap.get("url", "")
    article_title = scrap.get("title", "")
    article_timestamp = scrap.get("timestamp", "")
    article_content = scrap.get("text", "")

    is_already_answered = topic.check_if_topic_already_answered(uuid)

    n_words = count_words(article_content)
    n_words = max(1, n_words)
    n_keywords = count_keywords(article_content, topic_keywords)
    ratio = n_keywords / n_words

    check1 = n_words > 100
    check2 = ratio > 0.05  # Weed out some less relevant articles, dont evaluate every noise

    #print(uuid, topic.get_topic(), ratio, is_already_answered, url)
    inquire = False

    if check1 and check2:
        if use_ai:
            if ignore_existing_answer:
                inquire = True
            elif is_already_answered:
                inquire = False
            else:
                inquire = True

            if inquire:
                print(f"{uuid} | {topic.get_name()} | {article_timestamp} | {ratio} | {article_title} | {url}")

                llm_system = topic.get_llm_system()
                llm_question = topic.get_llm_question(article_title, article_content)

                topic_answer = ask_claude(llm_system, llm_question, use_web_fetch=True)
                return topic_answer

    return None

