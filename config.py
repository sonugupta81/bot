import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_USERNAME = os.getenv("OWNER_USERNAME", "")
if OWNER_USERNAME:
    OWNER_USERNAME = OWNER_USERNAME.replace("@", "").lower()

EXTERNAL_LINK = "https://www.bbgg6688.com/?invitationCode=7466367541"
