"""Create the text-free files in data/ from the private full datasets.

The full datasets contain tweet text (and, in the raw export, tweet URLs), which is
not redistributed. This script documents exactly which columns were kept. It needs the
private files, so it cannot be run from a fresh clone.

Usage:
    python scripts/make_derived_data.py \
        --main  /path/to/Main_Twitter_Sentiment_Analysis_Dataset.csv \
        --annotated /path/to/sample_tweets_for_annotation.csv \
        --out-dir data
"""
import argparse
import os

import pandas as pd

DERIVED_COLS = ["id", "timestamp", "Text_noise", "Processed_text_noise", "Compound", "Sentiment"]
ANNOTATION_COLS = ["id", "Compound", "Sentiment", "Human_Sentiment"]


def read_as_text(path):
    # dtype=str keeps 19-digit tweet IDs and float strings exactly as written
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--main", required=True)
    ap.add_argument("--annotated", required=True)
    ap.add_argument("--out-dir", default="data")
    a = ap.parse_args()

    main_df = read_as_text(a.main)
    derived = main_df[DERIVED_COLS]
    os.makedirs(os.path.join(a.out_dir, "derived"), exist_ok=True)
    derived.to_csv(os.path.join(a.out_dir, "derived", "twitter_sentiment_scores_2021.csv"), index=False)

    ann = read_as_text(a.annotated)[ANNOTATION_COLS]
    os.makedirs(os.path.join(a.out_dir, "annotation"), exist_ok=True)
    ann.to_csv(os.path.join(a.out_dir, "annotation", "sample_tweets_annotated.csv"), index=False)

    print(f"derived:    {len(derived):,} rows x {derived.shape[1]} columns")
    print(f"annotation: {len(ann):,} rows x {ann.shape[1]} columns")


if __name__ == "__main__":
    main()
