import abc
from typing import TYPE_CHECKING, List, Mapping, Optional, Type, TypeVar
import disnake
from disnake.ext import commands
from pymongo.typings import _DocumentType
from utils.functions import natural_join, timedeltaplus
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
    def new(cls, bot: _LabyrinthianT, owner: disnake.User, settings: ServerSettings, guild: disnake.Guild):
        inst = cls(owner=owner, timeout=180)
        inst.bot = bot
        inst.settings = settings
        inst.guild = guild
        return inst

    @disnake.ui.button(style=disnake.ButtonStyle.primary, label="Auction House Settings")
    async def auction_house_settings(self, _: disnake.ui.Button, inter: disnake.MessageInteraction):
        return
        await self.defer_to(AuctionSettingsView, inter)

    @disnake.ui.button(style=disnake.ButtonStyle.primary, label="Badgelog Settings")
    async def badgelog_settings(self, _: disnake.ui.Button, inter: disnake.MessageInteraction):
        return
        await self.defer_to(BadgelogSettingsView, inter)

    @disnake.ui.button(style=disnake.ButtonStyle.primary, label="Bot Settings")
    async def bot_settings(self, _:disnake.ui.Button, inter: disnake.MessageInteraction):
        await self.defer_to(BotSettingsView, inter)

    @disnake.ui.button(label="Exit", style=disnake.ButtonStyle.danger)
    async def exit(self, *_):
        print("testthingie")
        await self.on_timeout()

    async def get_content(self) -> Mapping:
        if self.settings.dmroles:
            dmroles = ''.join([f"<@&{role_id}>\n" for role_id in self.settings.dmroles])
        else:
            dmroles = "Dungeon Master, DM, Game Master, or GM"
        durstrcon = []
        for x,y in self.settings.listingdurs.items():
            durstrcon.append(f"{str(timedeltaplus(seconds=int(x)))} - {y} gp fee")
        listingdurstr = '\n'.join(durstrcon)
        embed = (
            disnake.Embed(title=f"Labyrinthian settings for {self.guild.name}")
            .add_field(
                name="__General Settings__",
                value=f"**DM Roles**: \n{dmroles}\n"
                f"\u200B",
                inline=True
            )
            .add_field(
                name="__Auction Settings__",
                value=f"**Auction Listings Channel**: <#{self.settings.ahfront}>\n"
                f"**Auction Logging Channel**: <#{self.settings.ahinternal}>\n"
                f"**Auction Menu Channel**: <#{self.settings.ahback}>\n"
                f"**Auction Outbit Threshold**: {self.settings.outbitthreshold}\n"
                f"**Listing Duration Options**: \n{listingdurstr}",
                inline=True
            )
            .add_field(name="__Character Log Settings__", value="\u200B", inline=True)
        )
        return {"embed": embed}


class AuctionSettingsView(SettingsMenuBase):
    def __init__(self, bot: _LabyrinthianT, settings: _DocumentType):
        super().__init__(timeout=180)


class BadgelogSettingsView(SettingsMenuBase):
    def __init__(self, bot: _LabyrinthianT, settings: _DocumentType):
        super().__init__(timeout=180)


class BotSettingsView(SettingsMenuBase):
    def __init__(self, bot: _LabyrinthianT, settings: _DocumentType):
        super().__init__(timeout=180)

