import abc
import asyncio
from contextlib import suppress
from copy import deepcopy
from random import randint
import re
from typing import TYPE_CHECKING, Any, Dict, List, Mapping, Optional, Union
import disnake
import inflect
from utils.functions import (
    has_unicode_emote,
    natural_join,
    search_and_select,
    simple_tabulate_str,
    truncate_list,
)
from utils.models.coinpurse import Coin
from utils.models.errors import FormInvalidInputError, FormTimeoutError
from utils.models.settings.auction import Duration, Rarity
from utils.models.settings.coin import BaseCoin, CoinType
from utils.models.settings.guild import XPConfig, ServerSettings

from utils.ui.menu import MenuBase
from utils.ui.menutemplates import AddButton, EditButton, RemoveButton, SelectandModify


if TYPE_CHECKING:
    from bot import Labyrinthian


class SettingsMenuBase(MenuBase, abc.ABC):
    __menu_copy_attrs__ = ("bot", "settings", "guild")
    bot: "Labyrinthian"
    settings: ServerSettings
    guild: disnake.Guild
    inputtemplate = {"main": {"title": "title", "descitems": [], "fielditems": []}}

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
                if "skipdesc" in embed:
                    if embed["skipdesc"]:
                        descoverflow = 1
                for item in embed["descitems"]:
                    itemlen = chkitemlen(item)
                    if (itemlen + len(result[embindex]["description"])) > 4096:
                        descoverflow = 1
                    if descoverflow == 1:
                        if len(result[embindex]["fields"]) == fieldindex:
                            result[embindex]["fields"].append(
                                {"name": "\u200B", "value": ""}
                            )
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
                            elif part == "inline":
                                result[embindex]["fields"][fieldindex][
                                    "inline"
                                ] = contents
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
        bot: "Labyrinthian",
        owner: disnake.User,
        settings: ServerSettings,
        guild: disnake.Guild,
    ):
        inst = cls(owner=owner, timeout=180)
        inst.bot = bot
        inst.settings = settings
        inst.guild = guild
        return inst

    # ==== ui ====
    @disnake.ui.button(
        style=disnake.ButtonStyle.primary,
        label="Auction House Settings",
        disabled=False,
    )
    async def auction_house_settings(
        self, _: disnake.ui.Button, inter: disnake.MessageInteraction
    ):
        await self.defer_to(AuctionSettingsView, inter)

    @disnake.ui.button(
        style=disnake.ButtonStyle.primary, label="Character Log Settings"
    )
    async def xplog_settings(
        self, _: disnake.ui.Button, inter: disnake.MessageInteraction
    ):
        await self.defer_to(CharacterLogSettingsView, inter)

    @disnake.ui.button(style=disnake.ButtonStyle.primary, label="Bot Settings")
    async def bot_settings(
        self, _: disnake.ui.Button, inter: disnake.MessageInteraction
    ):
        await self.defer_to(BotSettingsView, inter)

    @disnake.ui.button(style=disnake.ButtonStyle.primary, label="Coin Purse Settings")
    async def coin_purse_settings(
        self, _: disnake.ui.Button, inter: disnake.MessageInteraction
    ):
        await self.defer_to(CoinPurseSettingsView, inter)

    @disnake.ui.button(label="Exit", style=disnake.ButtonStyle.danger, row=4)
    async def exit(self, *_):
        await self.on_timeout()

    # ==== content ====
    async def get_content(self) -> Mapping:
        p = inflect.engine()
        inputdict = deepcopy(self.inputtemplate)

        # prepping dmroles string
        if self.settings.dmroles:
            dmroles = "".join([f"<@&{role_id}>\n" for role_id in self.settings.dmroles])
        else:
            dmroles = "Dungeon Master, DM, Game Master, or GM"

        # constructing list for listing durations
        firstmax = max(
            len(x.durstr) for x, y in zip(self.settings.listingdurs, range(0, 5))
        )
        secondmax = max(
            len(str(x)) for x, y in zip(self.settings.listingdurs.values(), range(0, 5))
        )
        listingdurstr = "\n".join(
            truncate_list(
                [
                    f"{x.durstr:{firstmax}} - {y:{secondmax}} {y.type.prefix} fee"
                    for x, y in self.settings.listingdurs.items()
                ],
                5,
                "...",
            )
        )

        # constructing list for item rarities
        firstmax = max(len(x) for x, y in zip(self.settings.rarities, range(0, 5)))
        secondmax = max(
            len(str(x)) for x, y in zip(self.settings.rarities.values(), range(0, 5))
        )
        raritiesstr = "\n".join(
            truncate_list(
                [
                    f"{x:{firstmax}} - {y:{secondmax}} {y.type.prefix} fee"
                    for x, y in self.settings.rarities.items()
                ],
                5,
                "...",
            )
        )

        # constructing list for xp template
        ordinal = lambda n: "%d%s" % (
            n,
            "tsnrhtdd"[(n // 10 % 10 != 1) * (n % 10 < 4) * n % 10 :: 4],
        )
        firstmax = max(
            len(ordinal(x + 1) if y.isnumeric() else y)
            for x, (y, z) in enumerate(
                zip(self.settings.xptemplate.values(), range(0, 5))
            )
        )
        secondmax = max(
            len(str(x)) for x, y in zip(self.settings.xptemplate, range(0, 5))
        )
        xplist = []
        for x, (y, z) in enumerate(self.settings.xptemplate.items()):
            if str(y).isnumeric():
                temp = f"{ordinal(x+1):{firstmax}} level"
            else:
                temp = f"{y}"
            xplist.append(
                f"{temp} requires {z:{secondmax}} {p.plural_noun(self.settings.xplabel, z)}"
            )
        templatestr = "\n".join(
            truncate_list(
                xplist,
                5,
                "...",
            )
        )

        # creating classlist str
        classlist = "\n".join(
            truncate_list(deepcopy(self.settings.classlist), 5, "...")
        )

        namemax = max(len(x.name) for x in self.settings.coinconf)
        prefmax = max(len(x.prefix) for x in self.settings.coinconf)
        ratemax = max(len(str(x.rate)) for x in self.settings.coinconf.types)
        coinstr = (
            f"""Base Currency:\n"""
            f"""> {self.settings.coinconf.base.emoji} `{self.settings.coinconf.base.name:>{namemax}}: prefix={'"'+self.settings.coinconf.base.prefix+'"':{prefmax+2}} | rate={'1.0':>{ratemax}}`\n"""
            f"""Currency Subtypes:\n"""
        )
        joinlist = []
        for x in self.settings.coinconf.types:
            joinlist.append(
                f"""> {x.emoji} `{x.name:>{namemax}}: prefix={'"'+x.prefix+'"':{prefmax+2}} | rate={x.rate:{ratemax}}`"""
            )
        coinstr += "\n".join(joinlist)

        # filling out embed form for processing into embed
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
                    f"**Listing Duration Options**: \n```{listingdurstr}```\n"
                    f"**Item Rarity Options**: \n```{raritiesstr}```\n"
                    f"**Auction Listings Channel**: <#{self.settings.ahfront}>\n"
                    f"**Auction Logging Channel**: <#{self.settings.ahinternal}>\n"
                    f"**Auction Menu Channel**: <#{self.settings.ahback}>\n"
                    f"**Auction Outbid Threshold**: {self.settings.outbidthreshold.prefixed_count}"
                ),
                "inline": True,
            }
        )
        inputdict["main"]["fielditems"].append(
            {
                "name": "__Character Log Settings__",
                "value": f"**{self.settings.xplabel} Requirements**: \n```{templatestr}```\n",
                "inline": True,
            }
        )
        inputdict["main"]["fielditems"].append({"name": "\u200B", "value": "\u200B"})
        inputdict["main"]["fielditems"].append(
            {
                "name": "__Coinpurse Settings__",
                "value": f"**Currency Types**: \n {coinstr}\n",
                "inline": True,
            }
        )
        embeds = self.format_settings_overflow(inputdict)
        embeds = [disnake.Embed.from_dict(x) for x in embeds]
        return {"embeds": embeds}


class CoinPurseSettingsView(SettingsMenuBase, SelectandModify):
    def __init__(self, owner, timeout):
        self.matched: Union[BaseCoin, CoinType] = None
        self.matchindex: int = None
        super().__init__(owner=owner, timeout=timeout)

    # ==== ui ====
    @disnake.ui.button(label="Back", style=disnake.ButtonStyle.grey, row=4)
    async def back(self, _: disnake.ui.Button, inter: disnake.Interaction):
        await self.defer_to(SettingsNav, inter)

    # ==== overloaded methods ====
    async def confirmation_callback(
        self, inter: disnake.MessageInteraction, modalinter: disnake.ModalInteraction
    ):
        if modalinter.text_values["reset_confirmation_input"] == "Confirm":
            await inter.send("Coin configuration reset.", ephemeral=True)
            self.settings.coinconf = self.settings.__fields__["coinconf"].get_default()
            self.selected = self.matched = self.matchindex = None
            self.refresh_select()
            self.process_selection()
            await self.commit_settings()
        else:
            await inter.send("Config reset canceled", ephemeral=True)
        await self.refresh_content(modalinter)

    # ==== handlers ====
    def process_selection(self):
        matched = False
        for enum, type in enumerate(self.settings.coinconf):
            if type.label == self.selected:
                self.matched = type
                self.matchindex = enum
                matched = True

        # Clear all Coin modification buttons before re-adding the appropriate ones
        self._clear_specific_items(AddButton, EditButton, RemoveButton)

        # Check whether we've reached the CoinType cap
        # and add AddButton if not
        if len(self.settings.coinconf.types) < 24:
            self.add_item(AddButton(label="Add Currency"))
        elif len(self.settings.coinconf.types) >= 24:
            self._clear_specific_items(AddButton)

        if matched == True:
            # Check whether we matched with a BaseCoin or a CoinType
            # if BaseCoin, we only add EditButton button
            # if CoinType, we add both EditButton and RemoveButton buttons
            if isinstance(self.matched, BaseCoin):
                self.add_item(
                    EditButton(label="Edit Currency", emoji=self.matched.emoji)
                )
            elif isinstance(self.matched, CoinType):
                self.add_item(
                    EditButton(label="Edit Currency", emoji=self.matched.emoji)
                )
                self.add_item(
                    RemoveButton(label="Remove Currency", emoji=self.matched.emoji)
                )

            # Check whether there are any existing CoinTypes
            # and remove all RemoveButton buttons if not
            # this is a redunant check incase self.matched isn't accurate
            if len(self.settings.coinconf.types) == 0:
                self._clear_specific_items(RemoveButton)

            # Check whether an item is selected
            # we remove the "remove" button if not
            if self.matched not in self.settings.coinconf.types:
                self._clear_specific_items(RemoveButton)

            # Check whether anything is selected
            # if not, we remove all RemoveButtons and EditButtons
            if not matched:
                self._clear_specific_items(EditButton, RemoveButton)

    async def add(self, inter: disnake.MessageInteraction):
        if len(self.settings.coinconf.types) >= 24:
            return
        await inter.response.send_modal(
            title="Add Currency",
            custom_id=f"{inter.id}add_currency_modal",
            components=self.setup_coin_modal_components(),
        )

        try:
            modalinter: disnake.ModalInteraction = await self.bot.wait_for(
                "modal_submit",
                check=lambda i: i.custom_id == f"{inter.id}add_currency_modal"
                and i.author.id == inter.author.id,
                timeout=180,
            )
        except asyncio.TimeoutError:
            raise FormTimeoutError
        data = {
            "name": modalinter.text_values["modal_currency_name"],
            "prefix": modalinter.text_values["modal_currency_prefix"],
            "rate": modalinter.text_values["modal_currency_rate"],
            "emoji": modalinter.text_values["modal_currency_emoji"],
        }
        for x in self.settings.coinconf:
            if data["name"] == x.name:
                raise FormInvalidInputError(
                    f"Multiple currencies cannot share the same name, please provide a unique name"
                )
            if data["prefix"] == x.prefix:
                raise FormInvalidInputError(
                    f"Multiple currencies cannot share the same prefix, please provide a unique prefix"
                )
        try:
            data["rate"] = re.sub(r"[^\d\.]+", "", data["rate"])
            data["rate"] = float(data["rate"])
        except ValueError:
            raise FormInvalidInputError(
                f"It seems your inputted rate couldn't be converted to a number, please ensure your "
                f"input only contains numbers, and up to a maximum of one decimal point."
            )
        if len(data["emoji"]) > 0:
            if disnake.PartialEmoji.from_str(data["emoji"]).is_unicode_emoji():
                if not has_unicode_emote(data["emoji"]):
                    raise FormInvalidInputError(
                        f"Your inputted icon couldn't be converted to a valid emoji.\n"
                        f"Please ensure it matches one of the following formats:\n"
                        f"Animated:\n"
                        f"> <a:name:id>\n"
                        f"> a:name:id\n"
                        f"Static:\n"
                        f"> <name:id>\n"
                        f"> name:id\n"
                        f"Or you can provide a valid Unicode emoji."
                    )
        self.settings.coinconf.types.append(CoinType.from_dict(data))
        self.settings.coinconf.sort_items()
        self.matchindex = (
            x for x, y in enumerate(self.settings.coinconf.types) if self.matched is y
        )
        await self.commit_settings()
        self.refresh_select()
        await self.refresh_content(modalinter)

    async def edit(self, inter: disnake.MessageInteraction):
        if not self.select_items.values:
            return
        await inter.response.send_modal(
            title="Edit Currency",
            custom_id=f"{inter.id}edit_currency_modal",
            components=self.setup_coin_modal_components(True),
        )
        try:
            modalinter: disnake.ModalInteraction = await self.bot.wait_for(
                "modal_submit",
                check=lambda i: i.custom_id == f"{inter.id}edit_currency_modal"
                and i.author.id == inter.author.id,
                timeout=180,
            )
        except asyncio.TimeoutError:
            raise FormTimeoutError
        data = {
            "name": modalinter.text_values["modal_currency_name"],
            "prefix": modalinter.text_values["modal_currency_prefix"],
            "emoji": modalinter.text_values["modal_currency_emoji"],
        }
        for x in self.settings.coinconf:
            if data["name"] == x.name and data["name"] != self.matched.name:
                raise FormInvalidInputError(
                    f"Multiple currencies cannot share the same name, please provide a unique name"
                )
            if data["prefix"] == x.prefix and data["prefix"] != self.matched.prefix:
                raise FormInvalidInputError(
                    f"Multiple currencies cannot share the same prefix, please provide a unique prefix"
                )
        if not isinstance(self.matched, BaseCoin):
            data["rate"] = modalinter.text_values["modal_currency_rate"]
            try:
                data["rate"] = re.sub(r"[^\d\.]+", "", data["rate"])
                data["rate"] = float(data["rate"])
            except ValueError:
                raise FormInvalidInputError(
                    f"It seems your inputted rate couldn't be converted to a number, please ensure your "
                    f"input only contains numbers, and up to a maximum of one decimal point."
                )
        if len(data["emoji"]) > 0:
            if disnake.PartialEmoji.from_str(data["emoji"]).is_unicode_emoji():
                if not has_unicode_emote(data["emoji"]):
                    raise FormInvalidInputError(
                        f"Your inputted icon couldn't be converted to a valid emoji.\n"
                        f"Please ensure it matches one of the following formats:\n"
                        f"Animated:\n"
                        f"> <a:name:id>\n"
                        f"> a:name:id\n"
                        f"Static:\n"
                        f"> <name:id>\n"
                        f"> name:id\n"
                        f"Or you can provide a valid Unicode emoji."
                    )
        self.settings.coinconf.types[self.matchindex] = CoinType.from_dict(data)
        self.matched = self.settings.coinconf.types[self.matchindex]
        self.settings.coinconf.sort_items()
        self.matchindex = (
            x for x, y in enumerate(self.settings.coinconf.types) if self.matched is y
        )
        await self.commit_settings()
        await self.refresh_content(modalinter)

    async def remove(self, inter: disnake.MessageInteraction):
        if not self.select_items.values:
            return
        elif not isinstance(self.matched, CoinType):
            return
        await inter.response.send_modal(
            title="Confirmation",
            custom_id=f"{inter.id}currency_removal_confirm",
            components=disnake.ui.TextInput(
                label="Confirm Currency Removal",
                custom_id="removal_confirm",
                style=disnake.TextInputStyle.single_line,
                placeholder="Confirm",
                required=True,
                min_length=7,
                max_length=7,
            ),
        )
        try:
            modalinter: disnake.ModalInteraction = await self.bot.wait_for(
                "modal_submit",
                check=lambda i: i.custom_id == f"{inter.id}currency_removal_confirm"
                and i.author.id == inter.author.id,
                timeout=180,
            )
        except asyncio.TimeoutError:
            raise FormTimeoutError
        if modalinter.text_values["removal_confirm"] == "Confirm":
            await inter.send("Removal confirmed", ephemeral=True)
            self.settings.coinconf.types.remove(self.matched)
            self.selected = self.matched = self.matchindex = None
            self.settings.coinconf.sort_items()
            await self.commit_settings()
            self.refresh_select()
            self.process_selection()
        else:
            await inter.send("Removal canceled", ephemeral=True)
        await self.refresh_content(modalinter)

    # ==== helpers ====
    def setup_coin_modal_components(
        self, editing: bool = False
    ) -> List[disnake.ui.TextInput]:
        values = (
            self.matched.to_dict()
            if editing
            else {
                {
                    "name": "",
                    "prefix": "",
                    "emoji": "",
                }
            }
        )
        is_base = isinstance(self.matched, BaseCoin)
        components = [
            disnake.ui.TextInput(
                label="Currency Name:",
                custom_id="modal_currency_name",
                style=disnake.TextInputStyle.single_line,
                placeholder="Gold Piece",
                value=values["name"],
                min_length=2,
                max_length=100,
            ),
            disnake.ui.TextInput(
                label="Currency Prefix:",
                custom_id="modal_currency_prefix",
                style=disnake.TextInputStyle.single_line,
                placeholder="gp",
                value=values["prefix"],
                min_length=1,
                max_length=10,
            ),
            disnake.ui.TextInput(
                label="*Optional* Currency Icon/Emoji:",
                custom_id="modal_currency_emoji",
                style=disnake.TextInputStyle.multi_line,
                placeholder=(
                    f"Accepted inputs:\n"
                    f"a:name:id\n"
                    f"<a:name:id>\n"
                    f"name:id\n"
                    f"<:name:id>\n"
                    f'Example: "<a:badge1:971600879868313602>"'
                ),
                value=values["emoji"],
                required=False,
                max_length=50,
            ),
        ]
        if "rate" in values or not is_base:
            components.insert(
                2,
                disnake.ui.TextInput(
                    label="Rate Description:",
                    custom_id="modal_rate_description",
                    style=disnake.TextInputStyle.multi_line,
                    placeholder="0.5",
                    value=(
                        f"Rate is a number that defines how much base currency this currency is worth.\n"
                        f"For example assuming a Gold piece has a rate of 1 as a base currency, "
                        f"since a Platinum piece is worth 10 Gold pieces, Platinum would have a rate "
                        f" of 0.1, as it is worth 0.1 Gold pieces.\n"
                        f"As another example, since 10 Silver pieces is equal to 1 Gold piece, it would have "
                        f"a rate of 10."
                    ),
                    required=False,
                ),
            )
            components.insert(
                3,
                disnake.ui.TextInput(
                    label="Currency Rate:",
                    custom_id="modal_currency_rate",
                    style=disnake.TextInputStyle.single_line,
                    placeholder="0.5",
                    value=str(values["rate"]),
                    min_length=1,
                    max_length=20,
                ),
            )
        return components

    # ==== content ====
    def refresh_select(self):
        """Update the options in the CoinType select to reflect the currently selected values."""
        self.select_items.options.clear()

        selected = isinstance(self.matched, BaseCoin)

        self.select_items.add_option(
            label=self.settings.coinconf.base.label,
            emoji=self.settings.coinconf.base.emoji,
            default=selected,
        )

        for coin in self.settings.coinconf.types:  # display highest-first
            selected = self.matched is coin
            self.select_items.add_option(
                label=coin.label, emoji=coin.emoji, default=selected
            )

    async def _before_send(self):
        for x in self.children:
            if hasattr(x, "label"):
                if x.label == "Reset Settings":
                    x.label = "Reset Currency Configuration"
            if hasattr(x, "placeholder"):
                if x.placeholder == "Select Item":
                    x.placeholder = "Select Currency Denomination"
        self.add_item(AddButton(label="Add Currency"))
        self.refresh_select()

    async def get_content(self):
        inputdict = deepcopy(self.inputtemplate)

        namemax = max(len(x.name) for x in self.settings.coinconf)
        prefmax = max(len(x.prefix) for x in self.settings.coinconf)
        ratemax = max(len(str(x.rate)) for x in self.settings.coinconf.types)
        coinstr = (
            f"""Base Currency:\n"""
            f"""> {self.settings.coinconf.base.emoji} `{self.settings.coinconf.base.name:>{namemax}}: prefix={'"'+self.settings.coinconf.base.prefix+'"':{prefmax+2}} | rate={'1.0':>{ratemax}}`\n"""
            f"""Currency Subtypes:\n"""
        )
        joinlist = []
        for x in self.settings.coinconf.types:
            joinlist.append(
                f"""> {x.emoji} `{x.name:>{namemax}}: prefix={'"'+x.prefix+'"':{prefmax+2}} | rate={x.rate:{ratemax}}`"""
            )
        coinstr += "\n".join(joinlist)

        inputdict["main"][
            "title"
        ] = f"Server Settings ({self.guild.name}) / Coin Purse Settings"
        inputdict["main"]["descitems"].append(
            {
                "header": "__**Currency Types**__",
                "settings": f"{coinstr}",
                "desc": (
                    f"These define what types of currencies are available for players to use.\n"
                    f"The base currency can never be removed, and always has a rate of 1.0\n"
                    f"All other currencies value are measured in how many of them is needed to equal"
                    f" one base currency, so a platinum piece would have a rate of 0.1, while copper "
                    f"pieces would have a rate of 100."
                ),
            }
        )

        embeds = self.format_settings_overflow(inputdict)
        embeds = [disnake.Embed.from_dict(x) for x in embeds]
        return {"embeds": embeds}


class AuctionSettingsView(SettingsMenuBase):

    # ==== ui ====
    @disnake.ui.button(
        label="Listing Durations Config", style=disnake.ButtonStyle.primary, row=0
    )
    async def durations_config(
        self, _: disnake.ui.Button, inter: disnake.MessageInteraction
    ):
        await self.defer_to(AuctionDurationsView, inter)

    @disnake.ui.button(
        label="Rarities Config", style=disnake.ButtonStyle.primary, row=0
    )
    async def rarities_config(
        self, _: disnake.ui.Button, inter: disnake.MessageInteraction
    ):
        await self.defer_to(AuctionRaritiesView, inter)

    @disnake.ui.button(
        label="Auction Setup Channel",
        style=disnake.ButtonStyle.green,
        row=1,
    )
    async def auction_setup_chan(
        self, _: disnake.ui.Button, inter: disnake.MessageInteraction
    ):
        self.settings.ahback = await self._text_select_channel(
            _, inter, self.settings.ahback
        )
        await self.commit_settings()
        await self.refresh_content(inter)

    @disnake.ui.button(
        label="Auction Logging Channel",
        style=disnake.ButtonStyle.green,
        row=1,
    )
    async def auction_logging_chan(
        self, _: disnake.ui.Button, inter: disnake.MessageInteraction
    ):
        self.settings.ahinternal = await self._text_select_channel(
            _, inter, self.settings.ahinternal
        )
        await self.commit_settings()
        await self.refresh_content(inter)

    @disnake.ui.button(
        label="Auction Listing Channel",
        style=disnake.ButtonStyle.green,
        row=1,
    )
    async def auction_listing_chan(
        self, _: disnake.ui.Button, inter: disnake.MessageInteraction
    ):
        self.settings.ahfront = await self._text_select_channel(
            _, inter, self.settings.ahfront
        )
        await self.commit_settings()
        await self.refresh_content(inter)

    @disnake.ui.button(
        label="Edit Outbid Threshold", style=disnake.ButtonStyle.green, row=2
    )
    async def set_outbid_threshold(
        self, _: disnake.ui.Button, inter: disnake.MessageInteraction
    ):
        options = []
        for x in self.settings.coinconf:
            selected = x.name == self.settings.outbidthreshold.type.name
            options.append(
                disnake.SelectOption(
                    label=f"{x.label} Rate: {x.rate}", emoji=x.emoji, default=selected
                )
            )
        components = [
            disnake.ui.Select(
                custom_id="modal_outbidthreshold_cointype_select",
                placeholder="Select Currency Type",
                options=options,
            ),
            disnake.ui.TextInput(
                label="Coin Count Description",
                custom_id="modal_outbidthreshold_fee_count_desc",
                style=disnake.TextInputStyle.multi_line,
                value=(
                    f"This is the amount of currency for the auction fee to be tied to this duration "
                    f"option."
                ),
                required=False,
            ),
            disnake.ui.TextInput(
                label="Coin Count",
                custom_id="modal_outbidthreshold_fee_count_input",
                style=disnake.TextInputStyle.single_line,
                placeholder="50",
                value=str(self.settings.outbidthreshold),
                max_length=7,
            ),
            disnake.ui.TextInput(
                label="Reset Outbid Threshold",
                custom_id="modal_outbidthreshold_reset_confirmation",
                style=disnake.TextInputStyle.single_line,
                placeholder="Confirm",
                required=False,
                min_length=7,
                max_length=7,
            ),
        ]
        await inter.response.send_modal(
            title="Edit Outbid Threshold",
            custom_id=f"{inter.id}outbidthreshold_modal",
            components=components,
        )

        try:
            modalinter: disnake.ModalInteraction = await self.bot.wait_for(
                "modal_submit",
                check=lambda i: i.custom_id == f"{inter.id}outbidthreshold_modal"
                and i.author.id == inter.author.id,
                timeout=180,
            )
        except asyncio.TimeoutError:
            raise FormTimeoutError

        if (
            modalinter.text_values["modal_outbidthreshold_reset_confirmation"]
            == "Confirm"
        ):
            inter.send("Outbid Threshold reset.", ephemeral=True)
            self.settings.outbidthreshold = self.settings.__fields__[
                "outbidthreshold"
            ].get_default()
            await self.commit_settings()
            await self.refresh_content(modalinter)
            return

        data = {
            "count": modalinter.text_values["modal_outbidthreshold_fee_count_input"],
        }

        for x in self.settings.coinconf:
            if (
                f"{x.label} Rate: {x.rate}"
                == modalinter.data["components"][0]["components"][0]["values"][0]
            ):
                data["type"] = x.to_dict()
                data["base"] = self.settings.coinconf.base.to_dict()
                data["isbase"] = x is self.settings.coinconf.base
        try:
            data["count"] = re.sub(r"[^\d]+", "", data["count"])
            data["count"] = int(data["count"])
        except ValueError:
            raise FormInvalidInputError(
                f"It seems your inputted fee count couldn't be converted to an integer, please ensure your "
                f"input only contains numbers."
            )
        self.settings.outbidthreshold = Coin.from_dict(data)
        await self.commit_settings()
        await self.refresh_content(modalinter)

    @disnake.ui.button(label="Back", style=disnake.ButtonStyle.grey, row=4)
    async def back(self, _: disnake.ui.Button, inter: disnake.MessageInteraction):
        await self.defer_to(SettingsNav, inter)

    # ==== handlers ====
    async def _text_select_channel(
        self, button: disnake.ui.Button, inter: disnake.MessageInteraction, setting: str
    ) -> Optional[List[int]]:
        button.disabled = True
        await self.refresh_content(inter)
        await inter.send(
            "Select a channel by sending a message to this channel. You can link a #channel.\n"
            "Type `reset` to unset the channel and disable this feature.",
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
                await inter.send(
                    "The channel has been unset, and feature disabled.", ephemeral=True
                )
                return None
            channel_id = ""
            if len(input_msg.channel_mentions) > 0:
                channel_id = str(input_msg.channel_mentions[0].id)
            else:
                result: disnake.TextChannel = await search_and_select(
                    inter,
                    self.guild.channels,
                    input_msg.content,
                    lambda c: c.name,
                    list_filter=lambda c: True
                    if isinstance(c, disnake.TextChannel)
                    else False,
                )
                channel_id = str(result.id)
            if channel_id:
                await inter.send("The channel id has been updated", ephemeral=True)
                return channel_id
            await inter.send(
                "No valid channel found. Use the button to try again.",
                ephemeral=True,
            )
            return setting
        except asyncio.TimeoutError:
            await inter.send(
                "No valid channel found. Use the button to try again.",
                ephemeral=True,
            )
            return setting
        finally:
            button.disabled = False

    # ==== content ====
    async def get_content(self):
        inputdict = deepcopy(self.inputtemplate)

        firstmax = max(len(x.durstr) for x in self.settings.listingdurs)
        secondmax = max(len(str(x)) for x in self.settings.listingdurs.values())
        listingdurstr = "\n".join(
            [
                f"{x.durstr:{firstmax}} - {y:{secondmax}} {y.type.prefix} fee"
                for x, y in self.settings.listingdurs.items()
            ]
        )

        firstmax = max(len(x) for x in self.settings.rarities)
        secondmax = max(len(str(x)) for x in self.settings.rarities.values())
        raritiesstr = "\n".join(
            [
                f"{x:{firstmax}} - {y:{secondmax}} {y.type.prefix} fee"
                for x, y in self.settings.rarities.items()
            ]
        )

        inputdict["main"][
            "title"
        ] = f"Server Settings ({self.guild.name}) / Auction House Settings"

        inputdict["main"]["descitems"].append(
            {
                "header": "__**Auction Listings Channel**__",
                "setting": f"<#{self.settings.ahfront}>",
                "desc": (
                    "This is the channel where newly created item listings will appear "
                    f"when posted.\n"
                ),
            }
        )

        inputdict["main"]["descitems"].append(
            {
                "header": "__**Auction Logging Channel**__",
                "setting": f"<#{self.settings.ahinternal}>",
                "desc": (
                    f"Setting this will enable auction logging, making it so all auction "
                    f"related actions are logged in the specified channel.\n"
                ),
            }
        )

        inputdict["main"]["descitems"].append(
            {
                "header": "__**Auction Menu Channel**__",
                "setting": f"<#{self.settings.ahback}>",
                "desc": (
                    f"Setting this will enable auction logging, making it so all auction "
                    f"related actions are logged in the specified channel.\n"
                ),
            }
        )

        inputdict["main"]["descitems"].append(
            {
                "header": "__**Auction Outbid Threshold**__",
                "setting": f"```{self.settings.outbidthreshold.prefixed_count}```",
                "desc": (
                    f"This setting determines the minimum amount a user must outbid the "
                    f"previous highest bid by.\n"
                ),
            }
        )

        inputdict["main"]["fielditems"].append(
            {
                "name": "__Listing Duration Options__",
                "value": (
                    f"```\n{listingdurstr}```"
                    f"These define what lengths of time players can list their items for "
                    f"on the auction house. You must have atleast one duration defined."
                ),
                "inline": True,
            }
        )

        inputdict["main"]["fielditems"].append(
            {
                "name": "__Item Rarity Options__",
                "value": (
                    f"```\n{raritiesstr}```"
                    f"These define what rarity of items players can post "
                    f"on the auction house. You must have atleast one rarity defined."
                ),
                "inline": True,
            }
        )

        embeds = self.format_settings_overflow(inputdict)
        embeds = [disnake.Embed.from_dict(x) for x in embeds]
        return {"embeds": embeds}


class AuctionDurationsView(SettingsMenuBase, SelectandModify):
    def __init__(self, owner, timeout):
        self.matched: Duration = None
        self.matchindex: int = None
        super().__init__(owner=owner, timeout=timeout)

    # ==== ui ====
    @disnake.ui.button(label="Back", style=disnake.ButtonStyle.grey, row=4)
    async def back(self, _: disnake.ui.Button, inter: disnake.Interaction):
        await self.defer_to(AuctionSettingsView, inter)

    # ==== overloaded methods ====
    async def confirmation_callback(
        self, inter: disnake.MessageInteraction, modalinter: disnake.ModalInteraction
    ):
        if modalinter.text_values["reset_confirmation_input"] == "Confirm":
            await inter.send("Listing duration configuration reset.", ephemeral=True)
            self.selected = self.matched = self.matchindex = None
            self.settings.listingdurs = self.settings.__fields__[
                "listingdurs"
            ].get_default()
            self.refresh_select()
            self.process_selection()
            await self.commit_settings()
        else:
            await inter.send("Config reset canceled", ephemeral=True)
        await self.refresh_content(modalinter)

    # ==== handlers ====
    def process_selection(self):
        matched = False
        for enum, item in enumerate(self.settings.listingdurs.durlist):
            if item.label == self.selected:
                self.matched = item
                self.matchindex = enum
                matched = True

        # Clear all modification buttons before re-adding the appropriate ones
        self._clear_specific_items(AddButton, EditButton, RemoveButton)

        # Check whether we've reached the item cap
        # and add "Add" button if not
        if len(self.settings.listingdurs.durlist) < 25:
            self.add_item(AddButton(label="Add Duration"))
        elif len(self.settings.listingdurs.durlist) >= 25:
            self._clear_specific_items(AddButton)

        if self.matched is not None or matched == True:
            # Check whether self.matched is None
            # we only add "Edit" or "Remove" if not
            self.add_item(EditButton(label="Edit Duration"))
            self.add_item(RemoveButton(label="Remove Duration"))

            # Check whether there is only one item
            # if so, remove all "Remove" buttons
            if len(self.settings.listingdurs.durlist) == 1:
                self._clear_specific_items(RemoveButton)

            # Check whether an item is selected
            # we remove the "remove" button if not
            if self.matched not in self.settings.listingdurs.durlist:
                self._clear_specific_items(RemoveButton)

            # Check whether anything is selected
            # if not, we remove all RemoveButtons and EditButtons
            if not matched:
                self._clear_specific_items(EditButton, RemoveButton)

    async def add(self, inter: disnake.MessageInteraction):
        if len(self.settings.listingdurs.durlist) >= 25:
            return
        await inter.response.send_modal(
            title="Add Duration",
            custom_id=f"{inter.id}add_duration_modal",
            components=self.setup_duration_modal_components(),
        )

        try:
            modalinter: disnake.ModalInteraction = await self.bot.wait_for(
                "modal_submit",
                check=lambda i: i.custom_id == f"{inter.id}add_duration_modal"
                and i.author.id == inter.author.id,
                timeout=180,
            )
        except asyncio.TimeoutError:
            raise FormTimeoutError

        data = {
            "duration": modalinter.text_values["modal_dur_input"],
            "fee": {"count": modalinter.text_values["modal_dur_fee_count_input"]},
        }

        for x in self.settings.coinconf:
            if (
                f"{x.label} Rate: {x.rate}"
                == modalinter.data["components"][2]["components"][0]["values"][0]
            ):
                data["fee"]["type"] = x.to_dict()
                data["fee"]["base"] = self.settings.coinconf.base.to_dict()
                data["fee"]["isbase"] = x is self.settings.coinconf.base
        try:
            data["duration"] = re.sub(r"[^\d]+", "", data["duration"])
            data["duration"] = int(data["duration"])

        except ValueError:
            raise FormInvalidInputError(
                f"It seems your inputted duration couldn't be converted to an integer, please ensure your "
                f"input only contains numbers."
            )
        try:
            data["fee"]["count"] = re.sub(r"[^\d]+", "", data["fee"]["count"])
            data["fee"]["count"] = int(data["fee"]["count"])
        except ValueError:
            raise FormInvalidInputError(
                f"It seems your inputted fee count couldn't be converted to an integer, please ensure your "
                f"input only contains numbers."
            )
        self.settings.listingdurs.durlist.append(Duration.from_dict(data))
        self.settings.listingdurs.sort_items()
        self.matchindex = (
            x
            for x, y in enumerate(self.settings.listingdurs.durlist)
            if self.matched is y
        )
        await self.commit_settings()
        self.refresh_select()
        await self.refresh_content(modalinter)

    async def edit(self, inter: disnake.MessageInteraction):
        if len(self.settings.listingdurs.durlist) >= 25:
            return
        await inter.response.send_modal(
            title="Edit Duration",
            custom_id=f"{inter.id}edit_duration_modal",
            components=self.setup_duration_modal_components(True),
        )

        try:
            modalinter: disnake.ModalInteraction = await self.bot.wait_for(
                "modal_submit",
                check=lambda i: i.custom_id == f"{inter.id}edit_duration_modal"
                and i.author.id == inter.author.id,
                timeout=180,
            )
        except asyncio.TimeoutError:
            raise FormTimeoutError

        data = {
            "duration": modalinter.text_values["modal_dur_input"],
            "fee": {"count": modalinter.text_values["modal_dur_fee_count_input"]},
        }

        for x in self.settings.coinconf:
            if (
                f"{x.label} Rate: {x.rate}"
                == modalinter.data["components"][2]["components"][0]["values"][0]
            ):
                data["fee"]["type"] = x.to_dict()
                data["fee"]["base"] = self.settings.coinconf.base.to_dict()
                data["fee"]["isbase"] = x is self.settings.coinconf.base
        try:
            data["duration"] = re.sub(r"[^\d]+", "", data["duration"])
            data["duration"] = int(data["duration"])
        except ValueError:
            raise FormInvalidInputError(
                f"It seems your inputted duration couldn't be converted to an integer, please ensure your "
                f"input only contains numbers."
            )
        for x in self.settings.listingdurs:
            if x == data["duration"] and x != self.matched:
                raise FormInvalidInputError(
                    f"Multiple durations cannot share the same length, please provide a unique duration"
                )
        try:
            data["fee"]["count"] = re.sub(r"[^\d]+", "", data["fee"]["count"])
            data["fee"]["count"] = int(data["fee"]["count"])
        except ValueError:
            raise FormInvalidInputError(
                f"It seems your inputted fee count couldn't be converted to an integer, please ensure your "
                f"input only contains numbers."
            )
        self.settings.listingdurs.durlist[self.matchindex] = Duration.from_dict(data)
        self.matched = self.settings.listingdurs.durlist[self.matchindex]
        self.settings.listingdurs.sort_items()
        self.matchindex = (
            x
            for x, y in enumerate(self.settings.listingdurs.durlist)
            if self.matched is y
        )
        await self.commit_settings()
        self.refresh_select()
        await self.refresh_content(modalinter)

    async def remove(self, inter: disnake.MessageInteraction):
        await inter.response.send_modal(
            title="Confirmation",
            custom_id=f"{inter.id}duration_removal_confirm",
            components=disnake.ui.TextInput(
                label="Confirm Duration Removal",
                custom_id="removal_confirm",
                style=disnake.TextInputStyle.single_line,
                placeholder="Confirm",
                required=True,
                min_length=7,
                max_length=7,
            ),
        )
        try:
            modalinter: disnake.ModalInteraction = await self.bot.wait_for(
                "modal_submit",
                check=lambda i: i.custom_id == f"{inter.id}duration_removal_confirm"
                and i.author.id == inter.author.id,
                timeout=180,
            )
        except asyncio.TimeoutError:
            raise FormTimeoutError

        if modalinter.text_values["removal_confirm"] == "Confirm":
            await inter.send("Removal confirmed", ephemeral=True)
            self.settings.listingdurs.durlist.remove(self.matched)
            self.selected = self.matched = self.matchindex = None
            self.settings.listingdurs.sort_items()
            await self.commit_settings()
            self.refresh_select()
            self.process_selection()
        else:
            await inter.send("Removal canceled", ephemeral=True)
        await self.refresh_content(modalinter)

    # ==== helpers ====
    def setup_duration_modal_components(
        self, editing: bool = False
    ) -> List[Union[disnake.ui.TextInput, disnake.ui.Select]]:
        options = []
        input = (
            self.matched.to_dict()
            if editing
            else {"duration": "", "fee": {"count": ""}}
        )
        for x in self.settings.coinconf:
            selected = (
                x.name == input["fee"]["type"]["name"]
                if "type" in input["fee"]
                else x is self.settings.coinconf.base
            )
            options.append(
                disnake.SelectOption(
                    label=f"{x.label} Rate: {x.rate}", emoji=x.emoji, default=selected
                )
            )
        return [
            disnake.ui.TextInput(
                label="Duration Description",
                custom_id="modal_dur_desc",
                style=disnake.TextInputStyle.multi_line,
                value=(
                    f"Durations are stored as seconds, if you are unsure how many seconds are "
                    f"in the length of time you wish to set, use google to get a rough estimate "
                    f"then submit this form, the settings menu will show you your exact measured duration "
                    f"in text for you to confirm, and tweak to be just right."
                ),
                required=False,
            ),
            disnake.ui.TextInput(
                label="Duration (In seconds)",
                custom_id="modal_dur_input",
                style=disnake.TextInputStyle.single_line,
                placeholder="2628000",
                value=input["duration"],
            ),
            disnake.ui.Select(
                custom_id="modal_dur_cointype_select",
                placeholder="Select Currency Type",
                options=options,
            ),
            disnake.ui.TextInput(
                label="Coin Count Description",
                custom_id="modal_dur_fee_count_desc",
                style=disnake.TextInputStyle.multi_line,
                value=(
                    f"This is the amount of currency for the auction fee to be tied to this duration "
                    f"option."
                ),
                required=False,
            ),
            disnake.ui.TextInput(
                label="Coin Count",
                custom_id="modal_dur_fee_count_input",
                style=disnake.TextInputStyle.single_line,
                placeholder="750",
                value=input["fee"]["count"],
                max_length=7,
            ),
        ]

    # ==== content ====
    def refresh_select(self):
        """Update the options in the Duration select to reflect the currently selected values."""
        self.select_items.options.clear()

        for item in self.settings.listingdurs.durlist:  # display highest-first
            selected = self.matched is item
            self.select_items.add_option(label=item.label, default=selected)

    async def _before_send(self):
        for x in self.children:
            if hasattr(x, "label"):
                if x.label == "Reset Settings":
                    x.label = "Reset Listing Durations"
            if hasattr(x, "placeholder"):
                if x.placeholder == "Select Item":
                    x.placeholder = "Select Duration Template"
        self.add_item(AddButton(label="Add Duration"))
        self.refresh_select()

    async def get_content(self):
        inputdict = deepcopy(self.inputtemplate)

        firstmax = max(len(x.durstr) for x in self.settings.listingdurs)
        secondmax = max(len(str(x)) for x in self.settings.listingdurs.values())
        listingdurstr = "\n".join(
            [
                f"{x.durstr:{firstmax}} - {y:{secondmax}} {y.type.prefix} fee"
                for x, y in self.settings.listingdurs.items()
            ]
        )

        inputdict["main"][
            "title"
        ] = f"Server Settings ({self.guild.name}) / Auction Listing Duration Settings"
        inputdict["main"]["descitems"].append(
            {
                "header": "__**Listing Duration Options**__",
                "settings": f"{listingdurstr}",
                "desc": (
                    f"These define what lengths of time players can list their items for "
                    f"on the auction house. You must have atleast one duration defined."
                ),
            }
        )

        embeds = self.format_settings_overflow(inputdict)
        embeds = [disnake.Embed.from_dict(x) for x in embeds]
        return {"embeds": embeds}


class AuctionRaritiesView(SettingsMenuBase, SelectandModify):
    def __init__(self, owner, timeout):
        self.matched: Duration = None
        self.matchindex: int = None
        super().__init__(owner=owner, timeout=timeout)

    # ==== ui ====
    @disnake.ui.button(label="Back", style=disnake.ButtonStyle.grey, row=4)
    async def back(self, _: disnake.ui.Button, inter: disnake.Interaction):
        await self.defer_to(AuctionSettingsView, inter)

    # ==== overloaded methods ====
    async def confirmation_callback(
        self, inter: disnake.MessageInteraction, modalinter: disnake.ModalInteraction
    ):
        if modalinter.text_values["reset_confirmation_input"] == "Confirm":
            await inter.send("Listing rarity configuration reset.", ephemeral=True)
            self.selected = self.matched = self.matchindex = None
            self.settings.rarities = self.settings.__fields__["rarities"].get_default()
            self.refresh_select()
            self.process_selection()
            await self.commit_settings()
        else:
            await inter.send("Config reset canceled", ephemeral=True)
        await self.refresh_content(modalinter)

    # ==== handlers ====
    def process_selection(self):
        matched = False
        for enum, item in enumerate(self.settings.rarities):
            if item.label == self.selected:
                self.matched = item
                self.matchindex = enum
                matched = True

        # Clear all modification buttons before re-adding the appropriate ones
        self._clear_specific_items(AddButton, EditButton, RemoveButton)

        # Check whether we've reached the item cap
        # and add "Add" button if not
        if len(self.settings.rarities.rarlist) < 25:
            self.add_item(AddButton(label="Add Rarity"))
        elif len(self.settings.rarities.rarlist) >= 25:
            self._clear_specific_items(AddButton)

        if self.matched is not None or matched == True:
            # Check whether self.matched is None
            # we only add "Edit" or "Remove" if not
            self.add_item(EditButton(label="Edit Rarity"))
            self.add_item(RemoveButton(label="Remove Rarity"))

            # Check whether there is only one item
            # if so, remove all "Remove" buttons
            if len(self.settings.rarities.rarlist) == 1:
                self._clear_specific_items(RemoveButton)

            # Check whether an item is selected
            # we remove the "remove" button if not
            if self.matched not in self.settings.rarities.rarlist:
                self._clear_specific_items(EditButton, RemoveButton)

            # Check whether anything is selected
            # if not, we remove all RemoveButtons and EditButtons
            if not matched:
                self._clear_specific_items(EditButton, RemoveButton)

    async def add(self, inter: disnake.MessageInteraction):
        if len(self.settings.listingdurs.durlist) >= 25:
            return
        await inter.response.send_modal(
            title="Add Rarity",
            custom_id=f"{inter.id}add_rarity_modal",
            components=self.setup_rarity_modal_components(),
        )

        try:
            modalinter: disnake.ModalInteraction = await self.bot.wait_for(
                "modal_submit",
                check=lambda i: i.custom_id == f"{inter.id}add_rarity_modal"
                and i.author.id == inter.author.id,
                timeout=180,
            )
        except asyncio.TimeoutError:
            raise FormTimeoutError

        data = {
            "rarity": modalinter.text_values["modal_rar_input"],
            "fee": {"count": modalinter.text_values["modal_rar_fee_count_input"]},
        }

        for x in self.settings.coinconf:
            if (
                f"{x.label} Rate: {x.rate}"
                == modalinter.data["components"][1]["components"][0]["values"][0]
            ):
                data["fee"]["type"] = x.to_dict()
                data["fee"]["base"] = self.settings.coinconf.base.to_dict()
                data["fee"]["isbase"] = x is self.settings.coinconf.base
        for x in self.settings.rarities:
            if x == data["rarity"]:
                raise FormInvalidInputError(
                    f"Multiple rarities cannot share the same name, please provide a unique name"
                )
        try:
            data["fee"]["count"] = re.sub(r"[^\d]+", "", data["fee"]["count"])
            data["fee"]["count"] = int(data["fee"]["count"])
        except ValueError:
            raise FormInvalidInputError(
                f"It seems your inputted fee count couldn't be converted to an integer, please ensure your "
                f"input only contains numbers."
            )
        self.settings.rarities.rarlist.append(Rarity.from_dict(data))
        self.settings.rarities.sort_items()
        self.matchindex = (
            x for x, y in enumerate(self.settings.rarities) if self.matched is y
        )
        await self.commit_settings()
        self.refresh_select()
        await self.refresh_content(modalinter)

    async def edit(self, inter: disnake.MessageInteraction):
        if len(self.settings.listingdurs.durlist) >= 25:
            return
        await inter.response.send_modal(
            title="Edit Rarity",
            custom_id=f"{inter.id}edit_rarity_modal",
            components=self.setup_rarity_modal_components(True),
        )

        try:
            modalinter: disnake.ModalInteraction = await self.bot.wait_for(
                "modal_submit",
                check=lambda i: i.custom_id == f"{inter.id}edit_rarity_modal"
                and i.author.id == inter.author.id,
                timeout=180,
            )
        except asyncio.TimeoutError:
            raise FormTimeoutError

        data = {
            "rarity": modalinter.text_values["modal_rar_input"],
            "fee": {"count": modalinter.text_values["modal_rar_fee_count_input"]},
        }

        for x in self.settings.coinconf:
            if (
                f"{x.label} Rate: {x.rate}"
                == modalinter.data["components"][1]["components"][0]["values"][0]
            ):
                data["fee"]["type"] = x.to_dict()
                data["fee"]["base"] = self.settings.coinconf.base.to_dict()
                data["fee"]["isbase"] = x is self.settings.coinconf.base
        for x in self.settings.rarities:
            if x == data["rarity"] and data["rarity"] != self.matched:
                raise FormInvalidInputError(
                    f"Multiple rarities cannot share the same name, please provide a unique name"
                )
        try:
            data["fee"]["count"] = re.sub(r"[^\d]+", "", data["fee"]["count"])
            data["fee"]["count"] = int(data["fee"]["count"])
        except ValueError:
            raise FormInvalidInputError(
                f"It seems your inputted fee count couldn't be converted to an integer, please ensure your "
                f"input only contains numbers."
            )
        self.settings.rarities.rarlist[self.matchindex] = Rarity.from_dict(data)
        self.matched = self.settings.rarities.rarlist[self.matchindex]
        self.settings.rarities.sort_items()
        self.matchindex = (
            x for x, y in enumerate(self.settings.rarities.rarlist) if self.matched is y
        )
        await self.commit_settings()
        self.refresh_select()
        await self.refresh_content(modalinter)

    async def remove(self, inter: disnake.MessageInteraction):
        await inter.response.send_modal(
            title="Confirmation",
            custom_id=f"{inter.id}rarity_removal_confirm",
            components=disnake.ui.TextInput(
                label="Confirm Rarity Removal",
                custom_id="removal_confirm",
                style=disnake.TextInputStyle.single_line,
                placeholder="Confirm",
                required=True,
                min_length=7,
                max_length=7,
            ),
        )
        try:
            modalinter: disnake.ModalInteraction = await self.bot.wait_for(
                "modal_submit",
                check=lambda i: i.custom_id == f"{inter.id}rarity_removal_confirm"
                and i.author.id == inter.author.id,
                timeout=180,
            )
        except asyncio.TimeoutError:
            raise FormTimeoutError

        if modalinter.text_values["removal_confirm"] == "Confirm":
            await inter.send("Removal confirmed", ephemeral=True)
            self.settings.rarities.rarlist.remove(self.matched)
            self.selected = self.matched = self.matchindex = None
            self.settings.rarities.sort_items()
            await self.commit_settings()
            self.refresh_select()
            self.process_selection()
        else:
            await inter.send("Removal canceled", ephemeral=True)
        await self.refresh_content(modalinter)

    # ==== helpers ====
    def setup_rarity_modal_components(
        self, editing: bool = False
    ) -> List[Union[disnake.ui.TextInput, disnake.ui.Select]]:
        input = (
            self.matched.to_dict() if editing else {"rarity": "", "fee": {"count": ""}}
        )
        options = []
        for x in self.settings.coinconf:
            selected = (
                x.name == input["fee"]["type"]["name"]
                if "type" in input["fee"]
                else x is self.settings.coinconf.base
            )
            options.append(
                disnake.SelectOption(
                    label=f"{x.label} Rate: {x.rate}", emoji=x.emoji, default=selected
                )
            )
        return [
            disnake.ui.TextInput(
                label="Rarity Name",
                custom_id="modal_rar_input",
                style=disnake.TextInputStyle.single_line,
                placeholder="Legendary",
                value=input["rarity"],
            ),
            disnake.ui.Select(
                custom_id="modal_rar_cointype_select",
                placeholder="Select Currency Type",
                options=options,
            ),
            disnake.ui.TextInput(
                label="Coin Count Description",
                custom_id="modal_rar_fee_count_desc",
                style=disnake.TextInputStyle.multi_line,
                value=(
                    f"This is the amount of currency for the auction fee to be tied to this duration "
                    f"option."
                ),
                required=False,
            ),
            disnake.ui.TextInput(
                label="Coin Count",
                custom_id="modal_rar_fee_count_input",
                style=disnake.TextInputStyle.single_line,
                placeholder="750",
                value=input["fee"]["count"],
                max_length=7,
            ),
        ]

    # ==== content ====
    def refresh_select(self):
        """Update the options in the Duration select to reflect the currently selected values."""
        self.select_items.options.clear()

        for item in self.settings.rarities.rarlist:  # display highest-first
            selected = self.matched is item
            self.select_items.add_option(label=item.label, default=selected)

    async def _before_send(self):
        for x in self.children:
            if hasattr(x, "label"):
                if x.label == "Reset Settings":
                    x.label = "Reset Rarities"
            if hasattr(x, "placeholder"):
                if x.placeholder == "Select Item":
                    x.placeholder = "Select Rarity Template"
        self.add_item(AddButton(label="Add Rarity"))
        self.refresh_select()

    async def get_content(self):
        inputdict = deepcopy(self.inputtemplate)

        firstmax = max(len(x) for x in self.settings.rarities)
        secondmax = max(len(str(x)) for x in self.settings.rarities.values())
        raritiesstr = "\n".join(
            [
                f"{x:{firstmax}} - {y:{secondmax}} {y.type.prefix} fee"
                for x, y in self.settings.rarities.items()
            ]
        )

        inputdict["main"][
            "title"
        ] = f"Server Settings ({self.guild.name}) / Auction Rarity Settings"
        inputdict["main"]["descitems"].append(
            {
                "header": "__**Item Rarity Options**__",
                "settings": f"{raritiesstr}",
                "desc": (
                    f"These define what rarity of items players can post "
                    f"on the auction house. You must have atleast one rarity defined."
                ),
            }
        )

        embeds = self.format_settings_overflow(inputdict)
        embeds = [disnake.Embed.from_dict(x) for x in embeds]
        return {"embeds": embeds}


class CharacterLogSettingsView(SettingsMenuBase):

    # ==== ui ====
    @disnake.ui.button(label="Set XP Label", style=disnake.ButtonStyle.primary)
    async def xp_label_modal(
        self, _: disnake.ui.Button, inter: disnake.MessageInteraction
    ):
        components = [
            disnake.ui.TextInput(
                style=disnake.TextInputStyle.single_line,
                label="Set XP Label",
                placeholder="badges",
                custom_id="settings_xp_label_set",
                value=self.settings.xplabel,
                required=False,
            ),
            disnake.ui.TextInput(
                style=disnake.TextInputStyle.single_line,
                label="Reset to Default",
                placeholder='Type "Confirm" here to reset the XP label to the default',
                custom_id="settings_xp_label_reset",
                required=False,
                max_length=7,
            ),
        ]
        await inter.response.send_modal(
            custom_id=f"{inter.id}settings_xp_label_modal",
            title='"Units of XP" Label:',
            components=components,
        )
        try:
            modalinter: disnake.ModalInteraction = await self.bot.wait_for(
                "modal_submit",
                check=lambda i: i.custom_id == f"{inter.id}settings_xp_label_modal"
                and i.author.id == inter.author.id,
                timeout=180,
            )

            if modalinter.text_values["settings_xp_label_reset"] == "Confirm":
                await inter.send(
                    f"{self.settings.xplabel} requirements reset to default",
                    ephemeral=True,
                )
                self.settings.xplabel = self.settings.__fields__[
                    "xplabel"
                ].get_default()
                await self.commit_settings()
                await self.refresh_content(modalinter)
                return
            if len(modalinter.text_values["settings_xp_label_set"]) > 0:
                self.settings.xplabel = modalinter.text_values["settings_xp_label_set"]
            await self.commit_settings()
            await self.refresh_content(modalinter)
        except asyncio.TimeoutError:
            raise FormTimeoutError

    @disnake.ui.button(
        label="Configure XP requirements", style=disnake.ButtonStyle.primary
    )
    async def xp_template_modal(
        self, _: disnake.ui.Button, inter: disnake.MessageInteraction
    ):
        valuestr = self.settings.xptemplate.to_str()
        components = [
            disnake.ui.TextInput(
                style=disnake.TextInputStyle.multi_line,
                label="Description",
                custom_id="settings_xp_template_desc",
                value=(
                    f"Edit the {self.settings.xplabel} requirements shown below. The template is shown as a line separated "
                    f"list of [level name]:<{self.settings.xplabel} threshold>. The level name may"
                    f" be removed or omitted and if done, it will reset to the default. All data entered"
                    f" below is assumed to be in ascending numerical order, starting at level one\n"
                ),
                required=False,
            ),
            disnake.ui.TextInput(
                style=disnake.TextInputStyle.multi_line,
                label=f"Server {self.settings.xplabel} requirements",
                placeholder=(
                    f"Line separated list of values"
                    f"You can also provide a key to name each level\n"
                    f"[key]:value\n"
                    f":value\n"
                    f"value"
                ),
                custom_id="settings_xp_template_set",
                value=valuestr,
                required=False,
            ),
            disnake.ui.TextInput(
                style=disnake.TextInputStyle.single_line,
                label="Reset to Default",
                placeholder=f'Type "Confirm" here to reset the {self.settings.xplabel} requirements to the default',
                custom_id="settings_xp_template_reset",
                required=False,
                max_length=7,
            ),
        ]
        await inter.response.send_modal(
            custom_id=f"{inter.id}settings_xp_template_modal",
            title=f"Edit {self.settings.xplabel} Requirements",
            components=components,
        )
        try:
            modalinter: disnake.ModalInteraction = await self.bot.wait_for(
                "modal_submit",
                check=lambda i: i.custom_id == f"{inter.id}settings_xp_template_modal"
                and i.author.id == inter.author.id,
                timeout=180,
            )

            if modalinter.text_values["settings_xp_template_reset"] == "Confirm":
                await inter.send("XP template reset to default", ephemeral=True)
                self.settings.xptemplate = self.settings.__fields__[
                    "xptemplate"
                ].get_default()
                await self.commit_settings()
                await self.refresh_content(modalinter)
                return
            if len(modalinter.text_values["settings_xp_template_set"]) > 0:
                self.settings.xptemplate = XPConfig.from_str(
                    modalinter.text_values["settings_xp_template_set"]
                )
            await self.commit_settings()
            await self.refresh_content(modalinter)
        except asyncio.TimeoutError:
            raise FormTimeoutError

    @disnake.ui.button(label="Back", style=disnake.ButtonStyle.grey, row=4)
    async def back(self, _: disnake.ui.Button, inter: disnake.MessageInteraction):
        await self.defer_to(SettingsNav, inter)

    # ==== content ====
    async def get_content(self) -> Mapping:
        inputdict = deepcopy(self.inputtemplate)
        ordinal = lambda n: "%d%s" % (
            n,
            "tsnrhtdd"[(n // 10 % 10 != 1) * (n % 10 < 4) * n % 10 :: 4],
        )
        maxes = [
            max(len(ordinal(x + 1)) for x, y in enumerate(self.settings.xptemplate)),
            max(len(str(x)) for x in self.settings.xptemplate.values()),
            max(len(str(x)) for x in self.settings.xptemplate),
        ]
        xptemplate = "Level : Level Name : Requirement\n"
        xptemplate += simple_tabulate_str(
            [
                f"{x+1:{maxes[0]}} : {z:^{maxes[1]}} : {y:<{maxes[2]}}"
                for x, (y, z) in enumerate(self.settings.xptemplate.items())
            ],
            2,
        )
        inputdict["main"][
            "title"
        ] = f"Server Settings ({self.guild.name}) / Character Log Settings"
        inputdict["main"]["descitems"].append(
            {
                "header": f'__**"Units of XP" Label:**__',
                "setting": f'"{self.settings.xplabel}"',
                "desc": (
                    f"*This setting will replace all uses of the word {self.settings.xplabel} "
                    f"with whatever this is set to.*"
                ),
            }
        )
        inputdict["main"]["fielditems"].append(
            {
                "name": f"__{self.settings.xplabel} Requirements:__",
                "value": (
                    f"```ansi\n\u001b[1;40;32m{xptemplate}```"
                    f"*This setting determines how much/many {self.settings.xplabel}(es) "
                    f"are required for each level.*"
                ),
                "inline": True,
            }
        )
        embeds = self.format_settings_overflow(inputdict)
        embeds = [disnake.Embed.from_dict(x) for x in embeds]
        return {"embeds": embeds}


class BotSettingsView(SettingsMenuBase):
    select_dm_roles: disnake.ui.Select  # type: ignore # make the type checker happy
    TOO_MANY_ROLES_SENTINEL = "__special:too_many_roles"

    # ==== ui ====
    @disnake.ui.select(placeholder="Select DM Roles", min_values=0)
    async def select_dm_roles(
        self, select: disnake.ui.Select, inter: disnake.MessageInteraction
    ):
        if len(select.values) == 1 and select.values[0] == self.TOO_MANY_ROLES_SENTINEL:
            role_ids = await self._text_select_dm_roles(inter)
        else:
            role_ids = list(map(int, select.values))
        self.settings.dmroles = role_ids or None  # type: ignore
        self._refresh_dm_role_select()
        await self.commit_settings()
        await self.refresh_content(inter)

    @disnake.ui.button(label="Configure Class List", style=disnake.ButtonStyle.primary)
    async def select_classes(
        self, _: disnake.ui.Button, inter: disnake.MessageInteraction
    ):
        components = [
            disnake.ui.TextInput(
                style=disnake.TextInputStyle.multi_line,
                label="Description",
                placeholder="A list of class names separated by either commas or new lines.",
                value=(
                    f"Each class must be on a separate line below. "
                    f"Any changes made will be applied to the server class list."
                ),
                custom_id="settings_classes_desc",
                required=False,
            ),
            disnake.ui.TextInput(
                style=disnake.TextInputStyle.multi_line,
                label="Class List Modification",
                placeholder="A list of class names separated by either commas or new lines.",
                value="\n".join(self.settings.classlist),
                custom_id="settings_classes_list",
                required=False,
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
                await inter.send("Class list reset to defaults", ephemeral=True)
                self.settings.classlist = self.settings.__fields__[
                    "classlist"
                ].get_default()
                await self.commit_settings()
                await self.refresh_content(modalinter)
                return
            if len(modalinter.text_values["settings_classes_list"]) > 0:
                addclasses = modalinter.text_values[
                    "settings_classes_list"
                ].splitlines()
                addclasses.sort()
                self.settings.classlist = addclasses
            await self.commit_settings()
            await self.refresh_content(modalinter)
        except asyncio.TimeoutError:
            raise FormTimeoutError

    @disnake.ui.button(label="Back", style=disnake.ButtonStyle.grey, row=4)
    async def back(self, _: disnake.ui.Button, inter: disnake.MessageInteraction):
        await self.defer_to(SettingsNav, inter)

    # ==== handlers ====
    async def _text_select_dm_roles(
        self, inter: disnake.MessageInteraction
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
            return self.settings.dmroles  # type: ignore
        except asyncio.TimeoutError:
            await inter.send(
                "No valid roles found. Use the select menu to try again.",
                ephemeral=True,
            )
            return self.settings.dmroles  # type: ignore
        finally:
            self.select_dm_roles.disabled = False

    # ==== content ====
    def _refresh_dm_role_select(self):
        """Update the options in the DM Role select to reflect the currently selected values."""
        self.select_dm_roles.options.clear()
        if len(self.guild.roles) > 25:
            self.select_dm_roles.add_option(
                label="Whoa, this server has a lot of roles! Click here to select them.",
                value=self.TOO_MANY_ROLES_SENTINEL,
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
        inputdict = deepcopy(self.inputtemplate)
        # classlist = natural_join([_class for _class in self.settings.classlist], "and")
        classlist = simple_tabulate_str(
            [_class for _class in self.settings.classlist], 3
        )
        if not self.settings.dmroles:
            dmroles = f"**Dungeon Master, DM, Game Master, or GM**\n"
            dmrolesdesc = (
                f"*Any user with a role named one of these will be considered a DM. This lets them adjust players "
                f"{self.settings.xplabel} counts.*"
            )
        else:
            dmroles = natural_join(
                [f"<@&{role_id}>" for role_id in self.settings.dmroles], "and"
            )
            dmrolesdesc = (
                f"*Any user with at least one of these roles will be considered a DM. This lets them adjust players "
                f"{self.settings.xplabel} counts.*"
            )
        inputdict["main"][
            "title"
        ] = f"Server Settings ({self.guild.name}) / General Bot Settings"
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
        inputdict["main"]["fielditems"].append(
            {
                "name": f"\n__Server Class List:__",
                "value": (
                    f"```ansi\n\u001b[1;40;32m{classlist}```\n"
                    f"*This is a list of classes that are allowed for play in this server."
                    f"Any class listed here will be selectable when creating a character"
                    f"log.*"
                ),
                "inline": True,
            }
        )
        embeds = self.format_settings_overflow(inputdict)
        embeds = [disnake.Embed.from_dict(x) for x in embeds]
        return {"embeds": embeds}
