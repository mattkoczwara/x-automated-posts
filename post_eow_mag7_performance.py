import os
import yfinance as yf
from dotenv import load_dotenv
import tweepy

# MAG 7 Tickers
TICKERS = ["MSFT", "AAPL", "GOOGL", "AMZN", "NVDA", "META", "TSLA"]


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


def fetch_weekly_performance(tickers):
    """
    Fetches the last 2 weekly data points for each ticker via yfinance,
    then computes the percentage change from last week's close to this week's close.

    Returns a dict:
    {
      'MSFT': {'close': 320.12, 'pct_change': 1.24},
      'AAPL': {'close': 198.50, 'pct_change': -0.77},
      ...
    }
    """
    # Download ~2 months of weekly data to ensure at least 2 valid candles.
    df = yf.download(
        tickers=tickers,
        period="2mo",
        interval="1wk",
        group_by="ticker",
        threads=True,
        auto_adjust=False
    )

    performance = {}
    for ticker in tickers:
        try:
            # Each ticker’s data is in df[ticker] if multiple tickers are passed.
            sub_df = df[ticker].dropna().tail(2)  # last 2 weekly rows
            if len(sub_df) < 2:
                # Not enough data
                continue

            close_prev_week = sub_df["Close"].iloc[0]
            close_this_week = sub_df["Close"].iloc[1]
            pct_change = ((close_this_week - close_prev_week) / close_prev_week) * 100

            performance[ticker] = {
                "close": close_this_week,
                "pct_change": pct_change
            }
        except Exception:
            pass

    return performance


def post_tweet(text):
    """
    Posts a text-only tweet with Tweepy v2 Client, matching the 'two-step' approach.
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
        # Step 1: Create OAuth1 object (commonly used for media, but we'll keep consistent)
        auth_1a = tweepy.OAuth1UserHandler(
            api_key,
            api_key_secret,
            access_token,
            access_token_secret
        )

        # Step 2: Create the v2 Client and post
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
    # 1) Fetch the weekly performance data
    perf_data = fetch_weekly_performance(TICKERS)

    if not perf_data:
        print("[INFO] No weekly performance data found (maybe not enough data?).")
        return

    # 2) Construct the lines for each ticker
    lines = []
    for ticker in TICKERS:
        info = perf_data.get(ticker)
        if info:
            close_price = info["close"]
            pct_chg = info["pct_change"]
            sign = "+" if pct_chg >= 0 else ""
            emoji = get_movement_emoji(pct_chg)

            line = f"${ticker}: ${close_price:.2f} ({sign}{pct_chg:.2f}%) {emoji}"
            lines.append(line)
        else:
            lines.append(f"${ticker}: No Data")

    # 3) Final tweet text
    tweet_text = "WEEKLY PERFORMANCE (MAG 7)\n\n" + "\n".join(lines) + "\n\n#TrumpTariffs #Stocks #Investing"

    # 4) Post the tweet
    try:
        response = post_tweet(tweet_text)
        print("[SUCCESS] Tweet posted successfully!")
        print(f"[INFO] Tweet ID: {response.data.get('id')}")
    except Exception as e:
        print(e)


if __name__ == "__main__":
    main()
