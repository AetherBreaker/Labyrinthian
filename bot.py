import asyncio
import logging
import os
import traceback
from copy import deepcopy
from typing import Optional, Union

import disnake
import motor.motor_asyncio
from aiohttp import ClientOSError, ClientResponseError
from bson import ObjectId
from disnake.errors import Forbidden, HTTPException, InvalidData, NotFound
from disnake.ext import commands
from disnake.ext.commands.errors import CommandInvokeError

from cogs.auction.auction_constructor import ConstSender
from utils import MongoCache, config
from utils.models.character import Character
from utils.models.errors import LabyrinthianException, MissingCharacterDataError
from utils.models.settings.guild import ServerSettings
from utils.models.settings.user import UserPreferences
from utils.models.xplog import XPLogBook

if config.TESTING:
    import sys

    sys.dont_write_bytecode = True

logging.basicConfig(level=logging.INFO)


# logger = logging.getLogger("disnake")
# logger.setLevel(logging.DEBUG)
# handler = logging.FileHandler(filename="disnake.log", encoding="utf-8", mode="w")
# handler.setFormatter(
#     logging.Formatter("%(asctime)s:%(levelname)s:%(name)s: %(message)s")
# )
# logger.addHandler(handler)


intents = disnake.Intents.all()

cwd = os.getcwd()

extensions = (
    "cogs.characterlog.charactercog",
    "cogs.administrative.configcog",
    "cogs.auction.auctioncog",
    "cogs.coins.coincog",
    "cogs.eventlogging.loggincog",
)


class Labyrinthian(commands.Bot):
    def __init__(
        self,
        prefix: str,
        help_command: commands.HelpCommand = None,
        description: str = None,
        **options,
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
            config.MONGODB_TESTINGDB_NAME
            if config.TESTING
            else config.MONGODB_SERVERDB_NAME
        ]
        self.dbcache = MongoCache.MongoCache(self, cwd, maxsize=50, ttl=30)
        self.charcache = MongoCache.CharlistCache(self, maxsize=50, ttl=30)

    async def get_server_settings(
        self, guild_id: str, validate: bool = True
    ) -> ServerSettings:
        data, wasnone = await ServerSettings.get_data(self, guild_id)
        if wasnone:
            settings = ServerSettings.for_guild(data)
            await settings.commit(self.dbcache)
            data = settings.dict()
        if validate:
            return ServerSettings.for_guild(data)
        else:
            return ServerSettings.no_validate(data)

    async def get_user_prefs(
        self, user_id: str, validate: bool = True
    ) -> Optional[UserPreferences]:
        data, wasnone = await UserPreferences.get_data(self, user_id)
        if wasnone:

            uprefs = UserPreferences(**data)
            await uprefs.commit(self.dbcache)
            data = uprefs.dict()
        if validate:
            return UserPreferences.parse_obj(data)
        else:
            return UserPreferences.no_validate(data)

    async def get_character(
        self, guild_id: str, user_id: str, character_name: str, validate: bool = True
    ) -> Optional[Character]:
        data = await Character.get_data(
            self, {"user": user_id, "guild": guild_id, "name": character_name}
        )
        if data is None:
            raise MissingCharacterDataError()
        if validate:
            return Character.parse_obj(data)
        else:
            return Character.no_validate(data)

    async def get_char_by_oid(
        self, oid: ObjectId, validate: bool = True
    ) -> Optional[Character]:
        data = await Character.get_data(self, {"_id": oid})
        if data is None:
            raise MissingCharacterDataError()
        if validate:
            return Character.parse_obj(data)
        else:
            return Character.no_validate(data)

    async def get_character_xplog(self, character_ref_id: ObjectId):
        return await XPLogBook.new(self.sdb, character_ref_id)


bot = Labyrinthian(
    prefix="'",
    intents=intents,
    reload=True if config.TESTING else False,
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
                    ] = await bot.fetch_channel(int(channel))
                    message = await channel.fetch_message(int(message))
                    bot.add_view(ConstSender(), message_id=message.id)
                except (InvalidData, HTTPException, NotFound, Forbidden) as e:
                    print(f"{e} trying again")
                    try:
                        channel, message = x["constid"]
                        channel: Union[
                            disnake.abc.GuildChannel, disnake.abc.Messageable
                        ] = await bot.fetch_channel(int(channel))
                        message = await channel.fetch_message(int(message))
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
        return await inter.send(str(error), ephemeral=True)

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
            return await inter.send(str(error), ephemeral=True)

        elif isinstance(original, Forbidden):
            try:
                return await inter.send(
                    "Error: I am missing permissions to run this command. "
                    f"Please make sure I have permission to send messages to <#{inter.channel.id}>."
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
        traceback.print_exc()
        return await inter.author.send(f"{error}\n```py\n{traceback.format_exc()}```")


@bot.event
async def on_error(event: str, *args, **kwargs):
    if args:
        for arg in args:
            if isinstance(arg, disnake.Interaction):
                traceback.print_exc()
                await arg.author.send(f"```py\n{traceback.format_exc()}```")
            elif isinstance(arg, commands.Context):
                traceback.print_exc()
                await arg.author.send(f"```py\n{traceback.format_exc()}```")
            elif hasattr(arg, "author"):
                try:
                    traceback.print_exc()
                    await arg.author.send(f"```py\n{traceback.format_exc()}```")
                except:
                    pass
            else:
                traceback.print_exc()
    if kwargs:
        for arg in kwargs.values:
            if isinstance(arg, disnake.Interaction):
                traceback.print_exc()
                await arg.author.send(f"```py\n{traceback.format_exc()}```")
            elif isinstance(arg, commands.Context):
                traceback.print_exc()
                await arg.author.send(f"```py\n{traceback.format_exc()}```")
            elif hasattr(arg, "author"):
                try:
                    traceback.print_exc()
                    await arg.author.send(f"```py\n{traceback.format_exc()}```")
                except:
                    pass
            else:
                traceback.print_exc()


for ext in extensions:
    bot.load_extension(ext)

bot.run(config.TOKEN)
