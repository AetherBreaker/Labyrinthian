import asyncio
import logging
import os
import traceback
from types import ModuleType
from typing import Optional, Union

import disnake
import motor.motor_asyncio
from aiohttp import ClientOSError, ClientResponseError
from disnake.errors import Forbidden, HTTPException, InvalidData, NotFound
from disnake.ext import commands
from disnake.ext.commands.common_bot_base import _is_submodule
from disnake.ext.commands.errors import CommandInvokeError

from cogs.auction.auction_constructor import ConstSender
from utils import MongoCache, config
from utils.models.errors import LabyrinthianException
from utils.models.settings.guild import ServerSettings
from utils.reload import reload_child_modules

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
    "cogs.coins.coincog",
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

    # # literally just a copy-paste from dpy, except for the `reload_submodules`` check w/ call
    # def reload_extension(
    #     self, name: str, *, package: Optional[str] = None, reload_submodules: bool = False
    # ) -> None:
    #     """Atomically reloads an extension.
    #     This replaces the extension with the same extension, only refreshed. This is
    #     equivalent to a :meth:`unload_extension` followed by a :meth:`load_extension`
    #     except done in an atomic way. That is, if an operation fails mid-reload then
    #     the bot will roll-back to the prior working state.
    #     Parameters
    #     ------------
    #     name: :class:`str`
    #         The extension name to reload. It must be dot separated like
    #         regular Python imports if accessing a sub-module. e.g.
    #         ``foo.test`` if you want to import ``foo/test.py``.
    #     package: Optional[:class:`str`]
    #         The package name to resolve relative imports with.
    #         This is required when reloading an extension using a relative path, e.g ``.foo.test``.
    #         Defaults to ``None``.
    #         .. versionadded:: 1.7
    #     reload_submodules: :class:`bool`
    #         Whether to reload the submodules loaded in the cog's module. For example,
    #         when set to `True`, reloading an extension `foo` that imports `bar` will
    #         also reload module `bar`. This makes it so that any changes made to bar.py
    #         will propagate to foo.py when foo.py is reloaded.
    #     Raises
    #     -------
    #     ExtensionNotLoaded
    #         The extension was not loaded.
    #     ExtensionNotFound
    #         The extension could not be imported.
    #         This is also raised if the name of the extension could not
    #         be resolved using the provided ``package`` parameter.
    #     NoEntryPointError
    #         The extension does not have a setup function.
    #     ExtensionFailed
    #         The extension setup function had an execution error.
    #     """

    #     name = self._resolve_name(name, package)
    #     lib: ModuleType = self._CommonBotBase__extensions.get(name)  # why is this mangled :/
    #     if lib is None:
    #         raise commands.ExtensionNotLoaded(name)

    #     if reload_submodules:
    #         reload_child_modules(lib)
    #         # TODO: redo `init_beanie` when db models are reloaded

    #     # get the previous module states from sys modules
    #     modules = {
    #         name: module
    #         for name, module in sys.modules.items()
    #         if _is_submodule(lib.__name__, name)
    #     }

    #     try:
    #         # Unload and then load the module...
    #         self._remove_module_references(lib.__name__)
    #         self._call_module_finalizers(lib, name)
    #         self.load_extension(name)
    #     except Exception:
    #         # if the load failed, the remnants should have been
    #         # cleaned from the load_extension function call
    #         # so let's load it from our old compiled library.
    #         lib.setup(self)  # type: ignore
    #         self._CommonBotBase__extensions[name] = lib

    #         # revert sys.modules back to normal and raise back to caller
    #         sys.modules.update(modules)
    #         raise


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
