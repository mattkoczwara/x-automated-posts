import os
from dotenv import load_dotenv
import tweepy


def main():
    # Load credentials from .env file
    load_dotenv()

    api_key = os.getenv("API_KEY")
    api_key_secret = os.getenv("API_KEY_SECRET")
    access_token = os.getenv("ACCESS_TOKEN")
    access_token_secret = os.getenv("ACCESS_TOKEN_SECRET")

    if not all([api_key, api_key_secret, access_token, access_token_secret]):
        raise ValueError("Missing one or more required credentials in .env")

    # Initialize Tweepy Client using OAuth 1.0a User Context for API v2
    client = tweepy.Client(
        consumer_key=api_key,
        consumer_secret=api_key_secret,
        access_token=access_token,
        access_token_secret=access_token_secret
    )

    # Post a tweet using the v2 endpoint
    try:
        response = client.create_tweet(text="Hello World!")
        print("Tweet posted successfully!")
        print("Tweet ID:", response.data["id"])
    except Exception as e:
        print("Error posting tweet:", e)


if __name__ == "__main__":
    main()
