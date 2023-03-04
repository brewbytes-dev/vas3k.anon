import os
from dotenv import load_dotenv

# Load the environment variables from the .env file
load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
SENTRY_DSN = os.getenv('SENTRY_DSN')
REDIS_URL = os.getenv('REDIS_URL')
CHAT_ID = os.getenv('CHAT_ID')
CHAT_AAA_ID = os.getenv('CHAT_AAA_ID')
CHAT_NAME = os.getenv('CHAT_NAME')
BOT_NAME = os.getenv('BOT_NAME')
