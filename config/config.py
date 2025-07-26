import os
from dotenv import load_dotenv

load_dotenv()

# Configuration for Azure Bot App
AZURE_BOT_APP_CONFIG = {
    "azure_bot_app_id" : os.getenv("AZURE_BOT_APP_ID"),
    "azure_app_bot_password" : os.getenv("AZURE_BOT_APP_PASSWORD")
}