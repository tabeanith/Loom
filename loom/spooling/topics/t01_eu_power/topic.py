import traceback

import numpy as np
import pandas as pd
from pathlib import Path
import os
import json
import re

from loom.spooling.topics.universal_topic import UniversalTopic
from loom.utils.files import find_scraped_article_content

from loom.spooling.topics.extraction import extract_q, roll_qs_to_months
from loom.spooling.topics.extraction import extract_answer_int
from loom.spooling.topics.extraction import extract_answer_multiple_floats
from loom.spooling.topics.extraction import extract_answer_yes_no



class T01_EU_Power(UniversalTopic):

    path_folder = Path(__file__).parent.resolve()

    def get_content_keywords(self):
        return [
            "europe",
            "eu",
            "germany",
            "france",
            "power",
            "energy",
            "plant",
            "renewable",
            "solar",
            "pv",
            "park",
            "wind",
            "reserve",
            "lignite",
            "battery",
            "batteries",
            "security",
            "mwh",
            "capacity",
            "merit",
            "merit order",
            "avail",
            "availability",
            "umm",
            "urgent",
            "commodity",
            "commodities",
            "emission",
            "eua",
            "cea",
            "ets",
            "certificates",
            "fuel",
            "gas",
            "oil",
            "gasoline",
            "crude",
            "diesel",
            "refine",
            "stock",
            "ttf",
            "henry",
            "lng",
            "storage",
            "reserve",
            "logistic",
            "ship",
            "congestion",
            "refining",
            "flow",
            "leak",
            "pipeline",
            "pip",
            "flare",
            "demand",
            "heating",
            "cooling",
            "energy",
            "power",
            "russia",
            "russland",
            "supply",
            "level",
            "storing",
            "deliver",
            "crisis",
            "shock",
            "fire",
            "explosion",
            "route",
            "strait",
            "street",
            "stream",
            "seaborne",
            "block",
            "tank",
            "tanker",
            "strike",
            "accident",
            "tightness",
            "imports",
            "dependen",
            "middle east",
            "east",
            "asia",
            "china",
            "greenland",
            "ressource",
            "conflict",
            "choke",
            "cargo",
            "freight",
            "vessel",
            "squeeze",
            "transit",
            "waterway",
            "control",
            "port",
            "shipping",
            "logistic",
            "insurance",
            "spillover",
            "war",
            "fuel",
            "energy",
            "fossil",
            "petrol",
            "trump",
            "netanjahu",
            "netanyahu",
            "putin",
            "panama",
            "hormuz",
            "hormus",
            "iran",
            "peace",
            "ceasefire",
            "negotiation",
            "strike",
            "rais",
            "tension",
            "tariff",
            "sanction",
            "blockade",
            "import",
            "export",
        ]

    def get_llm_system(self):
        return "Your are an analyst working for a hedge fund trading commodities in Europe. You are assisting traders to trade German Power Futures and Gas TTF Futures. Your analysis is sharp, mindful, succinct. Provide concise, focused responses. When you are evaluating risks: Put focus on forward-looking information, not historical/past. When formatting your answer, stay true to the input message, do not insert tabular formatting."

    def get_llm_question(self, article_title: str, article_content: str):
        message = f"""
                Parse and analyse this article:
                --- article starts here ---
                {article_title}
                {article_content}
                --- article ends here --- 

                Answer the following questions & follow exactly this format:

                Published online:
                    x date
                Geographic focus:
                    x [x is continent, country, area] 
                Temporal focus:
                    T1. Historical report [YES/NO]
                    T2. Forward-looking reporting short-term risks (next few weeks/months) [YES/NO]
                    T3. Forward-looking reporting long-term risks (next quarters/years) [YES/NO]
                Synopsis:
                    [Write a concise content summary]

                Q01.Is the content's main message about EU energy, EU commodities, German power market prices, German energy economics?
                Relevance: x (x [YES, NO])
                
                Q02. Is the content confirming already known information or reporting very new/uncertain risks?
                Risk score: y (y on a scale of 0 [already known and expected] to 100 [very unexpected/uncertain])

                Q03. Is the content explicit about bullish impact on the German power futures market?
                Explicit: x (x [YES, NO])
                Impact score: y (y on a scale of 0 [no impact] to 100 [extreme bullish])
                
                Q04. Is the content explicit about bearish impact on the German power futures market?
                Explicit: x (x [YES, NO])
                Impact score: y (y on a scale of 0 [no impact] to 100 [extreme bearish])
                """

        return message


    def calculate_scores(self, df):
        results = []

        for uuid in df["uuid"].values:

            text = self.load_llm_answer(uuid)
            if text == "": continue

            row = df[df["uuid"] == uuid].iloc[0]
            url = row["posted_url"]
            title = row["title"]
            uuid = row["uuid"]
            timestamp = row["timestamp"]

            if pd.isnull(timestamp):
                print(uuid, "No article timestamp, will drop datapoint")
                continue


            scraped_content = find_scraped_article_content(uuid)
            print(url)


            try:
                text = text.replace("**", "")
                parts = re.split(r'(?=[Q]\d{2})', text)

                # TODO: intro
                intro = parts[0]

                relevance = extract_answer_yes_no(parts[1], "relevance")

                risk_score = extract_answer_int(parts[2], "risk")

                bull_impact = extract_answer_yes_no(parts[3], "explicit")
                bull_score = extract_answer_int(parts[3], "impact")
                bear_impact = extract_answer_yes_no(parts[4], "explicit")
                bear_score = extract_answer_int(parts[4], "impact")

                risk_score = 0 if np.isnan(risk_score) else risk_score
                _bull_impact = 0 if np.isnan(bull_impact) else bull_impact
                bull_score = 0 if np.isnan(bull_score) else bull_score
                _bear_impact = 0 if np.isnan(bear_impact) else bear_impact
                bear_score = 0 if np.isnan(bear_score) else bear_score

                score_market = (1 + _bull_impact) * bull_score - (1 + _bear_impact) * bear_score
                score = score_market * (1 + risk_score/100.)

                results.append({
                    "timestamp": timestamp,
                    "relevance": relevance,
                    "risk": risk_score,
                    "score_market": score_market,
                    "score": score,
                    "topic": self.get_name(),
                    "title": title,
                    "uuid": uuid,
                    "url": url,
                })

            except Exception as e:
                #print(traceback.format_exc())
                print("Parsing error with uuid:", uuid, url)
                pass

        df_results = pd.DataFrame(results)
        df_results.index = df_results["timestamp"]
        return df_results



