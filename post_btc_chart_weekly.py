import os
import requests
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
import tweepy


def fetch_btc_data():
    """
    Fetches the past 7 days of Bitcoin-USD price data from CoinGecko,
    converting timestamps from UTC to ET (America/New_York).
    Returns a list of (datetime, price) in Eastern Time.
    Raises an Exception if there's any HTTP or data parsing issue.
    """
    print("[INFO] Fetching BTC data from CoinGecko...")
    url = "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart"
    params = {
        "vs_currency": "usd",
        "days": 7  # last 7 days
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

    print(f"[INFO] Successfully retrieved {len(btc_data)} data points for BTC (7 days).")
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
    Uses QuickChart.io to generate a line chart image for BTC price data in dark mode.
    Dynamically computes the y-axis min/max based on data to 'zoom in' on the price range.
    Saves the resulting PNG image to 'filename'.
    Raises an Exception if QuickChart returns an error.
    """
    if not btc_data:
        raise ValueError("[ERROR] No BTC data to generate a chart.")

    print(f"[INFO] Generating DARK MODE chart with {len(btc_data)} data points using QuickChart.io...")

    # Create arrays of timestamps (strings) and prices
    labels = [dt.strftime("%m-%d %H:%M") for dt, _ in btc_data]  # Example format includes day & hour
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
                "text": "BTC Price (Last 7 Days)",
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
        # A) Fetch BTC data (7 days) in ET
        btc_data = fetch_btc_data()

        # B) (Optional) Downsample if needed to avoid large payloads, e.g. every 5th data point
        btc_data = btc_data[::5]
        print(f"[INFO] Downsampled data to {len(btc_data)} points.")

        # C) Compute price stats
        latest_price = btc_data[-1][1]
        earliest_price = btc_data[0][1]
        price_diff = latest_price - earliest_price
        pct_change = (price_diff / earliest_price) * 100 if earliest_price else 0

        # D) Generate the dark-mode weekly chart
        chart_filename = "chart.png"
        generate_chart_image(btc_data, filename=chart_filename)

        # E) Determine appropriate emoji(s) for the price movement
        movement_emoji = get_movement_emoji(pct_change)

        # Build tweet text
        tweet_text = (
            f"BITCOIN IS NOW: ${latest_price:,.2f} {movement_emoji}\n\n"
            f"7D CHANGE: \n${price_diff:,.2f} \n({pct_change:,.2f}%)\n\n"
            "$BTC #Bitcoin #Crypto"
        )

        # F) Post tweet with chart
        print("[INFO] Posting tweet with weekly BTC price chart...")
        response = post_tweet_with_image(tweet_text, chart_filename)
        print("[SUCCESS] Tweet posted successfully!")
        print(f"[INFO] Tweet ID: {response.data.get('id')}")

    except Exception as e:
        print(e)


if __name__ == "__main__":
    main()
