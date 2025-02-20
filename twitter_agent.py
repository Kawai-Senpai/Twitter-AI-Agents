import asyncio
import os
import random
import httpx  # For async HTTP calls
from typing import Dict, Any
import tweepy
from dotenv import load_dotenv
from ultraconfiguration import UltraConfig
from ultraprint.logging import logger
from keys.keys import environment
from keys.keys import twitter_api_key, twitter_api_secret, twitter_access_token, twitter_access_token_secret, twitter_bearer_token

#! Initialize ---------------------------------------------------------------
config = UltraConfig('config.json')
log = logger('chat_log', 
            filename='debug/chat.log', 
            include_extra_info=config.get("logging.include_extra_info", False), 
            write_to_file=config.get("logging.write_to_file", False), 
            log_level=config.get("logging.development_level", "DEBUG") if environment == 'development' else config.get("logging.production_level", "INFO"))

# Load environment variables
load_dotenv()

# API and agent settings
API_BASE_URL = "http://localhost:8000/agent"
SESSION_ID = "default_session"  # Use dynamic session if needed
AGENT_ID = "vitalik"
TWEET_STYLES = [
    "technical_insight",
    "philosophical_observation",
    "future_prediction",
    "current_analysis",
    "historical_comparison"
]

# -----------------------------------------------
# Twitter posting function
# -----------------------------------------------
def post_tweet(text: str) -> Dict:
    """Post a tweet using Tweepy and return the response."""
    try:
        client = tweepy.Client(
            consumer_key=twitter_api_key,
            consumer_secret=twitter_api_secret,
            access_token=twitter_access_token,
            access_token_secret=twitter_access_token_secret,
            bearer_token=twitter_bearer_token
        )
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

# -----------------------------------------------
# API caller function
# -----------------------------------------------
async def call_api(prompt: str, client: httpx.AsyncClient) -> str:
    """Call the external API endpoint to process the prompt."""
    url = f"{API_BASE_URL}/{SESSION_ID}?agent_id={AGENT_ID}"
    try:
        payload = {"input": prompt}
        response = await client.post(url, json=payload)
        data = response.json()
        return data.get("response", "")
    except Exception as e:
        print(f"Error calling API: {e}")
        return ""

# -----------------------------------------------
# Helper to format tweet text
# -----------------------------------------------
def format_tweet(content: str) -> str:
    """Format content into a tweet-sized message."""
    if len(content) <= 280:
        return content
    bp = content[:277].rfind('.')
    if bp == -1:
        bp = content[:277].rfind(' ')
    return content[:bp + 1] if bp != -1 else content[:277] + "..."

# -----------------------------------------------
# Main function to generate and optionally post a tweet
# -----------------------------------------------
async def generate_and_post_tweet(post_to_twitter: bool = False, client: httpx.AsyncClient = None) -> Dict[str, Any]:
    """Generate a tweet in Vitalik's style via an API call and optionally post it."""
    style = random.choice(TWEET_STYLES)
    seed_topic = "Ethereum scaling solutions"  # Can randomize if needed
    prompt = (f"Write a tweet in the style of Vitalik Buterin ({style}) about "
            f"{seed_topic}. Use a mix of technical insight and philosophical observation.")
    
    tweet_response = await call_api(prompt, client)
    tweet = format_tweet(tweet_response)
    result = {
        "tweet": tweet,
        "topic": seed_topic,
        "style": style,
        "character_count": len(tweet)
    }
    if post_to_twitter:
        result["twitter_response"] = post_tweet(tweet)
    return result

# -----------------------------------------------
# Main async entry point
# -----------------------------------------------
async def main():
    async with httpx.AsyncClient() as client:
        result = await generate_and_post_tweet(post_to_twitter=False, client=client)
        if "tweet" in result:
            print("Generated Tweet:")
            print("-" * 40)
            print(result["tweet"])
            print("-" * 40)
            print(f"Topic: {result['topic']}")
            print(f"Style: {result['style']}")
            print(f"Character Count: {result['character_count']}")
            if "twitter_response" in result:
                print("\nTwitter Response:")
                print(result["twitter_response"])
        else:
            print("Error:", result.get("error", "Unknown error occurred"))

if __name__ == "__main__":
    asyncio.run(main())