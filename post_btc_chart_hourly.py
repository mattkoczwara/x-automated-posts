import os
import requests
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
import tweepy


def fetch_btc_data():
    """
    Fetches the past 24h of Bitcoin-USD price data from CoinGecko,
    converting timestamps from UTC to ET (America/New_York).
    Returns a list of (datetime, price) in Eastern Time.
    Raises an Exception if there's any HTTP or data parsing issue.
    """
    print("[INFO] Fetching BTC data (24h) from CoinGecko...")
    url = "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart"
    params = {
        "vs_currency": "usd",
        "days": 1  # fetch 1 day of data
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise Exception(f"[ERROR] Failed to fetch data from CoinGecko: {e}")

    data = response.json()
    if "prices" not in data or not data["prices"]:
        raise Exception("[ERROR] CoinGecko response is missing 'prices' data.")

    btc_data = []
    for point in data["prices"]:
        timestamp_ms, price = point
        # Convert from UTC -> ET
        dt_utc = datetime.utcfromtimestamp(timestamp_ms / 1000).replace(tzinfo=timezone.utc)
        dt_et = dt_utc.astimezone(ZoneInfo("America/New_York"))
        btc_data.append((dt_et, price))

    print(f"[INFO] Successfully retrieved {len(btc_data)} data points for BTC (24h).")
    return btc_data


def get_movement_emoji(pct_change):
    """
    Returns an emoji (or combination) based on the percentage change in BTC price.
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


def generate_chart_image(btc_data, filename="chart.png"):
    """
    Uses QuickChart.io to generate a line chart image for BTC price data in dark mode,
    for the filtered last hour. Dynamically computes y-axis min/max to 'zoom in.'
    Saves the resulting PNG image to 'filename'.
    Raises an Exception if QuickChart returns an error.
    """
    if not btc_data:
        raise ValueError("[ERROR] No BTC data to generate a chart.")

    print(f"[INFO] Generating DARK MODE chart with {len(btc_data)} data points (last hour) using QuickChart.io...")

    # Create arrays of timestamps (strings) and prices
    # Show only hour:minute for a single hour
    labels = [dt.strftime("%H:%M") for dt, _ in btc_data]
    prices = [round(price, 2) for _, price in btc_data]

    lowest_price = min(prices)
    highest_price = max(prices)
    price_range = highest_price - lowest_price

    # Add a small buffer around min and max for visual spacing
    y_min = lowest_price - (price_range * 0.05)
    y_max = highest_price + (price_range * 0.05)

    chart_config = {
        "type": "line",
        "data": {
            "labels": labels,
            "datasets": [
                {
                    "label": "BTC Price (USD)",
                    "data": prices
                }
            ]
        },
        "options": {
            "title": {
                "display": True,
                "text": "BTC Price (Last Hour)",
                "color": "#FFFFFF"  # White title text
            },
            "scales": {
                "y": {
                    "min": y_min,
                    "max": y_max,
                    "ticks": {
                        "color": "#FFFFFF"  # White y-axis labels
                    },
                    "grid": {
                        "color": "rgba(255, 255, 255, 0.2)"  # Light/transparent white grid lines
                    }
                },
                "x": {
                    "ticks": {
                        "color": "#FFFFFF"  # White x-axis labels
                    },
                    "grid": {
                        "color": "rgba(255, 255, 255, 0.2)"
                    }
                }
            },
            "plugins": {
                "legend": {
                    "labels": {
                        "color": "#FFFFFF"  # White legend text
                    }
                }
            }
        }
    }

    quickchart_url = "https://quickchart.io/chart"
    payload = {
        "width": 600,
        "height": 300,
        "format": "png",
        "backgroundColor": "#000000",  # black background for dark mode
        "chart": chart_config
    }

    # POST request to generate the chart
    try:
        response = requests.post(quickchart_url, json=payload)
        if response.status_code != 200:
            print("[DEBUG] QuickChart response text:", response.text)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise Exception(f"[ERROR] Failed to generate chart from QuickChart.io: {e}")

    with open(filename, "wb") as f:
        f.write(response.content)

    print(f"[INFO] Dark mode chart image saved as '{filename}'.")


def post_tweet_with_image(text, image_path):
    """
    1) Upload 'image_path' to X (via Tweepy v1.1 API)
    2) Post a tweet (via Tweepy v2 Client) with the uploaded media
    Returns the Tweepy 'create_tweet' response on success.
    Raises an Exception if uploading or tweeting fails.
    """
    print("[INFO] Attempting to post tweet with image...")
    load_dotenv()

    # Retrieve credentials from .env
    api_key = os.getenv("API_KEY")
    api_key_secret = os.getenv("API_KEY_SECRET")
    access_token = os.getenv("ACCESS_TOKEN")
    access_token_secret = os.getenv("ACCESS_TOKEN_SECRET")

    missing_creds = []
    for var_name, var_value in [
        ("API_KEY", api_key),
        ("API_KEY_SECRET", api_key_secret),
        ("ACCESS_TOKEN", access_token),
        ("ACCESS_TOKEN_SECRET", access_token_secret)
    ]:
        if not var_value:
            missing_creds.append(var_name)
    if missing_creds:
        raise ValueError(f"[ERROR] Missing required credentials in .env: {', '.join(missing_creds)}")

    try:
        # Step 1: Upload media via Tweepy v1.1 API
        auth_1a = tweepy.OAuth1UserHandler(api_key, api_key_secret, access_token, access_token_secret)
        api_v1 = tweepy.API(auth_1a)
        print(f"[INFO] Uploading media '{image_path}' to X...")
        media = api_v1.media_upload(filename=image_path)
        print(f"[INFO] Media upload successful (media_id={media.media_id}).")

        # Step 2: Post tweet with attached image (Tweepy v2)
        client = tweepy.Client(
            consumer_key=api_key,
            consumer_secret=api_key_secret,
            access_token=access_token,
            access_token_secret=access_token_secret
        )
        print("[INFO] Creating tweet...")
        response = client.create_tweet(text=text, media_ids=[media.media_id])
        print("[INFO] Tweet creation successful.")
        return response
    except Exception as e:
        raise Exception(f"[ERROR] Failed to post tweet with image: {e}")


def main():
    try:
        # 1) Fetch the full 24h data
        full_day_data = fetch_btc_data()

        # 2) Filter to only the last hour (using local ET time)
        now_et = datetime.now(tz=ZoneInfo("America/New_York"))
        one_hour_ago = now_et - timedelta(hours=1)

        # Keep points where timestamp > (now - 1 hour)
        btc_data_1h = [(dt, price) for dt, price in full_day_data if dt > one_hour_ago]

        if len(btc_data_1h) < 2:
            print("[INFO] Not enough data points in the last hour to calculate change. Exiting.")
            return

        # 3) Sort by timestamp just to be sure
        btc_data_1h.sort(key=lambda x: x[0])
        earliest_price = btc_data_1h[0][1]
        latest_price = btc_data_1h[-1][1]

        price_diff = latest_price - earliest_price
        pct_change = (price_diff / earliest_price) * 100

        # 4) Check if absolute movement is greater than 10%
        if abs(pct_change) < 10:
            print(f"[INFO] Movement is only {pct_change:.2f}%. Less than 10%. Skipping post.")
            return
        else:
            print(f"[INFO] Price moved {pct_change:.2f}% in the last hour. Proceeding with tweet...")

        # 5) Generate the chart (optionally downsample if needed)
        # e.g., btc_data_1h = btc_data_1h[::2] if large
        generate_chart_image(btc_data_1h, filename="chart.png")

        # 6) Determine emoji(s)
        movement_emoji = get_movement_emoji(pct_change)

        # 7) Build final tweet text
        tweet_text = (
            f"BITCOIN MAKING MOVES\n\n"
            f"BTC IS NOW: ${latest_price:,.2f} {movement_emoji}\n\n"
            f"1H CHANGE: \n{price_diff:,.2f} USD \n({pct_change:,.2f}%)\n\n"
            "#Bitcoin #BTC #Crypto"
        )

        # 8) Post tweet
        print("[INFO] Posting tweet with hourly BTC data...")
        response = post_tweet_with_image(tweet_text, "chart.png")
        print("[SUCCESS] Tweet posted successfully!")
        print(f"[INFO] Tweet ID: {response.data.get('id')}")

    except Exception as e:
        print(e)


if __name__ == "__main__":
    main()
