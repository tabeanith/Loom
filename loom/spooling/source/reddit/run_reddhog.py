import os
import subprocess
from pathlib import Path


listed_subreddits = [
        "climate",
        "climatechange",
        "weather",
        "meteorology",
        "ukweather",
        "rivercruises",
        "skiing",
        "umwelt_de",
        "futurology",
        "europe",
        "de",
        "newsd",
        "austria",
        "france",
        "switzerland",
        "askswitzerland",
        "worldnews",
        "politics",
        "oil",
        "news",
        "economics",
        "energy",
        "geopolitics",
        "usnews",
        "wallstreetwhales",
        ]


def run_reddhog():
        query_limit_new_posts = 100

        str_subreddits = ','.join(map(str, listed_subreddits))

        subprocess.run(
        f'reddhog subreddit {str_subreddits} {str(query_limit_new_posts)}',
                cwd=Path(__file__).parent.resolve(),
                shell=True,
        )


if __name__ == "__main__":
    run_reddhog()



