import disnake
import logging
from disnake.ext import commands
import motor.motor_asyncio
from utilities import config
from utilities.functions import confirm
from utilities import checks

logging.basicConfig(level=logging.INFO)

intents = disnake.Intents.default()
intents.members = True
intents.message_content = True
intents.presences = True

extensions = [
	"badgelogging.badgelog",
	"utilities.customization"
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
		gp_obj = await self.sdb['srvconf'].find_one({"guild_id": guild_id})
		if gp_obj.has_key("prefix"):
			gp = config.DEFAULT_PREFIX
		else:
			gp = gp_obj['prefix']
		self.prefixes[guild_id] = gp
		return 

bot = Labyrinthian(
	prefix="'",
	testing=config.TESTING,
	intents=intents,
	reload=True
)

@bot.event
async def on_ready():
	print(f'We have logged in as {bot.user}')

@bot.command()
@commands.guild_only()
async def prefix(ctx, prefix: str = None):
	"""
	Sets the bot's prefix for this server.
	You must have Manage Server permissions or a role called "Bot Admin" to use this command. Due to a possible Discord conflict, a prefix beginning with `/` will require confirmation.
	Forgot the prefix? Reset it with "@Labyrinthian#1476 prefix '".
	"""
	guild_id = str(ctx.guild.id)
	if prefix is None:
		current_prefix = await bot.get_guild_prefix(ctx.guild)
		return await ctx.send(f"My current prefix is: `{current_prefix}`.")

	if not checks._role_or_permissions(ctx, lambda r: r.name.lower() == "bot admin", manage_guild=True):
		return await ctx.send("You do not have permissions to change the guild prefix.")

	# Check for Discord Slash-command conflict
	if prefix.startswith("/"):
		if not await confirm(
			ctx,
			"Setting a prefix that begins with / may cause issues. "
			"Are you sure you want to continue? (Reply with yes/no)",
		):
			return await ctx.send("Ok, cancelling.")
	else:
		if not await confirm(
			ctx,
			f"Are you sure you want to set my prefix to `{prefix}`? This will affect "
			f"everyone on this server! (Reply with yes/no)",
		):
			return await ctx.send("Ok, cancelling.")

	# insert into cache
	bot.prefixes[guild_id] = prefix

	# update db
	await bot.sdb['srvconf'].update_one({"guild": guild_id}, {"$set": {"prefix": prefix}}, upsert=True)

	await ctx.send(f"Prefix set to `{prefix}` for this server.")

for ext in extensions:
	bot.load_extension(ext)

@bot.slash_command(description="Reload bot extensions")
async def reload(inter, extension: str = commands.Param(choices=extensions)):
	if str(inter.author.id) in bot.owner_ids:
		await inter.response.send_message(f"Reloading the {extension} extension.")
		bot.reload_extension(extension)
	else:
		await inter.response.send_message("You are not the owner of this bot")

bot.run(config.TOKEN)