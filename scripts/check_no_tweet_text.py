"""Fail if any tweet text from the private dataset appears in the repository.

Run this before every push. It needs the private file that contains the tweet text
(the full dataset with a `text` column), so it is a check for the author, not for
people who clone the repo.

    python scripts/check_no_tweet_text.py --text-csv /path/to/Main_Twitter_Sentiment_Analysis_Dataset.csv

Method: take the first 30 characters (whitespace-normalised) of every tweet that has at
least 30 characters, then slide a 30-character window over every text file in the repo
(notebook cells and outputs, CSV, Markdown, Python, ...). Any exact match is reported.
It also fails if a CSV in the repo has a column that normally carries tweet text or
user identity.
"""
import argparse
import csv
import json
import os
import re
import sys

import pandas as pd

WINDOW = 30
BAD_COLUMNS = {"text", "clean_text", "processed_text", "url", "username", "fullname", "user_location", "hashtags"}
TEXT_EXT = {".ipynb", ".csv", ".md", ".py", ".txt", ".sh", ".json", ".yml", ".yaml", ".toml", ".cfg"}
# Not part of the repo: version control, caches, raw data, and Python environments.
# Third-party packages (pandas tests, etc.) contain strings like "looooooo..." that can
# coincide with a tweet prefix, which would be a false alarm.
SKIP_DIRS = {".git", "__pycache__", ".ipynb_checkpoints", "raw", ".venv", "venv", "env", ".env",
             "node_modules", "site-packages", ".conda", ".tox", ".mypy_cache", ".pytest_cache"}


def norm(s):
    return re.sub(r"\s+", " ", s).strip().lower()


def notebook_strings(path):
    nb = json.load(open(path, encoding="utf-8"))
    out = []

    def walk(x, key=None):
        if isinstance(x, dict):
            for k, v in x.items():
                if k.startswith("image/") or k.startswith("application/vnd.plotly"):
                    continue
                walk(v, k)
        elif isinstance(x, list):
            for v in x:
                walk(v, key)
        elif isinstance(x, str):
            out.append(x)

    walk(nb)
    return "\n".join(out)


def iter_files(root):
    for d, dirs, files in os.walk(root):
        # Skip any virtual environment, whatever its folder is called (it has a pyvenv.cfg).
        dirs[:] = [x for x in dirs if x not in SKIP_DIRS and not os.path.exists(os.path.join(d, x, "pyvenv.cfg"))]
        for f in files:
            p = os.path.join(d, f)
            if os.path.splitext(f)[1].lower() in TEXT_EXT:
                yield p


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--text-csv", required=True, help="private CSV with a `text` column")
    ap.add_argument("--repo", default=".", help="repository root (default: current directory)")
    a = ap.parse_args()

    texts = pd.read_csv(a.text_csv, usecols=["text"], dtype=str, keep_default_na=False)["text"]
    prefixes = {norm(t)[:WINDOW] for t in texts if len(norm(t)) >= WINDOW}
    print(f"loaded {len(prefixes):,} tweet prefixes of {WINDOW} characters")

    problems = []
    n_files = 0
    for p in iter_files(a.repo):
        n_files += 1
        rel = os.path.relpath(p, a.repo)
        if rel.endswith("check_no_tweet_text.py"):
            continue
        ext = os.path.splitext(p)[1].lower()
        try:
            body = notebook_strings(p) if ext == ".ipynb" else open(p, encoding="utf-8", errors="ignore").read()
        except Exception as e:  # unreadable notebook counts as a failure, not a pass
            problems.append(f"{rel}: could not be parsed ({e})")
            continue
        if ext == ".csv":
            with open(p, newline="", encoding="utf-8", errors="ignore") as fh:
                header = next(csv.reader(fh), [])
            bad = [h for h in header if h.strip().lower() in BAD_COLUMNS]
            if bad:
                problems.append(f"{rel}: column(s) {bad} normally hold tweet text or user identity")
        body = norm(body)
        hit = next((body[i:i + WINDOW] for i in range(len(body) - WINDOW + 1) if body[i:i + WINDOW] in prefixes), None)
        if hit:
            problems.append(f"{rel}: contains tweet text starting '{hit}'")

    print(f"scanned {n_files} files")
    if problems:
        print("FAIL")
        for x in problems:
            print("  -", x)
        sys.exit(1)
    print("OK: no tweet text found")


if __name__ == "__main__":
    main()
