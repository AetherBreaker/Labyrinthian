import abc
import asyncio
from contextlib import suppress
from copy import deepcopy
from random import randint
import re
from typing import TYPE_CHECKING, Any, Dict, List, Mapping, Optional, TypeVar
import disnake
from utils.functions import natural_join, timedeltaplus, truncate_list
from utils.settings.guild import ServerSettings

from utils.ui.menu import MenuBase


_LabyrinthianT = TypeVar("_LabyrinthianT", bound=disnake.Client)
if TYPE_CHECKING:
    from bot import Labyrinthian

    _LabyrinthianT = Labyrinthian
TOO_MANY_ROLES_SENTINEL = "__special:too_many_roles"

T = TypeVar("T")

inputtemplate = {"main": {"title": "title", "descitems": [], "fielditems": []}}


class SettingsMenuBase(MenuBase, abc.ABC):
    __menu_copy_attrs__ = ("bot", "settings", "guild")
    bot: _LabyrinthianT
    settings: ServerSettings
    guild: disnake.Guild

    async def commit_settings(self):
        """Commits any changed guild settings to the db."""
        await self.settings.commit(self.bot.dbcache)

    def format_settings_overflow(self, input: Dict[str, Dict[str, Any]]):
        embindex = -1
        chktotallen = lambda list: sum(len(disnake.Embed.from_dict(x)) for x in list)
        chkemblen = (
            lambda emb, newlen: (len(disnake.Embed.from_dict(emb)) + newlen) > 6000
        )
        chkitemlen = lambda item: sum(
            [len(str(y)) for x, y in item.items() if x != "inline"]
        )
        result = []
        for key, embed in input.items():
            fieldindex = 0
            descoverflow = 0
            result.append(
                {
                    "title": "",
                    "description": "",
                    "color": disnake.Color.random().value,
                    "fields": [],
                }
            )
            embindex += 1
            if "title" in embed:
                result[embindex]["title"] = embed["title"]
            if "author" in embed:
                result[embindex]["author"] = embed["author"]
            if "footer" in embed:
                result[embindex]["footer"] = embed["footer"]
            if "descitems" in embed:
                for item in embed["descitems"]:
                    itemlen = chkitemlen(item)
                    if (itemlen + len(result[embindex]["description"])) > 4096:
                        descoverflow = 1
                    if (
                        descoverflow == 1
                        and (
                            len(result[embindex]["fields"][fieldindex]["value"])
                            + itemlen
                        )
                        > 1024
                    ):
                        result[embindex]["fields"].append({})
                        fieldindex += 1
                    if (itemlen + chktotallen(result)) > 6000:
                        return result
                    if descoverflow == 1:
                        result[embindex]["fields"][fieldindex]["name"] = "\u200B"
                        for part, contents in item.items():
                            if part == "header":
                                result[embindex]["fields"][fieldindex][
                                    "value"
                                ] += f"\n{contents}"
                            elif part == "setting":
                                result[embindex]["fields"][fieldindex][
                                    "value"
                                ] += f"\n{contents}"
                            elif part == "desc":
                                result[embindex]["fields"][fieldindex][
                                    "value"
                                ] += f"\n{contents}"
                    else:
                        for part, contents in item.items():
                            if part == "header":
                                result[embindex]["description"] += f"\n{contents}"
                            elif part == "setting":
                                result[embindex]["description"] += f"\n{contents}"
                            elif part == "desc":
                                result[embindex]["description"] += f"\n{contents}"
                            else:
                                result[embindex]["description"] += f"\n{contents}\n"
            else:
                result[embindex]["description"] = "\u200B"
            if "fielditems" in embed:
                for item in embed["fielditems"]:
                    itemlen = chkitemlen(item)
                    if (itemlen + chktotallen(result)) > 6000:
                        return result
                    result[embindex]["fields"].append(item)
        return result


class SettingsNav(SettingsMenuBase):
    @classmethod
    def new(
        cls,
        bot: _LabyrinthianT,
        owner: disnake.User,
        settings: ServerSettings,
        guild: disnake.Guild,
    ):
        inst = cls(owner=owner, timeout=180)
        inst.bot = bot
        inst.settings = settings
        inst.guild = guild
        return inst

    @disnake.ui.button(
        style=disnake.ButtonStyle.primary, label="Auction House Settings"
    )
    async def auction_house_settings(
        self, _: disnake.ui.Button, inter: disnake.MessageInteraction
    ):
        return
        await self.defer_to(AuctionSettingsView, inter)

    @disnake.ui.button(style=disnake.ButtonStyle.primary, label="Badgelog Settings")
    async def badgelog_settings(
        self, _: disnake.ui.Button, inter: disnake.MessageInteraction
    ):
        return
        await self.defer_to(BadgelogSettingsView, inter)

    @disnake.ui.button(style=disnake.ButtonStyle.primary, label="Bot Settings")
    async def bot_settings(
        self, _: disnake.ui.Button, inter: disnake.MessageInteraction
    ):
        await self.defer_to(BotSettingsView, inter)

    @disnake.ui.button(label="Exit", style=disnake.ButtonStyle.danger)
    async def exit(self, *_):
        await self.on_timeout()

    async def get_content(self) -> Mapping:
        inputdict = deepcopy(inputtemplate)
        if self.settings.dmroles:
            dmroles = "".join([f"<@&{role_id}>\n" for role_id in self.settings.dmroles])
        else:
            dmroles = "Dungeon Master, DM, Game Master, or GM"
        firstmax = max(
            len(str(timedeltaplus(seconds=int(x)))) for x in self.settings.listingdurs
        )
        secondmax = max(len(str(x)) for x in self.settings.listingdurs.values())
        listingdurstr = "\n".join(
            truncate_list(
                [
                    f"{str(timedeltaplus(seconds=int(x))):{firstmax}}"
                    f"- {y:{secondmax}} gp fee"
                    for x, y in self.settings.listingdurs.items()
                ],
                5,
            )
        )

        firstmax = max(len(x) for x in self.settings.rarities)
        secondmax = max(len(str(x)) for x in self.settings.rarities.values())
        raritiesstr = "\n".join(
            truncate_list(
                [
                    f"{x:{firstmax}} - {y:{secondmax}} gp fee"
                    for x, y in self.settings.rarities.items()
                ],
                5,
            )
        )

        ordinal = lambda n: "%d%s" % (
            n,
            "tsnrhtdd"[(n // 10 % 10 != 1) * (n % 10 < 4) * n % 10 :: 4],
        )
        firstmax = max(len(ordinal(int(x))) for x in self.settings.badgetemplate)
        secondmax = max(len(str(x)) for x in self.settings.badgetemplate.values())
        templatestr = "\n".join(
            (
                truncate_list(
                    [
                        f"{ordinal(int(x)):{firstmax}} requires"
                        f"{y:{secondmax}} {self.settings.badgelabel}"
                        for x, y in self.settings.badgetemplate.items()
                    ],
                    5,
                )
            )
        )

        classlist = "\n".join(truncate_list(deepcopy(self.settings.classlist), 5))

        inputdict["main"]["title"] = f"Labyrinthian settings for {self.guild.name}"
        inputdict["main"]["fielditems"].append(
            {
                "name": "__General Settings__",
                "value": (
                    f"**DM Roles**: \n{dmroles}\n"
                    f"**Server Class List**: \n```\n{classlist}```\n"
                ),
                "inline": False,
            }
        )
        inputdict["main"]["fielditems"].append(
            {
                "name": "__Auction Settings__",
                "value": (
                    f"**Auction Listings Channel**: <#{self.settings.ahfront}>\n"
                    f"**Auction Logging Channel**: <#{self.settings.ahinternal}>\n"
                    f"**Auction Menu Channel**: <#{self.settings.ahback}>\n"
                    f"**Auction Outbid Threshold**: {self.settings.outbidthreshold}\n"
                    f"**Listing Duration Options**: \n```{listingdurstr}```\n"
                    f"**Item Rarity Options**: \n```{raritiesstr}```"
                ),
                "inline": True,
            }
        )
        inputdict["main"]["fielditems"].append(
            {
                "name": "__Character Log Settings__",
                "value": f"**Badge Template**: \n```{templatestr}```\n",
                "inline": True,
            }
        )
        inputdict["main"]["fielditems"].append({"name": "\u200B", "value": "\u200B"})
        inputdict["main"]["fielditems"].append(
            {"name": "__Coinpurse Settings__", "value": f"\u200B", "inline": True}
        )
        embeds = self.format_settings_overflow(inputdict)
        embeds = [disnake.Embed.from_dict(x) for x in embeds]
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
    async def select_dm_roles(
        self, select: disnake.ui.Select, inter: disnake.Interaction
    ):
        if len(select.values) == 1 and select.values[0] == TOO_MANY_ROLES_SENTINEL:
            role_ids = await self._text_select_dm_roles(inter)
        else:
            role_ids = list(map(int, select.values))
        self.settings.dmroles = role_ids or None
        self._refresh_dm_role_select()
        await self.commit_settings()
        await self.refresh_content(inter)

    @disnake.ui.button(label="Configure Class List", style=disnake.ButtonStyle.primary)
    async def select_classes(
        self, button: disnake.ui.Button, inter: disnake.Interaction
    ):
        components = [
            disnake.ui.TextInput(
                style=disnake.TextInputStyle.multi_line,
                label="Classes to Add",
                placeholder="A list of class names separated by either commas or new lines.",
                custom_id="settings_classes_add",
                required=False,
                max_length=200,
            ),
            disnake.ui.TextInput(
                style=disnake.TextInputStyle.multi_line,
                label="Classes to Remove",
                placeholder="A list of class names separated by either commas or new lines.",
                custom_id="settings_classes_remove",
                required=False,
                max_length=200,
            ),
            disnake.ui.TextInput(
                style=disnake.TextInputStyle.single_line,
                label="Reset to Default",
                placeholder='Type "Confirm" here to reset the class list to the defaults',
                custom_id="settings_classes_reset",
                required=False,
                max_length=7,
            ),
        ]
        rand = randint(111111, 999999)
        await inter.response.send_modal(
            custom_id=f"{rand}settings_classes_modal",
            title="Add/Remove Server Classes",
            components=components,
        )
        try:
            modalinter: disnake.ModalInteraction = await self.bot.wait_for(
                "modal_submit",
                check=lambda i: i.custom_id == f"{rand}settings_classes_modal"
                and i.author.id == inter.author.id,
                timeout=180,
            )

            if modalinter.text_values["settings_classes_reset"] == "Confirm":
                inter.send("Class list reset to defaults", ephemeral=True)
                self.settings.classlist = None
                return
            if len(modalinter.text_values["settings_classes_add"]) > 0:
                addclasses = modalinter.text_values["settings_classes_add"]
                addclasses = re.split(",[ ]*|\n", addclasses)
                for x in addclasses:
                    x = re.sub(r"[^a-zA-Z0-9 ]", "", x)
                    x = re.sub(r" +", " ", x).strip()
                classlist = list(set(self.settings.classlist) | set(addclasses))
                classlist.sort()
                self.settings.classlist = classlist
            if len(modalinter.text_values["settings_classes_remove"]) > 0:
                removeclasses = modalinter.text_values["settings_classes_remove"]
                removeclasses = re.split(",[ ]*|\n", addclasses)
                for x in removeclasses:
                    x = re.sub(r"[^a-zA-Z0-9 ]", "", x)
                    x = re.sub(r" +", " ", x).strip()
                    if x in self.settings.classlist:
                        self.settings.classlist.remove(x)
            await self.commit_settings()
            await self.refresh_content(modalinter)
        except asyncio.TimeoutError:
            inter.send(
                "It seems your form timed out, if you see this message, it is most likely because you took too long to fill out the form.\n\nPlease try again.",
                ephemeral=True,
            )
            return

    @disnake.ui.button(label="Back", style=disnake.ButtonStyle.grey, row=4)
    async def back(self, _: disnake.ui.Button, inter: disnake.Interaction):
        await self.defer_to(SettingsNav, inter)

    # ==== handlers ====
    async def _text_select_dm_roles(
        self, inter: disnake.Interaction
    ) -> Optional[List[int]]:
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
                check=lambda msg: msg.author == inter.author
                and msg.channel.id == inter.channel_id,
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
                    maybe_role = next(
                        (
                            r
                            for r in self.guild.roles
                            if r.name.lower() == clean_stmt.lower()
                        ),
                        None,
                    )
                if maybe_role is not None:
                    role_ids.add(maybe_role.id)
            if role_ids:
                await inter.send("The DM roles have been updated.", ephemeral=True)
                return list(role_ids)
            await inter.send(
                "No valid roles found. Use the select menu to try again.",
                ephemeral=True,
            )
            return self.settings.dmroles
        except asyncio.TimeoutError:
            await inter.send(
                "No valid roles found. Use the select menu to try again.",
                ephemeral=True,
            )
            return self.settings.dmroles
        finally:
            self.select_dm_roles.disabled = False

    # ==== content ====
    def _refresh_dm_role_select(self):
        """Update the options in the DM Role select to reflect the currently selected values."""
        self.select_dm_roles.options.clear()
        if len(self.guild.roles) > 25:
            self.select_dm_roles.add_option(
                label="Whoa, this server has a lot of roles! Click here to select them.",
                value=TOO_MANY_ROLES_SENTINEL,
            )
            return
        for role in reversed(self.guild.roles):  # display highest-first
            selected = (
                self.settings.dmroles is not None and role.id in self.settings.dmroles
            )
            self.select_dm_roles.add_option(
                label=role.name, value=str(role.id), emoji=role.emoji, default=selected
            )
        self.select_dm_roles.max_values = len(self.select_dm_roles.options)

    async def _before_send(self):
        self._refresh_dm_role_select()

    async def get_content(self):
        inputdict = deepcopy(inputtemplate)
        classlist = natural_join([_class for _class in self.settings.classlist], "and")
        if not self.settings.dmroles:
            dmroles = f"**Dungeon Master, DM, Game Master, or GM**\n"
            dmrolesdesc = (
                f"*Any user with a role named one of these will be considered a DM. This lets them adjust players "
                f"badge counts.*"
            )
        else:
            dmroles = natural_join(
                [f"<@&{role_id}>" for role_id in self.settings.dmroles], "and"
            )
            dmrolesdesc = (
                f"*Any user with at least one of these roles will be considered a DM. This lets them adjust players "
                f"badge counts.*"
            )
        inputdict["main"][
            "title"
        ] = f"Server Settings ({self.guild.name}) / General Bot Settings"
        inputdict["main"]["color"] = disnake.Colour.blurple()
        inputdict["main"]["descitems"].append(
            {
                "this is a description": (
                    f"These settings affect the bot as a whole, and are used in many of the "
                    f"bots different systems."
                )
            }
        )
        inputdict["main"]["descitems"].append(
            {
                "header": f"__**DM Roles:**__",
                "setting": f"{dmroles}",
                "desc": f"{dmrolesdesc}",
            }
        )
        inputdict["main"]["descitems"].append(
            {
                "header": f"\n__**Server Class List:**__",
                "setting": f"```ansi\n\u001b[1;40;32m{classlist}```",
                "desc": (
                    f"*This is a list of classes that are allowed for play in this server."
                    f"Any class listed here will be selectable when creating a character"
                    f"log.*"
                ),
            }
        )
        embeds = self.format_settings_overflow(inputdict)
        embeds = [disnake.Embed.from_dict(x) for x in embeds]
        return {"embeds": embeds}
