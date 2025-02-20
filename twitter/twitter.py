from typing import Dict, Any
import tweepy
from keys.keys import twitter_api_key, twitter_api_secret, twitter_access_token, twitter_access_token_secret, twitter_bearer_token

client = tweepy.Client(
    consumer_key=twitter_api_key,
    consumer_secret=twitter_api_secret,
    access_token=twitter_access_token,
    access_token_secret=twitter_access_token_secret,
    bearer_token=twitter_bearer_token
)

def post_tweet(text: str) -> Dict:
    """Post a tweet using Tweepy and return the response."""
    try:
        
        response = client.create_tweet(text=text)
        return {
            "status": "success",
            "tweet_id": response.data['id'],
            "text": text
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "text": text
        }
