import os
import yfinance as yf
from dotenv import load_dotenv
import tweepy

# List of tickers to track
TICKERS = ["SPY", "QQQ", "AMZN", "GOOG", "NVDA", "TSLA", "HOOD", "COIN", "HIMS"]


def get_movement_emoji(pct_change):
    """
    Returns an emoji (or combination) based on the percentage change in a ticker's price.
    Adjust thresholds as desired.
    """
    # Large positive moves
    if pct_change > 20:
        return "🕊️"
    elif pct_change > 15:
        return "🚀"
    elif pct_change > 10:
        return "⚡"
    elif pct_change > 5:
        return "📈"
    elif pct_change > 1:
        return "⬆️"

    # Large negative moves
    elif pct_change < -20:
        return "🕳️"
    elif pct_change < -15:
        return "☠️"
    elif pct_change < -10:
        return "🩸"
    elif pct_change < -5:
        return "📉"
    elif pct_change < -1:
        return "⬇️"

    # Near flat (within ±1%)
    return "↔️"


def fetch_eod_performance(tickers):
    """
    Fetches the last 2 days of daily data for each ticker, then computes the
    day-over-day percentage change in closing price.

    Returns a dict like:
    {
      'SPY': {'close': 420.0, 'pct_change': 1.24},
      'QQQ': {'close': 345.5, 'pct_change': -0.77},
      ...
    }
    """
    # Download the last 5 days of data to ensure at least 2 valid trading days.
    df = yf.download(
        tickers=tickers,
        period="5d",
        interval="1d",
        group_by="ticker",
        threads=True,
        auto_adjust=False
    )

    performance = {}
    for ticker in tickers:
        try:
            # Each ticker’s data is in df[ticker] if multiple tickers are passed.
            sub_df = df[ticker].dropna().tail(2)  # last 2 valid rows
            if len(sub_df) < 2:
                continue  # Not enough data

            close_yesterday = sub_df["Close"].iloc[0]
            close_today = sub_df["Close"].iloc[1]
            pct_change = ((close_today - close_yesterday) / close_yesterday) * 100

            performance[ticker] = {
                "close": close_today,
                "pct_change": pct_change
            }
        except Exception:
            pass

    return performance


def post_tweet(text):
    """
    Posts a text-only tweet with the Tweepy v2 Client,
    using the same approach as in your monthly BTC script.
    """
    print("[INFO] Attempting to post a text-only tweet...")
    load_dotenv()

    # Retrieve credentials from .env
    api_key = os.getenv("API_KEY")
    api_key_secret = os.getenv("API_KEY_SECRET")
    access_token = os.getenv("ACCESS_TOKEN")
    access_token_secret = os.getenv("ACCESS_TOKEN_SECRET")

    missing = []
    for var_name, var_value in [
        ("API_KEY", api_key),
        ("API_KEY_SECRET", api_key_secret),
        ("ACCESS_TOKEN", access_token),
        ("ACCESS_TOKEN_SECRET", access_token_secret)
    ]:
        if not var_value:
            missing.append(var_name)
    if missing:
        raise ValueError(f"[ERROR] Missing required credentials in .env: {', '.join(missing)}")

    try:
        # STEP 1: OAuth1 auth object (commonly used for uploading media,
        # but we won't actually upload anything in this script).
        auth_1a = tweepy.OAuth1UserHandler(
            api_key,
            api_key_secret,
            access_token,
            access_token_secret
        )
        # If we needed the v1.1 "API" object, we could do:
        # api_v1 = tweepy.API(auth_1a)

        # STEP 2: Post the tweet with the Tweepy v2 Client
        client = tweepy.Client(
            consumer_key=api_key,
            consumer_secret=api_key_secret,
            access_token=access_token,
            access_token_secret=access_token_secret
        )
        print("[INFO] Creating tweet with v2 client...")
        response = client.create_tweet(text=text)
        print("[INFO] Tweet creation successful.")
        return response
    except Exception as e:
        raise RuntimeError(f"[ERROR] Failed to post tweet: {e}")


def main():
    # 1) Fetch the day-over-day performance data
    perf_data = fetch_eod_performance(TICKERS)

    if not perf_data:
        print("[INFO] No performance data fetched (possibly a holiday or no new data).")
        return

    # 2) Build the text lines for each ticker
    lines = []
    for ticker in TICKERS:
        info = perf_data.get(ticker)
        if info:
            close_price = info["close"]
            pct_chg = info["pct_change"]
            sign = "+" if pct_chg >= 0 else ""

            # Add the emoji
            emoji = get_movement_emoji(pct_chg)

            line = f"${ticker}: ${close_price:.2f} ({sign}{pct_chg:.2f}%) {emoji}"
            lines.append(line)
        else:
            lines.append(f"{ticker}: No Data")

    # 3) Create the final tweet text
    # Example:
    # EOD PERFORMANCE
    # $SPY: $414.00 (+1.23%) 📈
    # $QQQ: $325.50 (-0.56%) ⬇️
    # ...
    tweet_text = "EOD PERFORMANCE\n\n" + "\n".join(lines) + "\n\n#Stocks #Investing"

    # 4) Post the tweet with the v2 client
    try:
        response = post_tweet(tweet_text)
        print("[SUCCESS] Tweet posted successfully!")
        print(f"[INFO] Tweet ID: {response.data.get('id')}")
    except Exception as e:
        print(e)


if __name__ == "__main__":
    main()
