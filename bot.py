import asyncio
from aiohttp import ClientOSError, ClientResponseError
import disnake
import logging
from disnake.ext import commands
import motor.motor_asyncio
from utilities import config
from utilities.errors import LabyrinthianException
from utilities.functions import confirm
from utilities import checks
from disnake.errors import Forbidden, HTTPException, InvalidArgument, NotFound
from disnake.ext import commands
from disnake.ext.commands.errors import CommandInvokeError

logging.basicConfig(level=logging.INFO)

intents = disnake.Intents.default()
intents.members = True
intents.message_content = True
intents.presences = True

extensions = (
    "badgelog.main",
    "settings.customization"
)

async def get_prefix(bot: commands.Bot, message: disnake.Message):
    if not message.guild:
        return commands.when_mentioned_or(config.DEFAULT_PREFIX)(bot, message)
    gp = await bot.get_guild_prefix(message.guild)
    return commands.when_mentioned_or(gp)(bot, message)

class Labyrinthian(commands.Bot):
    def __init__(self, prefix: str, help_command=None, description=None, **options):
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

        #misc caches
        self.prefixes = dict()
        self.muted = set()

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
        return gp

bot = Labyrinthian(
    prefix="'",
    testing=config.TESTING,
    intents=intents,
    reload=True
)

@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return

    elif isinstance(error, LabyrinthianException):
        return await ctx.send(str(error))

    elif isinstance(error, (commands.UserInputError, commands.NoPrivateMessage, ValueError)):
        return await ctx.send(
            f"Error: {str(error)}\nUse `{ctx.prefix}help " + ctx.command.qualified_name + "` for help."
        )

    elif isinstance(error, commands.CheckFailure):
        msg = str(error) or "You are not allowed to run this command."
        return await ctx.send(f"Error: {msg}")

    elif isinstance(error, commands.CommandOnCooldown):
        return await ctx.send("This command is on cooldown for {:.1f} seconds.".format(error.retry_after))

    elif isinstance(error, commands.MaxConcurrencyReached):
        return await ctx.send(str(error))

    elif isinstance(error, CommandInvokeError):
        original = error.original

        if isinstance(original, LabyrinthianException):
            return await ctx.send(str(original)) 

        elif isinstance(original, Forbidden):
            try:
                return await ctx.author.send(
                    "Error: I am missing permissions to run this command. "
                    f"Please make sure I have permission to send messages to <#{ctx.channel.id}>."
                )
            except HTTPException:
                try:
                    return await ctx.send(f"Error: I cannot send messages to this user.")
                except HTTPException:
                    return

        elif isinstance(original, NotFound):
            return await ctx.send("Error: I tried to edit or delete a message that no longer exists.")

        elif isinstance(original, (ClientResponseError, InvalidArgument, asyncio.TimeoutError, ClientOSError)):
            return await ctx.send("Error in Discord API. Please try again.")

        elif isinstance(original, HTTPException):
            if original.response.status == 400:
                return await ctx.send(f"Error: Message is too long, malformed, or empty.\n{original.text}")
            elif 499 < original.response.status < 600:
                return await ctx.send("Error: Internal server error on Discord's end. Please try again.")

@bot.event
async def on_slash_command_error(inter, error):
    if isinstance(error, commands.CommandNotFound):
        return

    elif isinstance(error, LabyrinthianException):
        return await inter.send(str(error))

    elif isinstance(error, (commands.UserInputError, commands.NoPrivateMessage, ValueError)):
        return await inter.send(
            f"Error: {str(error)}\nUse `{inter.prefix}help " + inter.command.qualified_name + "` for help."
        )

    elif isinstance(error, commands.CheckFailure):
        msg = str(error) or "You are not allowed to run this command."
        return await inter.send(f"Error: {msg}")

    elif isinstance(error, commands.CommandOnCooldown):
        return await inter.send("This command is on cooldown for {:.1f} seconds.".format(error.retry_after))

    elif isinstance(error, commands.MaxConcurrencyReached):
        return await inter.send(str(error))

    elif isinstance(error, CommandInvokeError):
        original = error.original

        if isinstance(original, LabyrinthianException):
            return await inter.send(str(original)) 

        elif isinstance(original, Forbidden):
            try:
                return await inter.author.send(
                    "Error: I am missing permissions to run this command. "
                    f"Please make sure I have permission to send messages to <#{inter.channel.id}>."
                )
            except HTTPException:
                try:
                    return await inter.send(f"Error: I cannot send messages to this user.")
                except HTTPException:
                    return

        elif isinstance(original, NotFound):
            return await inter.send("Error: I tried to edit or delete a message that no longer exists.")

        elif isinstance(original, (ClientResponseError, InvalidArgument, asyncio.TimeoutError, ClientOSError)):
            return await inter.send("Error in Discord API. Please try again.")

        elif isinstance(original, HTTPException):
            if original.response.status == 400:
                return await inter.send(f"Error: Message is too long, malformed, or empty.\n{original.text}")
            elif 499 < original.response.status < 600:
                return await inter.send("Error: Internal server error on Discord's end. Please try again.")

@bot.command()
@commands.guild_only()
async def prefix(ctx: commands.Context, prefix: str = None):
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
async def reload(inter: disnake.ApplicationCommandInteraction, extension: str = commands.Param(choices=extensions)):
    if str(inter.author.id) in bot.owner_ids:
        await inter.response.send_message(f"Reloading the {extension} extension.")
        bot.reload_extension(extension)
    else:
        await inter.response.send_message("You are not the owner of this bot")

bot.run(config.TOKEN)