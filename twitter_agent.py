import asyncio
import os
import random
from typing import List, Dict, Any
import tweepy
from dotenv import load_dotenv

from vitalik import VitalikAgent

# Load environment variables
load_dotenv()

class TwitterAPI:
    def __init__(self):
        """Initialize Twitter API with credentials from environment variables"""
        self.client = tweepy.Client(
            consumer_key=os.getenv('TWITTER_API_KEY'),
            consumer_secret=os.getenv('TWITTER_API_SECRET'),
            access_token=os.getenv('TWITTER_ACCESS_TOKEN'),
            access_token_secret=os.getenv('TWITTER_ACCESS_TOKEN_SECRET'),
            bearer_token=os.getenv('TWITTER_BEARER_TOKEN')
        )

    def post_tweet(self, text: str) -> Dict:
        """Post a tweet and return the response"""
        try:
            response = self.client.create_tweet(text=text)
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

class VitalikTwitterAgent:
    def __init__(self):
        self.vitalik_agent = VitalikAgent()
        self.twitter_api = TwitterAPI()
        self.tweet_styles = [
            "technical_insight",
            "philosophical_observation",
            "future_prediction",
            "current_analysis",
            "historical_comparison"
        ]

    async def _get_random_topic(self) -> str:
        """Get a random topic by sampling from vector DBs"""
        try:
            db_choice = random.choice(['technical', 'blog', 'temporal'])
            
            seed_queries = {
                'technical': "ethereum technical concepts",
                'blog': "ethereum development thoughts",
                'temporal': "ethereum recent discussions"
            }
            
            if db_choice == 'technical':
                results = await self.vitalik_agent._search_technical_db(seed_queries[db_choice], n_results=5)
            elif db_choice == 'blog':
                results = await self.vitalik_agent._search_blog_db(seed_queries[db_choice], n_results=5)
            else:
                results = await self.vitalik_agent._search_temporal_db(seed_queries[db_choice], n_results=5)
            
            if results:
                result = random.choice(results)
                topic_prompt = f"""Extract a specific, focused topic for discussion from this content. 
                Make it concise (2-4 words) and technical. Content: {result['content']}"""
                
                topic_response = await self.vitalik_agent.query(topic_prompt)
                return topic_response['response']
            
            return "ethereum scaling solutions"  # fallback topic
            
        except Exception as e:
            print(f"Error getting random topic: {str(e)}")
            return "ethereum development"

    async def _get_topic_insights(self, topic: str) -> Dict[str, Any]:
        """Get deep insights on a topic from the base Vitalik agent"""
        result = await self.vitalik_agent.query(topic)
        return result

    def _format_tweet(self, content: str) -> str:
        """Format content into a tweet-sized message"""
        if len(content) <= 280:
            return content
        
        breakpoint = content[:277].rfind('.')
        if breakpoint == -1:
            breakpoint = content[:277].rfind(' ')
        
        if breakpoint == -1:
            return content[:277] + "..."
        
        return content[:breakpoint + 1]

    def _generate_tweet_prompt(self, topic: str, style: str, context: Dict[str, Any] = None) -> str:
        """Generate a specific prompt based on topic, style, and available context"""
        base_prompts = {
            "technical_insight": "Share a technical insight about {topic} that's not commonly known",
            "philosophical_observation": "What's a non-obvious philosophical implication of {topic}?",
            "future_prediction": "What's an unexpected way {topic} might evolve in the future?",
            "current_analysis": "What's your unique perspective on the current state of {topic}?",
            "historical_comparison": "How has your thinking about {topic} evolved over time?"
        }
        
        base_prompt = base_prompts[style].format(topic=topic)
        
        if context and 'sources' in context:
            relevant_sources = []
            for db_type, results in context['sources'].items():
                if results:
                    relevant_sources.extend([r['content'] for r in results[:2]])
            
            if relevant_sources:
                context_prompt = f"\n\nConsider this context: {' '.join(relevant_sources)}"
                base_prompt += context_prompt
        
        return base_prompt

    async def generate_and_post_tweet(self, post_to_twitter: bool = False) -> Dict[str, Any]:
        """Generate a random tweet in Vitalik's style and optionally post it"""
        try:
            # Get a random topic from vector DBs
            topic = await self._get_random_topic()
            print(f"Selected topic: {topic}")
            
            # Randomly select style
            style = random.choice(self.tweet_styles)
            print(f"Selected style: {style}")
            
            # Get initial insights
            insights = await self._get_topic_insights(topic)
            
            # Generate the specific prompt with context
            prompt = self._generate_tweet_prompt(topic, style, insights.get('context'))
            
            # Get final tweet content
            tweet_response = await self._get_topic_insights(prompt)
            raw_tweet = tweet_response["response"]
            
            # Format as a tweet
            tweet = self._format_tweet(raw_tweet)

            result = {
                "tweet": tweet,
                "topic": topic,
                "style": style,
                "character_count": len(tweet)
            }

            # Post to Twitter if requested
            if post_to_twitter:
                twitter_response = self.twitter_api.post_tweet(tweet)
                result["twitter_response"] = twitter_response
            
            return result
            
        except Exception as e:
            print(f"Error generating tweet: {str(e)}")
            return {
                "error": str(e),
                "status": "failed"
            }

async def main():
    try:
        twitter_agent = VitalikTwitterAgent()
        print("Generating Vitalik-style tweet...\n")
        
        # Set post_to_twitter=True to actually post the tweet
        result = await twitter_agent.generate_and_post_tweet(post_to_twitter=False)
        
        if "tweet" in result:
            print("Generated Tweet:")
            print("-" * 40)
            print(result["tweet"])
            print("-" * 40)
            print(f"\nTopic: {result['topic']}")
            print(f"Style: {result['style']}")
            print(f"Character count: {result['character_count']}")
            
            if "twitter_response" in result:
                print("\nTwitter Response:")
                print(result["twitter_response"])
        else:
            print("Error:", result.get("error", "Unknown error occurred"))
        
    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())