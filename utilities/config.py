import os
import sys
from dotenv import load_dotenv

load_dotenv()

# ==== bot config constants / env vars ====
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
TESTING = os.getenv("TESTING") or "test" in sys.argv
#ENVIRONMENT = os.getenv("ENVIRONMENT", "production" if not TESTING else "development")
OWNER_ID = os.getenv("DISCORD_OWNER_USER_ID", 0)
# slash command test guilds - these only apply in development anyway, so hardcoded
COMMAND_TEST_GUILD_IDS = (
    [
		915674780303249449,	#Gamering
		951225215801757716	#Star of Helvetica
    ]
    if TESTING
    else None
)

# ---- mongo/redis ----
MONGO_URL = os.getenv("MONGO_URL")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME")
MONGODB_SERVERDB_NAME = os.getenv("MONGODB_SERVERDB_NAME")
REDIS_URL = os.getenv("REDIS_URL")
REDIS_DB_NUM = int(os.getenv("REDIS_DB_NUM", 0))

# ---- user ----
DEFAULT_PREFIX = os.getenv("DEFAULT_PREFIX", "!")

# ---- character sheets ---
#NO_DICECLOUD = os.environ.get("NO_DICECLOUD", "DICECLOUD_USER" not in os.environ)
#DICECLOUD_USER = os.getenv("DICECLOUD_USER")
#DICECLOUD_PASS = os.getenv("DICECLOUD_PASS", "").encode()
#DICECLOUD_API_KEY = os.getenv("DICECLOUD_TOKEN")

#GOOGLE_SERVICE_ACCOUNT = os.getenv("GOOGLE_SERVICE_ACCOUNT")  # optional - if not supplied, uses avrae-google.json