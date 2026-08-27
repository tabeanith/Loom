from pathlib import Path
import pandas as pd
import os
import json


tz = "Europe/Berlin"

def load_references(folder: str):
    path = Path(__file__).parent.resolve()
    path_file = path / folder / "references.csv"

    if path_file.exists():
        df = pd.read_csv(path_file, sep=";")
        df["crawled_at"] = pd.to_datetime(df["crawled_at"], utc=True, errors='coerce').dt.tz_convert(tz)
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors='coerce').dt.tz_convert(tz)
        df = df.sort_values("timestamp", ascending=False)
        return df
    else:
        return pd.DataFrame()


def save_references(df, folder: str):
    # TODO: CAREFUL
    #   Do not destroy or overwrite/cutdown these files
    path = Path(__file__).parent.resolve()
    path_file = path / folder / "references.csv"

    df.to_csv(path_file, sep=";", index=True)
    print(f"Saved references: {path_file}")


def remove_duplicate_references(df):
    df["crawled_at"] = pd.to_datetime(df["crawled_at"], utc=True, errors='coerce').dt.tz_convert(tz)
    df = df.sort_values(by=["crawled_at"], ascending=True)
    df = df.groupby(["uuid"]).first()
    return df


def update_references(folder: str, df_new):
    if df_new.empty: return

    df_old = load_references(folder)
    df_new = df_new.drop(columns=['text'], errors='ignore')

    df = pd.concat([df_old, df_new], ignore_index=True)
    df = remove_duplicate_references(df)

    print(f"Updates references for: {folder}")
    save_references(df, folder)



