import asyncio
import random
import httpx
import traceback
from typing import Dict, Any
from ultraconfiguration import UltraConfig
from ultraprint.logging import logger
from keys.keys import environment
from keys.keys import aiml_service_url
from twitter.twitter import post_tweet
import argparse

#? Configuration constants --------------------------------------------------------
HTTP_TIMEOUT = 30.0  # seconds

#? API caller function -----------------------------------------------------------
async def call_api(prompt: str, client: httpx.AsyncClient) -> str:
    """
    Call the external API endpoint to process the given prompt.
    This asynchronous function sends a POST request to an external API endpoint with the provided prompt.
    It constructs the API URL using session and agent identifiers retrieved from configuration values, and uses
    customized request parameters and timeout settings.
    Args:
        prompt (str): The message to be processed by the external API.
        client (httpx.AsyncClient): The asynchronous HTTP client used to send the API request.
    Returns:
        str: The response from the API as a string. If the API returns an empty response or in case of an exception,
            an empty string is returned.
    Notes:
        - The API call includes additional query parameters to control agent behavior and response formatting.
        - Detailed debug logging is performed to track the request and response data.
        - Exceptions are caught, logged, and result in an empty string being returned.
    """
    """Call the external API endpoint to process the prompt."""
    session_id = config.get("session_id")
    agent_id = config.get("agent_id")
    url = f"{aiml_service_url}/chat/agent/{session_id}"
    
    try:
        log.debug(f"Making API call to {url}")
        log.debug(f"Session ID: {session_id}, Agent ID: {agent_id}")
        log.debug(f"Prompt: {prompt}")
        
        payload = {"message": prompt}
        params = {
            "agent_id": agent_id,
            "use_rag": "True",
            "stream": "False",
            "include_rich_response": "False"
        }
        
        log.debug(f"Request params: {params}")
        
        # Use a custom timeout with read disabled
        custom_timeout = httpx.Timeout(connect=60.0, read=None, write=60.0, pool=60.0)
        
        response = await client.post(
            url, 
            json=payload, 
            params=params,
            timeout=custom_timeout
        )
        log.debug(f"API Response status: {response.status_code}")
        
        response.raise_for_status()
        data = response.json()
        log.debug(f"API Response data: {data}")
        
        if not data.get("response"):
            log.warning("API returned empty response")
            return ""
            
        return data.get("response", "")
    except Exception as e:
        log.error(f"Error calling API: {e}")
        log.error(f"Traceback:\n{traceback.format_exc()}")
        return ""

#? Helper to format tweet text -----------------------------------------------------
def format_tweet(content: str) -> str:
    """
    Format the given text into a tweet-sized message.

    Parameters:
        content (str): The original text content to be formatted as a tweet.

    Returns:
        str: A string no longer than 280 characters. If the original content is within the limit,
             it is returned unchanged. If it exceeds 280 characters, the function attempts to truncate
             the text intelligently by:
             - Searching for the last period ('.') within the first 277 characters to end at a complete sentence.
             - If no period is found, searching for the last space within the same range.
             - If a suitable breakpoint is found, returning the content up to that point.
             - If no breakpoint is found, truncating directly at 277 characters and appending an ellipsis.

    Behavior:
        This function ensures that the output is appropriately trimmed for Twitter's character limit,
        prioritizing natural sentence breaks when possible to maintain readability.
    """
    """Format content into a tweet-sized message."""
    if len(content) <= 280:
        return content
    bp = content[:277].rfind('.')
    if bp == -1:
        bp = content[:277].rfind(' ')
    return content[:bp + 1] if bp != -1 else content[:277] + "..."

#? Main function to generate and optionally post a tweet ---------------------------
async def generate_and_post_tweet(post_to_twitter: bool = True, client: httpx.AsyncClient = None) -> Dict[str, Any]:
    """
    Generate a tweet in Vitalik's style via an API call and optionally post it to Twitter.
    This asynchronous function performs the following steps:
    1. Selects a tweet style and seed topic from the configuration.
    2. Constructs a prompt using the chosen style and topic.
    3. Calls an external API with the prompt to generate tweet content.
    4. Formats the API response to produce a tweet.
    5. Optionally posts the tweet to Twitter if the `post_to_twitter` flag is True.
    6. Returns a dictionary containing the generated tweet, topic, style, character count, and,
        if applicable, the Twitter response.
    7. Handles and logs any exceptions, returning a dictionary with an error message in such cases.
    Parameters:
         post_to_twitter (bool): Optional; if True, the generated tweet will be posted to Twitter. Defaults to True.
         client (httpx.AsyncClient, optional): An asynchronous HTTP client to be used for making API calls.
    Returns:
         dict: A dictionary with the following keys:
              - "tweet": The formatted tweet string.
              - "topic": The topic used for generating the tweet.
              - "style": The style selected for the tweet.
              - "character_count": The number of characters in the tweet.
              - "twitter_response": (Optional) The response from the Twitter API after posting the tweet.
              - "error": (Optional) An error message if an exception occurs during execution.
    """
    """Generate a tweet in Vitalik's style via an API call and optionally post it."""
    try:
        style = random.choice(config.get("tweet_styles", ["future_prediction"]))
        seed_topic = random.choice(config.get("seed_topics", ["Ethereum scaling solutions"]))
        
        log.debug(f"Selected style: {style}")
        log.debug(f"Selected topic: {seed_topic}")
        
        prompt = (f"Write a tweet in the style of Vitalik Buterin ({style}) about "
                f"{seed_topic}. Use a mix of technical insight and philosophical observation."
                f"Make sure the tweet is no longer than 280 characters.")
        
        tweet_response = await call_api(prompt, client)
        if not tweet_response:
            log.error("Received empty response from API")
            return {"error": "Empty API response", "topic": seed_topic, "style": style}
            
        tweet = format_tweet(tweet_response)
        result = {
            "tweet": tweet,
            "topic": seed_topic,
            "style": style,
            "character_count": len(tweet)
        }
        
        if post_to_twitter:
            log.debug("Attempting to post tweet to Twitter")
            result["twitter_response"] = post_tweet(tweet)
            
        return result
    except Exception as e:
        log.error(f"Error in generate_and_post_tweet: {e}")
        log.error(f"Traceback:\n{traceback.format_exc()}")
        return {"error": str(e)}

#? Main async entry point ----------------------------------------------------------
async def main():
    # Use a custom timeout with read disabled
    custom_timeout = httpx.Timeout(connect=60.0, read=None, write=60.0, pool=60.0)
    limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
    
    async with httpx.AsyncClient(timeout=custom_timeout, limits=limits) as client:
        result = await generate_and_post_tweet(post_to_twitter=True, client=client)
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
    # Parse command-line argument for configuration file
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=str, default='config.json', help='Path to configuration JSON file')
    args = parser.parse_args()

    # Initialize globals using the provided config file path
    global config, log
    config = UltraConfig(args.config)
    log = logger('agent_log', 
                filename='debug/chat.log', 
                include_extra_info=config.get("logging.include_extra_info", False), 
                write_to_file=config.get("logging.write_to_file", False), 
                log_level=config.get("logging.development_level", "DEBUG") if environment == 'development' else config.get("logging.production_level", "INFO"))

    asyncio.run(main())