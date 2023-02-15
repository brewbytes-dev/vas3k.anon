import os
from dotenv import load_dotenv

# Load the environment variables from the .env file
load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
REDIS_URL = os.getenv('REDIS_URL')
DEVELOPER = os.getenv('DEVELOPER_ID')
CHAT_ID = os.getenv('CHAT_ID')