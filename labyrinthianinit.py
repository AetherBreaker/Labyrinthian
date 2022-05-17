import disnake
import logging
import os
from disnake.ext import commands
from dotenv import load_dotenv
import pymongo
import pymongo
import motor.motor_asyncio

logging.basicConfig(level=logging.DEBUG)

intents = disnake.Intents.default()
intents.members = True
intents.message_content = True

load_dotenv()

extensions = [
	"badgelogging.badgelog"
]

class Labyrinthian(commands.Bot):
	def __init__(self, prefix, **options):
		super().__init__(
			prefix,
			test_guilds=[915674780303249449, 951225215801757716],
			sync_commands_debug=True,
			**options
		)
		self.mclient = motor.motor_asyncio.AsyncIOMotorClient(f"mongodb+srv://labyrinthadmin:{os.getenv('DBPSS')}@labyrinthdb.ng3ca.mongodb.net/?retryWrites=true&w=majority")
		self.mdb = self.mclient["helveticaDB"]
		#self.rdb = self.loop.run_until_complete(self.setup_rdb())

bot = Labyrinthian(
	prefix="'",
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