import asyncio
import random
import httpx  # For async HTTP calls
from typing import Dict, Any
from ultraconfiguration import UltraConfig
from ultraprint.logging import logger
from keys.keys import environment
from keys.keys import aiml_service_url
from twitter.twitter import post_tweet

#! Initialize ---------------------------------------------------------------
config = UltraConfig('config.json')
log = logger('chat_log', 
            filename='debug/chat.log', 
            include_extra_info=config.get("logging.include_extra_info", False), 
            write_to_file=config.get("logging.write_to_file", False), 
            log_level=config.get("logging.development_level", "DEBUG") if environment == 'development' else config.get("logging.production_level", "INFO"))

#? API caller function -----------------------------------------------------------
async def call_api(prompt: str, client: httpx.AsyncClient) -> str:
    """Call the external API endpoint to process the prompt."""
    session_id = config.get("session_id")
    agent_id = config.get("agent_id")
    url = f"{aiml_service_url}/chat/agent/{session_id}"
    
    try:
        payload = {"message": prompt}
        params = {
            "agent_id": agent_id,
            "use_rag": "True",
            "stream": "False",
            "include_rich_response": "False"
        }
        
        response = await client.post(url, json=payload, params=params)
        response.raise_for_status()
        data = response.json()
        return data.get("response", "")
    except Exception as e:
        log.error(f"Error calling API: {e}")
        return ""

#? Helper to format tweet text -----------------------------------------------------
def format_tweet(content: str) -> str:
    """Format content into a tweet-sized message."""
    if len(content) <= 280:
        return content
    bp = content[:277].rfind('.')
    if bp == -1:
        bp = content[:277].rfind(' ')
    return content[:bp + 1] if bp != -1 else content[:277] + "..."

#? Main function to generate and optionally post a tweet ---------------------------
async def generate_and_post_tweet(post_to_twitter: bool = False, client: httpx.AsyncClient = None) -> Dict[str, Any]:
    """Generate a tweet in Vitalik's style via an API call and optionally post it."""

    style = random.choice(config.get("tweet_styles", ["future_prediction"]))
    seed_topic = random.choice(config.get("seed_topics", ["Ethereum scaling solutions"]))
    
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

#? Main async entry point ----------------------------------------------------------
async def main():
    async with httpx.AsyncClient() as client:
        result = await generate_and_post_tweet(post_to_twitter=False, client=client)
        if "tweet" in result:
            log.success("Generated Tweet:")
            log.info("-" * 40)
            log.info(result["tweet"])
            log.info("-" * 40)
            log.info(f"Topic: {result['topic']}")
            log.info(f"Style: {result['style']}")
            log.info(f"Character Count: {result['character_count']}")
            if "twitter_response" in result:
                log.info("\nTwitter Response:")
                log.info(result["twitter_response"])
        else:
            log.error("Error: " + result.get("error", "Unknown error occurred"))

if __name__ == "__main__":
    asyncio.run(main())