import json
import pandas as pd
import numpy as np
import anthropic
from dotenv import load_dotenv
import os

pd.set_option('display.max_rows', 10000)
pd.set_option('display.max_columns', 500)
pd.set_option('display.width', 10000)
pd.set_option('display.max_colwidth', None)


tz = "Europe/Berlin"


role = "user"


load_dotenv()

api_key = os.environ.get('ANTHROPIC_API_KEY')
client = anthropic.Anthropic(api_key=api_key)


def ask_claude(system, content, use_web_fetch: bool=False):
    # Initialize the client with your API key
    # Get a key at https://aistudio.google.com/apikey

    if use_web_fetch:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1536,
            system = system,
            messages=[
                {"role": role,
                 "content": content}
            ],
            tools=[{"type": "web_fetch_20250910", "name": "web_fetch", "max_uses": 3}],  # Enables web search for articles
        )
    else:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1536,
            system=system,
            messages=[
                {"role": role,
                 "content": content}
            ],
        )

    # It should be just on1 text block
    for block in response.content:
        if block.type == "text":
            result = block.text

    return result

