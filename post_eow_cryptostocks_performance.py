import os
import yfinance as yf
from dotenv import load_dotenv
import tweepy

# CRYPTO-RELATED Tickers
TICKERS = ["MSTR", "COIN", "RIOT", "MARA", "BTC-USD", "ETH-USD", "SOL-USD"]


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
      'MSTR': {'close': 305.12, 'pct_change': 1.24},
      'COIN': {'close': 65.50, 'pct_change': -0.77},
      ...
      'BTC-USD': {'close': 28150.50, 'pct_change': 2.00},
      ...
    }
    """
    # Download ~3 months of weekly data to ensure we have at least 2 valid weekly candles.
    df = yf.download(
        tickers=tickers,
        period="3mo",
        interval="1wk",
        group_by="ticker",
        threads=True,
        auto_adjust=False
    )

    performance = {}
    for ticker in tickers:
        try:
            sub_df = df[ticker].dropna().tail(2)  # last 2 weekly rows
            if len(sub_df) < 2:
                continue

            close_prev_week = sub_df["Close"].iloc[0]
            close_this_week = sub_df["Close"].iloc[1]
            pct_change = ((close_this_week - close_prev_week) / close_prev_week) * 100

            performance[ticker] = {
                "close": close_this_week,
                "pct_change": pct_change
            }
        except Exception:
            # Might occur if there's no valid data for that ticker
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
        # Step 1: OAuth1 auth (commonly used for media, but we keep it for consistency)
        auth_1a = tweepy.OAuth1UserHandler(
            api_key,
            api_key_secret,
            access_token,
            access_token_secret
        )

        # Step 2: Create the Tweepy v2 Client and post
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

    # 2) Build lines for each ticker
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
            lines.append(f"{ticker}: No Data")

    # 3) Create the final tweet text
    tweet_text = "WEEKLY PERFORMANCE (Crypto-Related)\n\n" + "\n".join(lines) + "\n\n#STOCKS #CRYPTO"

    # 4) Post the tweet
    try:
        response = post_tweet(tweet_text)
        print("[SUCCESS] Tweet posted successfully!")
        print(f"[INFO] Tweet ID: {response.data.get('id')}")
    except Exception as e:
        print(e)


if __name__ == "__main__":
    main()
