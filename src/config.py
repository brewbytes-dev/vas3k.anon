import os
from dotenv import load_dotenv

# Load the environment variables from the .env file
load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
# SENTRY_DSN = os.getenv('SENTRY_DSN')
REDIS_URL = os.getenv('REDIS_URL')
DATABASE_URL = os.getenv('DATABASE_URL')
DEVELOPER = os.getenv('DEVELOPER_ID')
SEX_CHAT_ID = os.getenv('SEX_CHAT_ID')
