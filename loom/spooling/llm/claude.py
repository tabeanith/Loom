import json
import pandas as pd
import numpy as np
import anthropic

pd.set_option('display.max_rows', 10000)
pd.set_option('display.max_columns', 500)
pd.set_option('display.width', 10000)
pd.set_option('display.max_colwidth', None)


tz = "Europe/Berlin"


# TODO: Make this role configurable
system = "Your are an analyst working for a commodities trading hedge fund in Europe. You are assisting traders to trade German Power Base Futures. Your analysis is sharp, mindful, succinct. Provide concise, focused responses. When you are evaluating risks: Put focus on forward-looking information, not historical/past."
role = "user"


api_key = "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"
client = anthropic.Anthropic(api_key=api_key)


def ask_claude(content, use_web_fetch: bool=False):
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

