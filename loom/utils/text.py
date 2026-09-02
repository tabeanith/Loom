import pandas as pd
import json
import os
from pathlib import Path


tz = "Europe/Berlin"


def count_keywords(content: str, list_of_keywords: list):
    if content is None: return 0
    count = sum(content.count(key) for key in list_of_keywords)
    return count


def count_words(content: str):
    if content is None: return 0
    if content == "": return 0
    count = len(content.split())
    return count

