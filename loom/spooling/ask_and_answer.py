
from loom.spooling.source.references import load_references

from loom.spooling.source.universal_scraper import UniversalScraper
from loom.spooling.topics.universal_topic import UniversalTopic

from loom.spooling.llm.claude import ask_claude
import pandas as pd

tz = "Europe/Berlin"


def ask_and_answer(scraper: UniversalScraper, topic: UniversalTopic, ts_start_reviewing: pd.Timestamp, use_ai: bool=False):
    folder = scraper.get_folder()

    df = load_references(folder)
    df = df.sort_values("crawled_at", ascending=False)

    _df = df[df["timestamp"] > ts_start_reviewing]

    for ix, row in _df.iterrows():
        uuid = row["uuid"]
        ask_and_answer_for_uuid(scraper, topic, uuid, use_ai=use_ai)


def ask_and_answer_for_uuid(scraper: UniversalScraper, topic: UniversalTopic, uuid: str, use_ai: bool=False):
    topic_keywords = topic.get_topic_keywords()
    scrap = scraper.get_scrap(uuid)

    # First open scraped article
    url = scrap.get("url", "")
    article_title = scrap.get("title", "")
    article_content = scrap.get("text", "")

    is_already_answered = topic.check_if_topic_already_answered(uuid)

    n_words = scraper.count_words(article_content)
    n_words = max(1, n_words)
    n_keywords = scraper.count_keywords(article_content, topic_keywords)
    ratio = n_keywords / n_words

    check1 = n_words > 100
    check2 = ratio > 0.05  # This is quite tight
    #print(uuid, topic.get_topic(), ratio, is_already_answered, url)


    if check1 and check2:
        if not is_already_answered:
            print(uuid, topic.get_topic(), ratio, is_already_answered, url)

        if use_ai:
            if is_already_answered:
                return

            print(uuid, topic.get_topic(), ratio, article_title)
            print(f"{topic.get_topic()} - AI reviewing url: {url}")

            question = topic.get_topic_question(article_title, article_content)
            topic_answer = ask_claude(question, use_web_fetch=True)

            topic.save_topic_answer(uuid, topic_answer)

