import traceback

import numpy as np
import pandas as pd
from pathlib import Path
import os
import json
import re

from loom.spooling.topics.universal_topic import UniversalTopic
from loom.spooling.topics.extraction import roll_qs_to_months
from loom.spooling.topics.extraction import extract_answer_yes_no
from loom.spooling.topics.extraction import extract_answer_int
from loom.spooling.topics.extraction import extract_answer_int_four_season
from loom.spooling.source.universal_scraper import find_scraped_article_content

from loom.spooling.llm.ask_and_answer import ask_and_answer_for_uuid


class T02_Weather(UniversalTopic):

    path_folder = Path(__file__).parent.resolve()

    def get_content_keywords(self):
        return [
            "warm",
            "wet",
            "windy",
            "cool",
            "hot",
            "cold",
            "freeze",
            "temperature",
            "climate",
            "wind",
            "solar",
            "pv",
            "dry",
            "drought",
            "water",
            "hydro",
            "heat",
            "summer",
            "winter",
            "spring",
            "autumn",
            "pour",
            "rain",
            "glacier",
            "spell",
            "wildfire",
            "storm",
            "bake",
            "smoke",
            "sand",
            "rivers",
            "levels",
            "rhine",
            "danube",
            "cloud",
            "pressure",
            "atmosphere",
            "snow",
            "blizzard",
            "grey",
            "polar",
            "vortex",
            "split",
            "instable",
            "stable",
            "oscillation",
            "scorch",
            "crisis",
            "prognos",
            "scarcity",
            "flood",
            "irradian",
            "run-of-river",
            "alps",
            "forecast",
            "climate",
            "celcius",
            "kelvin",
            "fahrenheit",
            "wave",
            "met",
            "el ni",  # El Nino
            "la ni",  # La Nina
            "precip",
            "precipitation",
            "fog",
            "foggy",
            "sunny",
            "wassertiefe",
            "pegel",
            "kaub",
            "wasser",
            "waldbrand",
            "descruction",
            "oceans",
            "weather",
            "wetter",
            "klima",
            "krise",
            "eco",
            "öko",
            "green",
            "grün",
        ]

    def get_llm_system(self):
        return "Your are an analyst working for a commodities trading hedge fund in Europe. You are assisting traders to trade German Power Base Futures. Your analysis is sharp, mindful, succinct. Provide concise, focused responses. When you are evaluating risks: Put focus on forward-looking information, not historical/past. When formatting your answer, stay true to the input message, do not insert tabular formatting."

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
        
            Q01. Is the content relevant to extreme summers/heat/dryness, specifically in a spring/summer/autumn context? How severe is the issue?
            Relevance: x (x [YES, NO, IMPLICIT])
            Severity score: Spring y, Summer y, Fall y, Winter y (y on a scale of 0: very neutral to 100: extreme heat, dryness, crisis, death)
    
            Q02. Is the content relevant to extreme winters, cold/spells/heating demand, specifically in winter context? How severe is the issue?
            Relevance: x (x [YES, NO, IMPLICIT])
            Severity score: Spring y, Summer y, Fall y, Winter y (y on a scale of 0: very neutral to 100: extreme cold, freezing, dark)
            
            Q03. Is the content relevant to moderate weather: mild temperatures/wet/windy/sunny? How severe is the issue?
            Relevance: x (x [YES, NO, IMPLICIT])
            Severity score: Spring y, Summer y, Fall y, Winter y (y on a scale of 0: very neutral to 100: cool or normal warm, very wet, very windy)
        
            Q04. Is the content relevant to weather patterns and their probability for staying/increasing critical weather risks? How severe is the risk?
            Relevance: x (x [YES, NO, IMPLICIT])
            Severity score: Y (Y on a scale of 0: very short-lives pattern, little risk to 100: critical and persistent patterns and risks)
        
            Q05. Is the content implying risks for increasing energy demand or decreasing energy supply? 
            Relevance: x (x [YES, NO, IMPLICIT])
            Severity score: Y (Y on a scale of 0: no risk 100: very high demand, very low supply, extreme high risks)
                
            Q06. Is the content implying risks for decreasing energy demand? 
            Relevance: x (x [YES, NO, IMPLICIT])
            Severity score: Y (Y on a scale of 0: no risk 100: much lower demand, strong decline due to economics/destruction/weather)
                        
            Q07. Is the content describing effects very directly impacting Europe and/or European energy markets? 
            Relevance: ---
            Severity score: Y (Y on a scale of 0: no relationship at all 100: very directly, immediate impacts)
            """
        return message

    def calculate_scores(self, df):
        results = []
        results_meta = []

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

            url_scraped_content = find_scraped_article_content(uuid)


            print(url)
            #print(text)

            try:
                text = text.replace("**", "")
                parts = re.split(r'(?=[Q]\d{2})', text)

                # TODO: intro
                intro = parts[0]

                Q01_r = extract_answer_yes_no(parts[1], "relevance")
                Q01_q1, Q01_q2, Q01_q3, Q01_q4 = extract_answer_int_four_season(parts[1], "severity")

                Q02_r = extract_answer_yes_no(parts[2], "relevance")
                Q02_q1, Q02_q2, Q02_q3, Q02_q4 = extract_answer_int_four_season(parts[2], "severity")

                Q03_r = extract_answer_yes_no(parts[3], "relevance")
                Q03_q1, Q03_q2, Q03_q3, Q03_q4 = extract_answer_int_four_season(parts[3], "severity")

                Q04_r = extract_answer_yes_no(parts[4], "relevance")
                Q04_s = extract_answer_int(parts[4], "severity")

                Q05_r = extract_answer_yes_no(parts[5], "relevance")
                Q05_s = extract_answer_int(parts[5], "severity")

                Q06_r = extract_answer_yes_no(parts[6], "relevance")
                Q06_s = extract_answer_int(parts[6], "severity")

                relevance = extract_answer_int(parts[7], "severity") / 100.
                relevance = 0 if np.isnan(relevance) else relevance
                if relevance > 0.5: relevance = 1
                elif relevance > 0.25: relevance = 0.25
                else: relevance = 0.0

                # Risk factor:
                risk = (Q05_r * Q05_s - Q06_r * Q06_s) / (Q05_r + Q06_r)
                time = 1. + Q04_r * Q04_s / 100.

                if relevance < 0.1: continue

                q1 = (Q01_r * Q01_q1 + Q02_r * Q02_q1 - Q03_r * Q03_q1) / (Q01_r + Q02_r + Q03_r)
                q2 = (Q01_r * Q01_q2 + Q02_r * Q02_q2 - Q03_r * Q03_q2) / (Q01_r + Q02_r + Q03_r)
                q3 = (Q01_r * Q01_q3 + Q02_r * Q02_q3 - Q03_r * Q03_q3) / (Q01_r + Q02_r + Q03_r)
                q4 = (Q01_r * Q01_q4 + Q02_r * Q02_q4 - Q03_r * Q03_q4) / (Q01_r + Q02_r + Q03_r)

                q1 = q1 * (1 + risk/100.)
                q2 = q2 * (1 + risk/100.)
                q3 = q3 * (1 + risk/100.)
                q4 = q4 * (1 + risk/100.)

                if np.isnan(q1):
                    pass
                    #print(q1)

                #print("q1, q2, q3, q4", q1, q2, q3, q4)
                result = roll_qs_to_months(timestamp, q1, q2, q3, q4, 1)
                #print(result)

                result.name = timestamp

                results.append(result)
                results_meta.append({
                    "relevance": relevance,
                    "timestamp": timestamp,
                    "topic": self.get_name(),
                    "title": title,
                    "uuid": uuid,
                    "url": url,
                })

            except Exception as e:
                #print(traceback.format_exc())
                print("Parsing error with uuid:", uuid, url)
                if False:
                    ask_and_answer_for_uuid(self, uuid, use_ai=True, save_answer=True)

        df_results = pd.concat(results, axis=1).T
        df_results_meta = pd.DataFrame(results_meta)
        df_results_meta.index = df_results_meta["timestamp"]

        df_full = df_results.merge(df_results_meta, left_index=True, right_index=True)

        return df_full
