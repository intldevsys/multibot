from dotenv import load_dotenv
import os
from decouple import config

# Load .env file
load_dotenv()

# Bot Configuration
BOT_TOKEN = config("BOT_TOKEN", default="")
API_ID = config("API_ID", default=0, cast=int)
API_HASH = config("API_HASH", default="")
OWNER_ID = config("OWNER_ID", default=0, cast=int)

# Admin Configuration
ADMINS = []
for x in (config("ADMINS", default="").split()):
    try:
        ADMINS.append(int(x))
    except ValueError:
        pass
ADMINS.append(OWNER_ID)

# Database Configuration
DATABASE_URI = config("DATABASE_URI", default="mongodb://localhost:27017")
DATABASE_NAME = config("DATABASE_NAME", default="telegram_bot")

# LLM Configuration
ANTHROPIC_API_KEY = config("ANTHROPIC_API_KEY", default="")
OPENAI_API_KEY = config("OPENAI_API_KEY", default="")
COHERE_API_KEY = config("COHERE_API_KEY", default="")
GOOGLE_API_KEY = config("GOOGLE_API_KEY", default="")
DEEPSEEK_API_KEY = config("DEEPSEEK_API_KEY", default="")
QWEN_API_KEY = config("QWEN_API_KEY", default="")

# News API Configuration
NEWS_API_KEY = config("NEWS_API_KEY", default="")
NEWSDATA_API_KEY = config("NEWSDATA_API_KEY", default="")
GNEWS_API_KEY = config("GNEWS_API_KEY", default="")
GUARDIAN_API_KEY = config("GUARDIAN_API_KEY", default="")

# Cryptocurrency API Configuration
COINMARKETCAP_API_KEY = config("COINMARKETCAP_API_KEY", default="")
COINGECKO_API_KEY = config("COINGECKO_API_KEY", default="")

# X/Twitter API Configuration
TWITTER_BEARER_TOKEN = config("TWITTER_BEARER_TOKEN", default="")
TWITTER_API_KEY = config("TWITTER_API_KEY", default="")
TWITTER_API_SECRET = config("TWITTER_API_SECRET", default="")

# Rate Limiting Configuration
RATE_LIMIT_REQUESTS = config("RATE_LIMIT_REQUESTS", default=3, cast=int)
RATE_LIMIT_WINDOW = config("RATE_LIMIT_WINDOW", default=86400, cast=int)  # 24 hours

# Bot Features Configuration
CHAT_HISTORY_DAYS = config("CHAT_HISTORY_DAYS", default=20, cast=int)
MAX_INTERACTION_MESSAGES = config("MAX_INTERACTION_MESSAGES", default=20, cast=int)
MAX_RESULTS_NON_ADMIN = config("MAX_RESULTS_NON_ADMIN", default=10, cast=int)
MAX_TWEETS_RESULTS = config("MAX_TWEETS_RESULTS", default=5, cast=int)

# File Configuration
DOWNLOADS_PATH = config("DOWNLOADS_PATH", default="downloads/")
LOGS_PATH = config("LOGS_PATH", default="logs/")

# Ensure directories exist
os.makedirs(DOWNLOADS_PATH, exist_ok=True)
os.makedirs(LOGS_PATH, exist_ok=True)