# Data

Everything in this folder is either numeric or an identifier. **No tweet text, user names or tweet URLs are redistributed.**

## `derived/twitter_sentiment_scores_2021.csv`

50,293 rows, one per tweet, in the order of the original dataset. Produced from the private full dataset by [`scripts/make_derived_data.py`](../scripts/make_derived_data.py).

| Column | Meaning |
|---|---|
| `id` | Tweet ID (19 digits). Read it as a string or int64; Excel and float parsing corrupt it. |
| `timestamp` | Posting time, UTC, ISO 8601 |
| `Text_noise` | neattext noise score of the original text: (punctuation + stop-word + emoji + URL counts) / text length × 100 |
| `Processed_text_noise` | The same score after cleaning and lemmatisation |
| `Compound` | VADER compound score (−1 to 1) of the lemmatised text |
| `Sentiment` | `POSITIVE` if `Compound` > 0, `NEUTRAL` if = 0, `NEGATIVE` if < 0 |

Check: 27,405 positive, 16,188 neutral, 6,700 negative.

## `annotation/sample_tweets_annotated.csv`

40 rows: a random sample of the full dataset (`df.sample(n=40, random_state=42)`), with the VADER label and the hand label.

| Column | Meaning |
|---|---|
| `id` | Tweet ID |
| `Compound`, `Sentiment` | VADER output for the tweet (matches `derived/`) |
| `Human_Sentiment` | Hand label: `POSITIVE`, `NEUTRAL` or `NEGATIVE` |

## `prices/`

Six files from Yahoo Finance via `yfinance` (notebook 03): `BTC-USD` and `ETH-USD`, each at `1d`, `1wk` and `1mo`, for 2021.

Columns: `Date, Open, High, Low, Close, Volume, Dividends, Stock Splits, Returns`. `Returns` is the percentage change of `Close` from the previous bar, so the first row is empty.

## `tweet_counts/daily_tweet_counts_2021.xlsx`

`Date`, `Count`: 365 daily counts for the top 8 Bitcoin and Ethereum hashtags (144,157 to 1,011,392 per day). Supplied with the original project submission; used by notebook 09 as a volume measure. These counts are unrelated to the size of the 50,293-tweet sample.

## Not in the repository (`raw/`, git-ignored)

| File | Why it is withheld |
|---|---|
| Raw Apify export and daily exports | Tweet text, user names, URLs |
| Full scored dataset (50,293 × 10) | Contains `text`, `Clean_text`, `Processed_text` |
| Annotation file with tweet text | Tweet text |

To rebuild text from `id`, look the IDs up through X's official API, subject to X's current terms and your access tier. Deleted or protected posts will not be retrievable.
