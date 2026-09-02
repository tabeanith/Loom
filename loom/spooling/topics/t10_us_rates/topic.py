import traceback

import numpy as np
import pandas as pd
from pathlib import Path
import os
import json
import re

from loom.spooling.topics.universal_topic import UniversalTopic
from loom.spooling.source.universal_scraper import find_scraped_article_content

from loom.spooling.topics.extraction import extract_q, roll_qs_to_months
from loom.spooling.topics.extraction import extract_answer_int
from loom.spooling.topics.extraction import extract_answer_multiple_floats
from loom.spooling.topics.extraction import extract_answer_yes_no



class T10_US_Rates(UniversalTopic):

    path_folder = Path(__file__).parent.resolve()

    def get_content_keywords(self):
        return [
            "fomc",
            "fed",
            "fed chair",
            "federal reserve",
            "bank",
            "us",
            "rate",
            "hike",
            "inflation",
            "hawk",
            "hawkish",
            "dove",
            "dovish",
            "rates",
            "pressure",
            "dampening",
            "damp",
            "economic",
            "economy",
            "equities",
            "equity",
            "asset",
            "stock",
            "interest",
            "fiscal",
            "fixed income",
            "powell",
            "warsh",
            "treasury",
            "bond",
            "yield",
            "guide",
            "guidance",
            "speech",
            "policy",
            "forward",
            "stability",
            "performance",
            "expect",
            "trend",
            "consumer",
            "borrow",
            "odds",
            "growth",
            "hot",
            "cold",
            "fear",
            "central bank",
            "crisis",
            "america",
            "us",
            "chairman",
            "rising",
            "falling",
            "rise",
            "fall",
            "capital",
            "insurance",
            "recession",
            "signal",
            "buyback",
        ]

    def get_llm_system(self):
        return "Your are an analyst working for a hedge fund trading US markets. You are assisting traders to trade Index Futures (NQ, ES, QQQ, SPY). Your analysis is sharp, mindful, succinct. Provide concise, focused responses. When you are evaluating risks: Put focus on forward-looking information, not historical/past. When formatting your answer, stay true to the input message, do not insert tabular formatting."

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

                Q01. Is the content relevant to US economy, US yields, US interest rates and US market pricing?
                Relevance: x (x [YES, NO, IMPLICIT])
                
                Q02. Is the content about increasing US interest rates? On the shorter term (next 1-2 years)? On the longer term (10 years)?
                Increasing rates magnitude: y (y [percentage value])
                Increasing rates shortterm: x (x [YES, NO])
                Increasing rates longterm: x (x [YES, NO])
                
                Q03. Is the US rate increase already expected/confirmed or very new/uncertain information?
                Expectancy score: y (y on a scale of 0 [already known and expected] to 100 [very unexpected/uncertain])

                Q04. Is the content about decreasing US interest rates? On the shorter term (next 1-2 years)? On the longer term (10 years)?
                Decreasing rates magnitude: y (y [percentage value])
                Decreasing rates shortterm: x (x [YES, NO])
                Decreasing rates longterm: x (x [YES, NO])
                
                Q05. Is the US rate decrease already expected/confirmed or very new/uncertain information?
                Expectancy score: y (y on a scale of 0 [already known and expected] to 100 [very unexpected/uncertain])
                
                Q06. Is the content explicitly about bullish impact on the US stock markets?
                Explicit: x (x [YES, NO])
                Impact score: y (y on a scale of 0 [no impact] to 100 [very bullish])
                
                Q07. Is the content explicitly about bearish impact on the US stock markets?
                Explicit: x (x [YES, NO])
                Impact score: y (y on a scale of 0 [no impact] to 100 [very bearish])
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

                relevance_to_us = extract_answer_yes_no(parts[1], "relevance")

                inc_magnitude = extract_answer_multiple_floats(parts[2], "increasing rates magnitude")
                inc_st = extract_answer_yes_no(parts[2], "increasing rates short")
                inc_lt = extract_answer_yes_no(parts[2], "increasing rates long")
                inc_expectancy = extract_answer_int(parts[3], "expectancy")

                dec_magnitude = extract_answer_multiple_floats(parts[4], "decreasing rates magnitude")
                dec_st = extract_answer_yes_no(parts[4], "decreasing rates short")
                dec_lt = extract_answer_yes_no(parts[4], "decreasing rates long")
                dec_expectancy = extract_answer_int(parts[5], "expectancy") if not np.nan else 0

                bull_impact = extract_answer_yes_no(parts[6], "explicit")
                bull_score = extract_answer_int(parts[6], "impact")

                bear_impact = extract_answer_yes_no(parts[7], "explicit")
                bear_score = extract_answer_int(parts[7], "impact")


                inc_score = (inc_st + inc_lt) * inc_expectancy * -1  # Increasing Rates means bearish market
                dec_score = (dec_st + dec_lt) * dec_expectancy
                market_score = bull_impact * bull_score - bear_impact * bear_score

                inc_score = 0 if np.isnan(inc_score) else inc_score
                dec_score = 0 if np.isnan(dec_score) else dec_score
                market_score = 0 if np.isnan(market_score) else market_score

                score = (inc_score + dec_score + market_score) * 0.5

                # If article is not relevant to US, cancel the score
                if np.isnan(relevance_to_us) or (relevance_to_us < 1):
                    score = np.nan

                results.append({
                    "timestamp": timestamp,
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



