import os
from dotenv import load_dotenv

#* Get environment
load_dotenv(".env")
environment = os.getenv("ENVIRONMENT", "development")  # Default to 'development'

#* laod proper environment file
dotenv_file = f".env.{environment}"
load_dotenv(dotenv_file)

#! Server URLs -----------------------------------------------
#* Service URLs ---------------------------------------------
aiml_service_url = os.getenv("AIML_SERVICE_URL", "http://localhost:8000")

#! Keys -----------------------------------------------------
#* Tritter ---------------------------------------------------
twitter_api_key = os.getenv("TWITTER_API_KEY")
twitter_api_secret = os.getenv("TWITTER_API_SECRET")
twitter_access_token = os.getenv("TWITTER_ACCESS_TOKEN")
twitter_access_token_secret = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")
twitter_bearer_token = os.getenv("TWITTER_BEARER_TOKEN")
