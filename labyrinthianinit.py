import disnake
import logging
import os
from disnake.errors import Forbidden, HTTPException, InvalidArgument, NotFound
from disnake.ext import commands
from disnake.ext.commands.errors import CommandInvokeError
import pymongo
import motor.motor_asyncio
import aioredis
from utilities import config
from utilities.redisIOAvrae import RedisIO

logging.basicConfig(level=logging.DEBUG)

intents = disnake.Intents.default()
intents.members = True
intents.message_content = True
intents.guilds = True
intents.messages = True
intents.presences = True

extensions = [
	"badgelogging.badgelog"
]

async def get_prefix(bot, message):
	if not message.guild:
		return commands.when_mentioned_or(config.DEFAULT_PREFIX)(bot, message)
	gp = await bot.get_guild_prefix(message.guild)
	return commands.when_mentioned_or(gp)(bot, message)

class Labyrinthian(commands.Bot):
	def __init__(self, prefix, help_command=None, description=None, **options):
		super().__init__(
			prefix,
			help_command=help_command,
			description=description,
			test_guilds=config.COMMAND_TEST_GUILD_IDS,
			sync_commands_debug=config.TESTING,
			owner_ids=config.OWNER_ID,
			**options
		)
		self.state = "init"
		
		#databases
		self.mclient = motor.motor_asyncio.AsyncIOMotorClient(config.MONGO_URL)
		self.mdb = self.mclient[config.MONGODB_DB_NAME]
		self.sdb = self.mclient[config.MONGODB_SERVERDB_NAME]
		#self.rdb = self.loop.run_until_complete(self.setup_rdb())

		#misc caches
		self.prefixes = dict()
		self.muted = set()

	#async def setup_rdb(self):
	#	return RedisIO(await aioredis.create_redis_pool(config.REDIS_URL, db=config.REDIS_DB_NUM))

	async def get_guild_prefix(self, guild: disnake.Guild) -> str:
		guild_id = str(guild.id)
		if guild_id in self.prefixes:
			return self.prefixes.get(guild_id, config.DEFAULT_PREFIX)
		# load from db and cache
		gp_obj = await self.sdb.prefixes.find_one({"guild_id": guild_id})
		if gp_obj is None:
			gp = config.DEFAULT_PREFIX
		else:
			gp = gp_obj.get("prefix", config.DEFAULT_PREFIX)
		self.prefixes[guild_id] = gp
		return 

bot = Labyrinthian(
	prefix=get_prefix,
	testing=config.TESTING,
	intents=intents,
)

@bot.event
async def on_ready():
	print(f'We have logged in as {bot.user}')

for ext in extensions:
	bot.load_extension(ext)

@bot.slash_command(description="Reload bot extensions", checks=[commands.is_owner()])
async def reload(inter, extension: str = commands.Param(choices=extensions)):
	await inter.response.send_message(f"Reloading the {extension} extension.")
	await bot.reload_extension(extension)

bot.run(config.TOKEN)