import abc
import asyncio
from contextlib import suppress
from copy import deepcopy
from random import randint
import re
from typing import TYPE_CHECKING, List, Mapping, Optional, Type, TypeVar
from click import style
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

TOO_MANY_ROLES_SENTINEL = "__special:too_many_roles"


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
        await self.on_timeout()

    async def get_content(self) -> Mapping:
        if self.settings.dmroles:
            dmroles = ''.join([f"<@&{role_id}>\n" for role_id in self.settings.dmroles])
        else:
            dmroles = "Dungeon Master, DM, Game Master, or GM"
        
        firstmax = max([len(str(timedeltaplus(seconds=int(x)))) for x in self.settings.listingdurs])
        secondmax = max([len(str(x)) for x in self.settings.listingdurs.values()])
        listingdurstr = []
        for x,y in self.settings.listingdurs.items():
            listingdurstr.append(f"{str(timedeltaplus(seconds=int(x))):{firstmax}} - {y:{secondmax}} gp fee")
        if len(listingdurstr) > 5:
            listingdurstr = listingdurstr[:5]
            listingdurstr.append('...')
        listingdurstr = '\n'.join(listingdurstr)
        
        firstmax = max([len(x) for x in self.settings.rarities])
        secondmax = max([len(str(x)) for x in self.settings.rarities.values()])
        raritiesstr = []
        for x,y in self.settings.rarities.items():
            raritiesstr.append(f"{x:{firstmax}} - {y:{secondmax}} gp fee")
        if len(raritiesstr) > 5:
            raritiesstr = raritiesstr[:5]
            raritiesstr.append('...')
        raritiesstr = '\n'.join(raritiesstr)
        
        ordinal = lambda n: "%d%s" % (n,"tsnrhtdd"[(n//10%10!=1)*(n%10<4)*n%10::4])
        firstmax = max([len(ordinal(int(x))) for x in self.settings.badgetemplate])
        secondmax = max([len(str(x)) for x in self.settings.badgetemplate.values()])
        templatestr = []
        for x,y in self.settings.badgetemplate.items():
            templatestr.append(f"{ordinal(int(x)):{firstmax}} requires {y:{secondmax}} {self.settings.badgelabel}")
        if len(templatestr) > 5:
            templatestr = templatestr[:5]
            templatestr.append('...')
        templatestr = '\n'.join(templatestr)
        
        classlist = deepcopy(self.settings.classlist)
        if len(classlist) > 5:
            classlist = classlist[:5]
            classlist.append('...')
        classlist = '\n'.join(classlist)
        
        embeds = [
            (
                disnake.Embed(title=f"Labyrinthian settings for {self.guild.name}")
                .add_field(
                    name="__General Settings__",
                    value=f"**DM Roles**: \n{dmroles}\n"
                    f"**Server Class List**: \n```\n{classlist}```\n",
                    inline=False
                )
                .add_field(
                    name="__Auction Settings__",
                    value=f"**Auction Listings Channel**: <#{self.settings.ahfront}>\n"
                    f"**Auction Logging Channel**: <#{self.settings.ahinternal}>\n"
                    f"**Auction Menu Channel**: <#{self.settings.ahback}>\n"
                    f"**Auction Outbid Threshold**: {self.settings.outbidthreshold}\n"
                    f"**Listing Duration Options**: \n```{listingdurstr}```\n"
                    f"**Item Rarity Options**: \n```{raritiesstr}```",
                    inline=True
                )
                .add_field(
                    name="__Character Log Settings__",
                    value=f"**Badge Template**: \n```{templatestr}```\n",
                    inline=True
                )
                .add_field(name='\u200B', value='\u200B')
                .add_field(
                    name='__Coinpurse Settings__',
                    value=f"\u200B",
                    inline=True
                )
            )
        ]
        return {"embeds": embeds}


class AuctionSettingsView(SettingsMenuBase):

    # ==== ui ====
    

    @disnake.ui.button(label="Back", style=disnake.ButtonStyle.grey, row=4)
    async def back(self, _: disnake.ui.Button, inter: disnake.Interaction):
        await self.defer_to(SettingsNav, inter)


class BadgelogSettingsView(SettingsMenuBase):

    # ==== ui ====


    @disnake.ui.button(label="Back", style=disnake.ButtonStyle.grey, row=4)
    async def back(self, _: disnake.ui.Button, inter: disnake.Interaction):
        await self.defer_to(SettingsNav, inter)


class BotSettingsView(SettingsMenuBase):
    select_dm_roles: disnake.ui.Select  # make the type checker happy

    # ==== ui ====
    @disnake.ui.select(placeholder="Select DM Roles", min_values=0)
    async def select_dm_roles(self, select: disnake.ui.Select, inter: disnake.Interaction):
        if len(select.values) == 1 and select.values[0] == TOO_MANY_ROLES_SENTINEL:
            role_ids = await self._text_select_dm_roles(inter)
        else:
            role_ids = list(map(int, select.values))
        self.settings.dmroles = role_ids or None
        self._refresh_dm_role_select()
        await self.commit_settings()
        await self.refresh_content(inter)

    @disnake.ui.button(label='Configure Class List', style=disnake.ButtonStyle.primary)
    async def select_classes(self, button: disnake.ui.Button, inter: disnake.Interaction):
        components = [
            disnake.ui.TextInput(
                style=disnake.TextInputStyle.multi_line,
                label='Classes to Add',
                placeholder='A list of class names separated by either commas or new lines.',
                custom_id='settings_classes_add',
                required=False,
                max_length=200
            ),
            disnake.ui.TextInput(
                style=disnake.TextInputStyle.multi_line,
                label='Classes to Remove',
                placeholder='A list of class names separated by either commas or new lines.',
                custom_id='settings_classes_remove',
                required=False,
                max_length=200
            ),
            disnake.ui.TextInput(
                style=disnake.TextInputStyle.single_line,
                label='Reset to Default',
                placeholder='Type "Confirm" here to reset the class list to the defaults',
                custom_id='settings_classes_reset',
                required=False,
                max_length=7
            )
        ]
        rand = randint(111111, 999999)
        await inter.response.send_modal(
            custom_id=f'{rand}settings_classes_modal',
            title='Add/Remove Server Classes',
            components=components
        )
        try:
            modalinter: disnake.ModalInteraction = await self.bot.wait_for(
                "modal_submit",
                check=lambda i: i.custom_id == f"{rand}settings_classes_modal" and i.author.id == inter.author.id,
                timeout=180
            )

            if modalinter.text_values['settings_classes_reset'] == 'Confirm':
                inter.send('Class list reset to defaults', ephemeral=True)
                self.settings.classlist = None
                return

            if len(modalinter.text_values['settings_classes_add']) > 0:
                addclasses = modalinter.text_values['settings_classes_add']
                addclasses = re.split(',[ ]*|\n', addclasses)
                for x in addclasses:
                    x = re.sub(r'[^a-zA-Z0-9 ]', '', x)
                    x = re.sub(r' +', ' ', x).strip()
                classlist = list(set(self.settings.classlist)|set(addclasses))
                classlist.sort()
                self.settings.classlist = classlist

            if len(modalinter.text_values['settings_classes_remove']) > 0:
                removeclasses = modalinter.text_values['settings_classes_remove']
                removeclasses = re.split(',[ ]*|\n', addclasses)
                for x in removeclasses:
                    x = re.sub(r'[^a-zA-Z0-9 ]', '', x)
                    x = re.sub(r' +', ' ', x).strip()
                    if x in self.settings.classlist:
                        self.settings.classlist.remove(x)
            await self.commit_settings()
            await self.refresh_content(modalinter)
        except asyncio.TimeoutError:
            inter.send("It seems your form timed out, if you see this message, it is most likely because you took too long to fill out the form.\n\nPlease try again.", ephemeral=True)
            return



    @disnake.ui.button(label="Back", style=disnake.ButtonStyle.grey, row=4)
    async def back(self, _: disnake.ui.Button, inter: disnake.Interaction):
        await self.defer_to(SettingsNav, inter)
    
    
    # ==== handlers ====
    async def _text_select_dm_roles(self, inter: disnake.Interaction) -> Optional[List[int]]:
        self.select_dm_roles.disabled = True
        await self.refresh_content(inter)
        await inter.send(
            "Choose the DM roles by sending a message to this channel. You can mention the roles, or use a "
            "comma-separated list of role names or IDs. Type `reset` to reset the role list to the default.",
            ephemeral=True,
        )

        try:
            input_msg: disnake.Message = await self.bot.wait_for(
                "message",
                timeout=60,
                check=lambda msg: msg.author == inter.author and msg.channel.id == inter.channel_id,
            )
            with suppress(disnake.HTTPException):
                await input_msg.delete()

            if input_msg.content == "reset":
                await inter.send("The DM roles have been updated.", ephemeral=True)
                return None

            role_ids = {r.id for r in input_msg.role_mentions}
            for stmt in input_msg.content.split(","):
                clean_stmt = stmt.strip()
                try:  # get role by id
                    role_id = int(clean_stmt)
                    maybe_role = self.guild.get_role(role_id)
                except ValueError:  # get role by name
                    maybe_role = next((r for r in self.guild.roles if r.name.lower() == clean_stmt.lower()), None)
                if maybe_role is not None:
                    role_ids.add(maybe_role.id)

            if role_ids:
                await inter.send("The DM roles have been updated.", ephemeral=True)
                return list(role_ids)
            await inter.send("No valid roles found. Use the select menu to try again.", ephemeral=True)
            return self.settings.dmroles
        except asyncio.TimeoutError:
            await inter.send("No valid roles found. Use the select menu to try again.", ephemeral=True)
            return self.settings.dmroles
        finally:
            self.select_dm_roles.disabled = False

    # ==== content ====
    def _refresh_dm_role_select(self):
        """Update the options in the DM Role select to reflect the currently selected values."""
        self.select_dm_roles.options.clear()
        if len(self.guild.roles) > 25:
            self.select_dm_roles.add_option(
                label="Whoa, this server has a lot of roles! Click here to select them.", value=TOO_MANY_ROLES_SENTINEL
            )
            return

        for role in reversed(self.guild.roles):  # display highest-first
            selected = self.settings.dmroles is not None and role.id in self.settings.dmroles
            self.select_dm_roles.add_option(label=role.name, value=str(role.id), emoji=role.emoji, default=selected)
        self.select_dm_roles.max_values = len(self.select_dm_roles.options)

    async def _before_send(self):
        self._refresh_dm_role_select()

    async def get_content(self):
        classlist = natural_join([_class for _class in self.settings.classlist], 'and')
        embeds = [
            (
                disnake.Embed(
                    title=f"Server Settings ({self.guild.name}) / General Bot Settings",
                    colour=disnake.Colour.blurple(),
                    description="These settings affect the bot as a whole, and are used in many of the bots different systems.",
                )
                .add_field(
                    name='Server Class List',
                    value=f"**{classlist}**\n"
                    f"This is a list of classes that are allowed for play in this server."
                    f"Any class listed here will be selectable when creating a character"
                    f"log.",
                    inline=True
                )
            )
        ]
        if not self.settings.dmroles:
            embeds[0].insert_field_at(
                index=0,
                name="DM Roles",
                value=f"**Dungeon Master, DM, Game Master, or GM**\n"
                f"*Any user with a role named one of these will be considered a DM. This lets them adjust players "
                f"badge counts.*",
                inline=False,
            )
        else:
            dmroles = natural_join([f"<@&{role_id}>" for role_id in self.settings.dmroles], "and")
            embeds[0].insert_field_at(
                index=0,
                name="DM Roles",
                value=f"**{dmroles}**\n"
                f"*Any user with at least one of these roles will be considered a DM. This lets them adjust players "
                f"badge counts.*",
                inline=False,
            )
        
        return {"embeds": embeds}

