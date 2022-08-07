import os
import sys

from dotenv import load_dotenv

load_dotenv()

# ==== bot config constants / env vars ====
TESTING = os.getenv("TESTING") == "True" or "test" in sys.argv
TOKEN = (
    os.getenv("LABYRINTHIAN_DOT_DEV_TOKEN")
    if TESTING
    else os.getenv("LABYRINTHIAN_TOKEN")
)

# ENVIRONMENT = os.getenv("ENVIRONMENT", "production" if not TESTING else "development")
OWNER_ID = os.getenv("DISCORD_OWNER_USER_ID", 0).split()
# slash command test guilds - these only apply in development anyway, so hardcoded
COMMAND_TEST_GUILD_IDS = [
    951225215801757716,  # Star of Helvetica
    # 788527785844801549,  # the pond
]
# ---- mongo/redis ----
MONGO_URL = os.getenv("MONGO_URL")
MONGODB_SERVERDB_NAME = os.getenv("MONGODB_SERVERDB_NAME")
MONGODB_TESTINGDB_NAME = os.getenv("MONGODB_TESTINGDB_NAME")

# ---- user ----
DEFAULT_PREFIX = os.getenv("DEFAULT_PREFIX", "!")

# ---- character sheets ---
# NO_DICECLOUD = os.environ.get("NO_DICECLOUD", "DICECLOUD_USER" not in os.environ)
# DICECLOUD_USER = os.getenv("DICECLOUD_USER")
# DICECLOUD_PASS = os.getenv("DICECLOUD_PASS", "").encode()
# DICECLOUD_API_KEY = os.getenv("DICECLOUD_TOKEN")

# GOOGLE_SERVICE_ACCOUNT = os.getenv("GOOGLE_SERVICE_ACCOUNT")  # optional - if not supplied, uses avrae-google.json
