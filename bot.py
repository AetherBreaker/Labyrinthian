import asyncio
import logging
import os
import traceback
from typing import Union

import disnake
import motor.motor_asyncio
from aiohttp import ClientOSError, ClientResponseError
from disnake.errors import Forbidden, HTTPException, InvalidData, NotFound
from disnake.ext import commands
from disnake.ext.commands.errors import CommandInvokeError

from cogs.auction.auction_constructor import ConstSender
from utils import MongoCache, config
from utils.models.errors import LabyrinthianException
from utils.settings.guild import ServerSettings

if config.TESTING_VAR == "True":
    import sys

    sys.dont_write_bytecode = True

logging.basicConfig(level=logging.INFO)

intents = disnake.Intents.all()

cwd = os.getcwd()

extensions = (
    "cogs.badgelog.badgelogcog",
    "cogs.administrative.configcog",
    "cogs.auction.auctioncog",
)

# async def get_prefix(bot: commands.Bot, message: disnake.Message):
#     """Redefines Disnake get_prefix function to redirect get_guild_prefix when running in servers."""
#     if not message.guild:
#         return commands.when_mentioned_or(config.DEFAULT_PREFIX)(bot, message)
#     guildprefix = await bot.get_guild_prefix(message.guild)
#     return commands.when_mentioned_or(guildprefix)(bot, message)


class Labyrinthian(commands.Bot):
    def __init__(
        self, prefix: str, help_command: commands.HelpCommand = None, description: str = None, **options  # type: ignore
    ) -> None:
        super().__init__(
            prefix,
            help_command=help_command,
            description=description,
            test_guilds=config.COMMAND_TEST_GUILD_IDS,
            sync_commands_debug=config.TESTING,
            owner_ids=config.OWNER_ID,
            **options,
        )
        self.persistent_views_added = False

        # databases
        self.mclient = motor.motor_asyncio.AsyncIOMotorClient(config.MONGO_URL)
        self.sdb: motor.motor_asyncio.AsyncIOMotorDatabase = self.mclient[
            config.MONGODB_SERVERDB_NAME
        ]
        self.dbcache = MongoCache.MongoCache(self, cwd, maxsize=50, ttl=20)
        self.charcache = MongoCache.CharlistCache(self, maxsize=50, ttl=20)

    async def get_server_settings(self, guild_id: str) -> ServerSettings:
        if not isinstance(guild_id, str):
            guild_id = str(guild_id)
        server_settings = await ServerSettings.for_guild(self.dbcache, guild_id)
        return server_settings

    # async def get_guild_prefix(self, guild: disnake.Guild) -> str:
    #     guild_id = str(guild.id)
    #     if guild_id in self.prefixes:
    #         return self.prefixes.get(guild_id, config.DEFAULT_PREFIX)
    #     # load from db and cache
    #     gp_obj = await self.sdb['srvconf'].find_one({"guild_id": guild_id})
    #     if gp_obj.has_key("prefix"):
    #         gp = config.DEFAULT_PREFIX
    #     else:
    #         gp = gp_obj['prefix']
    #     self.prefixes[guild_id] = gp
    #     return gp


bot = Labyrinthian(
    prefix="'",
    testing=config.TESTING,
    intents=intents,
    reload=True if config.TESTING_VAR == "True" else False,
)


@bot.event
async def on_ready():
    if not bot.persistent_views_added:
        constviews = await bot.sdb["srvconf"].find({}).to_list(None)
        for x in constviews:
            if "constid" in x:
                try:
                    channel, message = x["constid"]
                    channel: Union[
                        disnake.abc.GuildChannel, disnake.abc.Messageable
                    ] = await bot.fetch_channel(
                        int(channel)  # type: ignore
                    )  # type: ignore
                    message = await channel.fetch_message(int(message))  # type: ignore
                    bot.add_view(ConstSender(), message_id=message.id)
                except (InvalidData, HTTPException, NotFound, Forbidden) as e:
                    print(f"{e} trying again")
                    try:
                        channel, message = x["constid"]
                        channel: Union[
                            disnake.abc.GuildChannel, disnake.abc.Messageable
                        ] = await bot.fetch_channel(
                            int(channel)
                        )  # type: ignore
                        message = await channel.fetch_message(int(message))  # type: ignore
                        bot.add_view(ConstSender(), message_id=message.id)
                    except (InvalidData, HTTPException, NotFound, Forbidden) as e:
                        print(f"{e} deleting view IDs")
                        x.pop("constid")
                        await bot.sdb["srvconf"].replace_one(
                            {"guild": x["guild"]}, x, True
                        )
        bot.persistent_views_added = True


@bot.event
async def on_slash_command_error(inter: disnake.Interaction, error):
    if isinstance(error, commands.CommandNotFound):
        return

    elif isinstance(error, LabyrinthianException):
        return await inter.author.send(str(error))

    elif isinstance(
        error, (commands.UserInputError, commands.NoPrivateMessage, ValueError)
    ):
        return await inter.send(
            f"Error: {str(error)}\nUse `{inter.prefix}help "  # type: ignore
            + inter.application_command.qualified_name  # type: ignore
            + "` for help."
        )

    elif isinstance(error, commands.CheckFailure):
        msg = str(error) or "You are not allowed to run this command."
        return await inter.send(f"Error: {msg}")

    elif isinstance(error, commands.CommandOnCooldown):
        return await inter.send(
            "This command is on cooldown for {:.1f} seconds.".format(error.retry_after)
        )

    elif isinstance(error, commands.MaxConcurrencyReached):
        return await inter.send(str(error))

    elif isinstance(error, CommandInvokeError):
        original = error.original

        if isinstance(original, LabyrinthianException):
            return await inter.author.send(str(original))

        elif isinstance(original, Forbidden):
            try:
                return await inter.author.send(
                    "Error: I am missing permissions to run this command. "
                    f"Please make sure I have permission to send messages to <#{inter.channel.id}>."
                )
            except HTTPException:
                try:
                    return await inter.send(
                        "Error: I cannot send messages to this user."
                    )
                except HTTPException:
                    return

        elif isinstance(original, NotFound):
            return await inter.send(
                "Error: I tried to edit or delete a message that no longer exists."
            )

        elif isinstance(
            original, (ClientResponseError, asyncio.TimeoutError, ClientOSError)
        ):
            return await inter.send("Error in Discord API. Please try again.")

        elif isinstance(original, HTTPException):
            if original.response.status == 400:
                return await inter.send(
                    f"Error: Message is too long, malformed, or empty.\n{original.text}"
                )
            elif 499 < original.response.status < 600:
                return await inter.send(
                    "Error: Internal server error on Discord's end. Please try again."
                )

    else:
        return await inter.author.send(f"{error}\n```py\n{traceback.format_exc()}```")


@bot.event
async def on_error(event: str, *args, **kwargs):
    for arg in args:
        if isinstance(arg, disnake.Interaction):
            await arg.author.send(f"```py\n{traceback.format_exc()}```")
        elif isinstance(arg, commands.Context):
            await arg.author.send(f"```py\n{traceback.format_exc()}```")


for ext in extensions:
    bot.load_extension(ext)

bot.run(config.TOKEN)
