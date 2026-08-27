import traceback

import numpy as np
import pandas as pd
from pathlib import Path
import os
import json
import re

from loom.spooling.topics.universal_topic import UniversalTopic
from loom.spooling.topics.extraction import extract_q, roll_qs_to_months
from loom.spooling.source.universal_scraper import find_scraped_article_content


class T01_Weather(UniversalTopic):

    path_folder = Path(__file__).parent.resolve()

    def get_topic_keywords(self):
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

    def get_topic_question(self, article_title: str, article_content: str):
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
                T1. Historical observation [YES/NO]
                T2. Forward-looking immediate [YES/NO]
                T3. Longterm developement [YES/NO]
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

            text = self.load_topic_answer(uuid)
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
                parts = re.split(r'([Q]\d{2})', text)
                n_quests = len(parts) - 1

                intro = parts[0]

                # TODO: intro
                data = {}

                for i in np.arange(0, int(n_quests / 2)):
                    q_code = parts[1 + i*2]
                    q_text = parts[2 + i*2]
                    #print(q_code)
                    #print(q_text)

                    q_data = extract_q(q_code, q_text)

                    data = {**data, **q_data}

                # Weatherscore total:
                risk = data["Q05_r"] * data["Q05_q"] - data["Q06_r"] * data["Q06_q"]
                time = 1. + data["Q04_r"] * data["Q04_q"] / 100.
                europe = data["Q07_q"] / 100.

                if europe < 0.5: continue

                q1 = data["Q01_r"] * data["Q01_q1"] + \
                     data["Q02_r"] * data["Q02_q1"] + \
                     data["Q03_r"] * data["Q03_q1"] * -1.

                q2 = data["Q01_r"] * data["Q01_q2"] + \
                     data["Q02_r"] * data["Q02_q2"] + \
                     data["Q03_r"] * data["Q03_q2"] * -1.

                q3 = data["Q01_r"] * data["Q01_q3"] + \
                     data["Q02_r"] * data["Q02_q3"] + \
                     data["Q03_r"] * data["Q03_q3"] * -1.

                q4 = data["Q01_r"] * data["Q01_q4"] + \
                     data["Q02_r"] * data["Q02_q4"] + \
                     data["Q03_r"] * data["Q03_q4"] * -1.

                q1 = q1 + risk * 0.5
                q2 = q2 + risk * 0.5
                q3 = q3 + risk * 0.5
                q4 = q4 + risk * 0.5

                q1 = q1 * europe
                q2 = q2 * europe
                q3 = q3 * europe
                q4 = q4 * europe

                #print("q1, q2, q3, q4", q1, q2, q3, q4)
                result = roll_qs_to_months(timestamp, q1, q2, q3, q4, time)
                #print(result)

                result.name = timestamp

                results.append(result)
                results_meta.append({
                    "timestamp": timestamp,
                    "topic": self.get_name(),
                    "title": title,
                    "uuid": uuid,
                    "url": url,
                })

            except Exception as e:
                #print(traceback.format_exc())
                print("Parsing error with uuid:", uuid, url)
                pass

        df_results = pd.concat(results, axis=1).T
        df_results_meta = pd.DataFrame(results_meta)
        df_results_meta.index = df_results_meta["timestamp"]

        df_full = df_results.merge(df_results_meta, left_index=True, right_index=True)

        return df_full
