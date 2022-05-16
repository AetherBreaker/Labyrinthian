import disnake
import logging
import os
from disnake.ext import commands
from dotenv import load_dotenv
import pymongo
from pymongo.errors import InvalidName

logging.basicConfig(level=logging.DEBUG)

intents = disnake.Intents.default()
intents.members = True
intents.message_content = True

load_dotenv()

extensions = [
	"badgelogging.badgelog"
]

bot = commands.Bot(
	command_prefix="'",
	test_guilds=[915674780303249449, 951225215801757716],
	sync_commands_debug=True,
	intents=intents,
	owner_ids=['200632489998417929', '136583737931595777']
)

@bot.slash_command(description="Responds with 'World'")
async def hello(inter):
	await inter.response.send_message("World")

@bot.event
async def on_ready():
	print(f'We have logged in as {bot.user}')

for ext in extensions:
	bot.load_extension(ext)

bot.run(os.getenv('TOKEN'))