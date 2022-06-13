import abc
from typing import TYPE_CHECKING, List, Optional, Type, TypeVar
import disnake
from disnake.ext import commands
from pymongo.typings import _DocumentType
from utils.settings.guild import ServerSettings

from utils.ui.menu import MenuBase


_LabyrinthianT = TypeVar("_LabyrinthianT", bound=disnake.Client)
if TYPE_CHECKING:
    from bot import Labyrinthian

    _LabyrinthianT = Labyrinthian


class SettingsMenuBase(MenuBase, abc.ABC):
    __menu_copy_attrs__ = ("bot", "settings", "guild")
    bot: _LabyrinthianT
    settings: ServerSettings
    guild: disnake.Guild
    
    async def commit_settings(self):
        """Commits any changed guild settings to the db."""
        await self.settings.commit(self.bot.dbcache)


class SettingsNav(SettingsMenuBase):
    @classmethod
    async def new(cls, bot: _LabyrinthianT, owner: disnake.User, settings: ServerSettings, guild: disnake.Guild):
        inst = cls(owner=owner)
        inst.bot = bot
        inst.settings = settings
        inst.guild = guild
        return inst
    
    @property
    def embed_main(self):
        emb = (
            disnake.Embed()
            .add_field()
            .add_field()
        )
        return emb

    @disnake.ui.button(
        emoji = "🗿",
        style=disnake.ButtonStyle.primary,
        label="Auction House Settings"
    )
    async def auction_house_settings(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        
        await self.defer_to(AuctionSettingsView, inter)

    @disnake.ui.button(
        style=disnake.ButtonStyle.primary,
        label="Badgelog Settings"
    )
    async def badgelog_settings(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        
        await self.defer_to(BadgelogSettingsView, inter)

    @disnake.ui.button(
        style=disnake.ButtonStyle.primary,
        label="Bot Settings"
    )
    async def bot_settings(self, button:disnake.ui.Button, inter: disnake.MessageInteraction):
        await self.defer_to(BotSettingsView, inter)


class AuctionSettingsView(SettingsMenuBase):
    def __init__(self, bot: _LabyrinthianT, settings: _DocumentType):
        super().__init__(timeout=180)


class BadgelogSettingsView(SettingsMenuBase):
    def __init__(self, bot: _LabyrinthianT, settings: _DocumentType):
        super().__init__(timeout=180)


class BotSettingsView(SettingsMenuBase):
    def __init__(self, bot: _LabyrinthianT, settings: _DocumentType):
        super().__init__(timeout=180)

