"""Recompute the headline tables from the committed data and write them to results/.

Runs from a fresh clone (no tweet text needed):
    python scripts/make_results_tables.py

Outputs
    results/correlation_summary.csv        Pearson r, p and n for every sentiment / volume test
    results/vader_validation.csv           per-class precision and recall on the 40 hand-labelled tweets
    results/sentiment_distribution.csv     VADER label counts, overall and by month
    results/figures/correlation_summary.png

The logic mirrors notebooks 05, 06, 08 and 09 (same aggregation rules); the notebooks remain the
primary record. This script exists so the tables, including the sample sizes n, can be regenerated
and checked without opening a notebook.
"""
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import pearsonr
from sklearn.metrics import accuracy_score, precision_score, recall_score

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(ROOT, "results")
os.makedirs(os.path.join(OUT, "figures"), exist_ok=True)

MONTH_END = "ME"
try:  # pandas >= 2.2 uses "ME"; older versions use "M"
    pd.Series([0], index=pd.to_datetime(["2021-01-01"])).resample("ME")
except ValueError:
    MONTH_END = "M"


def load_prices():
    px = {}
    for coin, ticker in (("Bitcoin", "BTC-USD"), ("Ethereum", "ETH-USD")):
        d = pd.read_csv(os.path.join(DATA, "prices", f"{ticker}_1d_2021.csv"), usecols=["Date", "Close", "Returns"])
        d["Date"] = pd.to_datetime(d["Date"])
        px[coin] = d
    return px


def sentiment_tests(px):
    t = pd.read_csv(os.path.join(DATA, "derived", "twitter_sentiment_scores_2021.csv"), usecols=["timestamp", "Compound"])
    t["Date"] = pd.to_datetime(pd.to_datetime(t["timestamp"]).dt.date)
    daily_sent = t.groupby("Date")["Compound"].mean().reset_index()
    sent_w = daily_sent.set_index("Date").resample("W-FRI")["Compound"].mean()
    sent_m = daily_sent.set_index("Date").resample(MONTH_END)["Compound"].mean()
    rows = []
    for coin, d in px.items():
        w = d.set_index("Date").resample("W-FRI")["Returns"].sum()
        m = d.set_index("Date").resample(MONTH_END)["Returns"].sum()
        daily = pd.merge(daily_sent, d[["Date", "Returns"]], on="Date").dropna(subset=["Compound", "Returns"])
        weekly = pd.merge(w, sent_w, left_index=True, right_index=True).dropna(subset=["Compound", "Returns"])
        monthly = pd.merge(m, sent_m, left_index=True, right_index=True).dropna(subset=["Compound", "Returns"])
        for name, df in (("Daily", daily), ("Weekly", weekly), ("Monthly", monthly)):
            r, p = pearsonr(df["Compound"], df["Returns"])
            rows.append(("sentiment vs returns", coin, name, len(df), r, p, ""))
        daily = daily.copy()
        daily["RS"] = daily["Compound"].rolling(7).mean()
        daily["RR"] = daily["Returns"].rolling(7).mean()
        x = daily.dropna(subset=["RS", "RR"])
        r, p = pearsonr(x["RR"], x["RS"])
        rows.append(("sentiment vs returns", coin, "7-day smoothed", len(x), r, p, "overlapping windows"))
        for lag in (1, 2, 3):
            sh = daily["RS"].shift(lag).dropna()
            r, p = pearsonr(sh, daily["RR"].dropna().iloc[-len(sh):])
            rows.append(("sentiment vs returns", coin, f"7-day smoothed, {lag}-day lag", len(sh), r, p, "overlapping windows"))
        daily["Vol"] = daily["Returns"].rolling(7).std()
        n = min(daily["RS"].dropna().shape[0], daily["Vol"].dropna().shape[0])
        r, p = pearsonr(daily["RS"].dropna().iloc[-n:], daily["Vol"].dropna().iloc[-n:])
        rows.append(("sentiment vs 7-day volatility", coin, "7-day smoothed", n, r, p, "overlapping windows"))
    return rows


def volume_tests(px):
    c = pd.read_excel(os.path.join(DATA, "tweet_counts", "daily_tweet_counts_2021.xlsx"))
    c["Date"] = pd.to_datetime(c["Date"])
    rows = []
    for coin, d in px.items():
        d = d.copy()
        d["Returns"] = d["Close"].pct_change()
        d = d.dropna(subset=["Returns"])
        daily = pd.merge(d[["Date", "Returns"]], c, on="Date")
        weekly = daily.resample("W-FRI", on="Date").mean().reset_index()
        monthly = daily.resample(MONTH_END, on="Date").mean().reset_index()
        for name, df in (("Daily", daily), ("Weekly", weekly), ("Monthly", monthly)):
            r, p = pearsonr(df["Returns"], df["Count"])
            note = "12 points; not interpreted" if name == "Monthly" else ""
            rows.append(("tweet volume vs returns", coin, name, len(df), r, p, note))
    return rows


def vader_validation():
    a = pd.read_csv(os.path.join(DATA, "annotation", "sample_tweets_annotated.csv"), dtype={"id": str})
    labels = ["POSITIVE", "NEGATIVE", "NEUTRAL"]
    prec = precision_score(a["Human_Sentiment"], a["Sentiment"], labels=labels, average=None)
    rec = recall_score(a["Human_Sentiment"], a["Sentiment"], labels=labels, average=None)
    out = pd.DataFrame({
        "class": labels,
        "precision_pct": np.round(prec * 100, 2),
        "recall_pct": np.round(rec * 100, 2),
        "human_labelled": [int((a["Human_Sentiment"] == l).sum()) for l in labels],
        "vader_predicted": [int((a["Sentiment"] == l).sum()) for l in labels],
        "correct": [int(((a["Sentiment"] == l) & (a["Human_Sentiment"] == l)).sum()) for l in labels],
    })
    acc = accuracy_score(a["Human_Sentiment"], a["Sentiment"])
    out.loc[len(out)] = ["OVERALL (accuracy)", round(acc * 100, 2), round(acc * 100, 2), len(a), len(a), int(round(acc * len(a)))]
    return out


def sentiment_distribution():
    t = pd.read_csv(os.path.join(DATA, "derived", "twitter_sentiment_scores_2021.csv"), usecols=["timestamp", "Sentiment"])
    t["month"] = pd.to_datetime(t["timestamp"]).dt.strftime("%Y-%m")
    order = ["POSITIVE", "NEUTRAL", "NEGATIVE"]
    by_m = t.groupby(["month", "Sentiment"]).size().unstack(fill_value=0)[order]
    by_m.loc["2021 (all)"] = by_m.sum()
    pct = (by_m.div(by_m.sum(axis=1), axis=0) * 100).round(2)
    out = by_m.join(pct, rsuffix="_pct")
    out.columns = [f"{c.lower()}_count" if not c.endswith("_pct") else c.lower() for c in out.columns]
    out.insert(0, "tweets", by_m.sum(axis=1))
    return out.reset_index().rename(columns={"index": "period", "month": "period"})


def plot_summary(df):
    s = df[df["analysis"] == "sentiment vs returns"].copy()
    tests = list(dict.fromkeys(s["test"]))
    fig, ax = plt.subplots(figsize=(9, 5.2))
    colours = {"Bitcoin": "#F7931A", "Ethereum": "#627EEA"}
    ypos = {t: i for i, t in enumerate(reversed(tests))}
    for coin, off in (("Bitcoin", 0.13), ("Ethereum", -0.13)):
        d = s[s["coin"] == coin]
        y = [ypos[t] + off for t in d["test"]]
        sig = d["p"].values < 0.05
        ax.scatter(d["r"][sig], np.array(y)[sig], s=70, color=colours[coin], label=f"{coin} (p < 0.05, unadjusted)", zorder=3)
        ax.scatter(d["r"][~sig], np.array(y)[~sig], s=70, facecolors="white", edgecolors=colours[coin], linewidths=1.6,
                   label=f"{coin} (p ≥ 0.05)", zorder=3)
    ax.axvline(0, color="#444", linewidth=0.8)
    ax.set_yticks(list(ypos.values()))
    ax.set_yticklabels(list(ypos.keys()))
    ax.set_xlim(-0.45, 0.1)
    ax.set_xlabel("Pearson r (VADER compound sentiment vs returns)")
    ax.set_title("Sentiment vs returns, 2021: Pearson r by aggregation and lag", loc="left", fontsize=12)
    ax.grid(axis="x", alpha=0.3)
    ax.legend(loc="lower left", fontsize=8, frameon=False)
    fig.text(0.01, 0.01, "p-values unadjusted for multiple tests. Smoothed and lagged rows use overlapping 7-day windows, so their p-values are optimistic.",
             fontsize=7.5, color="#555")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(os.path.join(OUT, "figures", "correlation_summary.png"), dpi=150)
    plt.close(fig)


def main():
    px = load_prices()
    rows = sentiment_tests(px) + volume_tests(px)
    df = pd.DataFrame(rows, columns=["analysis", "coin", "test", "n", "r", "p", "note"])
    df["r"] = df["r"].round(6)
    df["p"] = df["p"].round(6)
    df.to_csv(os.path.join(OUT, "correlation_summary.csv"), index=False)
    vader_validation().to_csv(os.path.join(OUT, "vader_validation.csv"), index=False)
    sentiment_distribution().to_csv(os.path.join(OUT, "sentiment_distribution.csv"), index=False)
    plot_summary(df)
    print(df.to_string(index=False))


if __name__ == "__main__":
    main()
