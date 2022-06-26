import abc
import asyncio
from contextlib import suppress
from copy import deepcopy
from random import randint
import re
from typing import TYPE_CHECKING, Any, Dict, List, Mapping, Optional, TypeVar, Union
import disnake
import emoji
import inflect
from utils.functions import (
    has_unicode_emote,
    natural_join,
    simple_tabulate_str,
    truncate_list,
)
from utils.models.errors import FormInvalidInputError, FormTimeoutError
from utils.models.settings.coin_docs import BaseCoin, CoinType
from utils.models.settings.guild import XPConfig, ServerSettings

from utils.ui.menu import MenuBase


_LabyrinthianT = TypeVar("_LabyrinthianT", bound=disnake.Client)
if TYPE_CHECKING:
    from bot import Labyrinthian

    _LabyrinthianT = Labyrinthian


TOO_MANY_ROLES_SENTINEL = "__special:too_many_roles"


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
        style=disnake.ButtonStyle.primary, label="Auction House Settings", disabled=True
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

    async def get_content(self) -> Mapping:
        p = inflect.engine()
        inputdict = deepcopy(inputtemplate)

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


class CoinPurseSettingsView(SettingsMenuBase):
    def __init__(self, owner, timeout):
        self.selected: str = None
        self.matched: Union[BaseCoin, CoinType] = None
        super().__init__(owner=owner, timeout=timeout)

    # ==== ui ====
    @disnake.ui.button(label="Reset Coin Config", style=disnake.ButtonStyle.red, row=0)
    async def reset_coinconf(
        self, _: disnake.ui.Button, inter: disnake.MessageInteraction
    ):
        await inter.response.send_modal(
            title="Confirm Config Reset",
            custom_id=f"{inter.id}coinconf_reset_modal",
            components=disnake.ui.TextInput(
                label="Confirmation:",
                custom_id="coinconf_reset_modal_confirmation",
                placeholder="Confirm",
                min_length=7,
                max_length=7,
            ),
        )
        try:
            modalinter: disnake.ModalInteraction = await self.bot.wait_for(
                "modal_submit",
                check=lambda i: i.custom_id == f"{inter.id}coinconf_reset_modal"
                and i.author.id == inter.author.id,
                timeout=180,
            )
        except asyncio.TimeoutError:
            raise FormTimeoutError

        if modalinter.text_values["coinconf_reset_modal_confirmation"] == "Confirm":
            self.settings.coinconf = self.settings.__fields__["coinconf"].get_default()
            await inter.send("Coin configuration reset.", ephemeral=True)
        else:
            await inter.send("Config reset canceled", ephemeral=True)

        self._refresh_cointype_select()
        await self.commit_settings()
        await self.refresh_content(modalinter)

    @disnake.ui.select(
        placeholder="Select Currency Denomination", min_values=1, max_values=1, row=2
    )
    async def select_cointype(
        self, select: disnake.ui.Select, inter: disnake.MessageInteraction
    ):
        if select.values[0] != self.selected:
            self.selected = select.values[0]
            self.process_selection(select.values[0])
            self._refresh_cointype_select()
            await self.refresh_content(inter)

    @disnake.ui.button(label="Back", style=disnake.ButtonStyle.grey, row=4)
    async def back(self, _: disnake.ui.Button, inter: disnake.Interaction):
        await self.defer_to(SettingsNav, inter)

    # ==== handlers ====
    def process_selection(self, input: str):
        for type in self.settings.coinconf:
            print(type)
            if type.label == input:
                self.matched = type
                print(type)

        # Clear all Coin modification buttons before re-adding the appropriate ones
        self.clear_specific_items(AddCoin, EditCoin, RemoveCoin)

        # Check whether we've reached the CoinType cap
        # and add AddCoin if not
        if len(self.settings.coinconf.types) < 24:
            self.add_item(AddCoin(self.bot))
        elif len(self.settings.coinconf.types) >= 24:
            self.clear_specific_items(AddCoin)

        # Check whether we matched with a BaseCoin or a CoinType
        # if BaseCoin, we only add EditCoin button
        # if CoinType, we add both EditCoin and RemoveCoin buttons
        if isinstance(self.matched, BaseCoin):
            self.add_item(EditCoin(self.bot, self.matched))
        elif isinstance(self.matched, CoinType):
            self.add_item(EditCoin(self.bot, self.matched))
            self.add_item(RemoveCoin(self.bot, self.matched))

        # Check whether there are any existing CoinTypes
        # and remove all RemoveCoin buttons if not
        # this is a redunant check incase self.matched isn't accurate
        if len(self.settings.coinconf.types) == 0:
            self.clear_specific_items(RemoveCoin)

    # ==== helpers ====
    def clear_specific_items(self, *args):
        for x in self.children.copy():
            if isinstance(x, args):
                self.remove_item(x)

    # ==== content ====
    def _refresh_cointype_select(self):
        """Update the options in the CoinType select to reflect the currently selected values."""
        self.select_cointype.options.clear()

        selected = self.selected == self.settings.coinconf.base.label

        self.select_cointype.add_option(
            label=self.settings.coinconf.base.label,
            emoji=self.settings.coinconf.base.emoji,
            default=selected,
        )

        for coin in self.settings.coinconf.types:  # display highest-first
            selected = self.selected == coin.label
            self.select_cointype.add_option(
                label=coin.label, emoji=coin.emoji, default=selected
            )

    async def _before_send(self):
        self.add_item(AddCoin(self.bot))
        self._refresh_cointype_select()

    async def get_content(self):
        inputdict = deepcopy(inputtemplate)

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


class AddCoin(disnake.ui.Button[CoinPurseSettingsView]):
    def __init__(self, bot: "Labyrinthian"):
        self.bot = bot
        super().__init__(style=disnake.ButtonStyle.green, label="Add Currency", row=3)

    async def callback(self, inter: disnake.MessageInteraction):
        if len(self.view.settings.coinconf.types) >= 24:
            return
        await inter.response.send_modal(
            title="Add Currency",
            custom_id=f"{inter.id}add_currency_modal",
            components=setup_coin_modal_components(),
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
        for x in self.view.settings.coinconf:
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
        self.view.settings.coinconf.types.append(CoinType.from_dict(data))
        await self.view.commit_settings()
        self.view._refresh_cointype_select()
        await self.view.refresh_content(modalinter)


class EditCoin(disnake.ui.Button[CoinPurseSettingsView]):
    def __init__(
        self, bot: "Labyrinthian", match: Union[BaseCoin, CoinType], emoji: str = None
    ):
        self.bot = bot
        self.matched = match
        emoji = None if emoji is None else disnake.PartialEmoji.from_str(emoji)
        super().__init__(
            style=disnake.ButtonStyle.grey, label="Edit Currency", emoji=emoji, row=3
        )

    async def callback(self, inter: disnake.MessageInteraction):
        components = setup_coin_modal_components(
            self.matched.to_dict(), isinstance(self.matched, BaseCoin)
        )
        await inter.response.send_modal(
            title="Edit Currency",
            custom_id=f"{inter.id}edit_currency_modal",
            components=components,
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
        is_base = isinstance(self.matched, BaseCoin)
        data = {
            "name": modalinter.text_values["modal_currency_name"],
            "prefix": modalinter.text_values["modal_currency_prefix"],
            "emoji": modalinter.text_values["modal_currency_emoji"],
        }
        for x in self.view.settings.coinconf:
            if data["name"] == x.name:
                raise FormInvalidInputError(
                    f"Multiple currencies cannot share the same name, please provide a unique name"
                )
            if data["prefix"] == x.prefix:
                raise FormInvalidInputError(
                    f"Multiple currencies cannot share the same prefix, please provide a unique prefix"
                )
        if is_base:
            data["rate"] = (modalinter.text_values["modal_currency_rate"],)
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
        self.view.settings.coinconf.types.append(CoinType.from_dict(data))
        await self.view.commit_settings()
        await self.view.refresh_content(modalinter)


class RemoveCoin(disnake.ui.Button[CoinPurseSettingsView]):
    def __init__(
        self, bot: "Labyrinthian", match: Union[BaseCoin, CoinType], emoji: str = None
    ):
        self.bot = bot
        self.matched = match
        emoji = None if emoji is None else disnake.PartialEmoji.from_str(emoji)
        super().__init__(
            style=disnake.ButtonStyle.red, label="Remove Currency", emoji=emoji, row=3
        )

    async def callback(self, inter: disnake.MessageInteraction):
        if not isinstance(self.matched, CoinType):
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
            self.view.settings.coinconf.types.remove(self.matched)
            await inter.send("Removal confirmed", ephemeral=True)
        else:
            await inter.send("Removal canceled", ephemeral=True)
        await self.view.commit_settings()
        self.view._refresh_cointype_select()
        await self.view.refresh_content(modalinter)


def setup_coin_modal_components(
    values: Optional[Dict[str, str]] = {
        "name": "",
        "prefix": "",
        "rate": "",
        "emoji": "",
    },
    is_base: bool = False,
) -> List[disnake.ui.WrappedComponent]:
    print(values)
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

    @disnake.ui.button(label="Auction Setup Channel", style=disnake.ButtonStyle.green)
    async def auction_setup_chan(
        self, _: disnake.ui.Button, inter: disnake.MessageInteraction
    ):
        pass

    @disnake.ui.button(label="Auction Logging Channel", style=disnake.ButtonStyle.green)
    async def auction_logging_chan(
        self, _: disnake.ui.Button, inter: disnake.MessageInteraction
    ):
        pass

    @disnake.ui.button(label="Auction Listing Channel", style=disnake.ButtonStyle.green)
    async def auction_listing_chan(
        self, _: disnake.ui.Button, inter: disnake.MessageInteraction
    ):
        pass

    @disnake.ui.button(label="Back", style=disnake.ButtonStyle.grey, row=4)
    async def back(self, _: disnake.ui.Button, inter: disnake.MessageInteraction):
        await self.defer_to(SettingsNav, inter)

    # ==== content ====
    async def get_content(self):
        return await super().get_content()


class AuctionDurationsView(SettingsMenuBase):

    # ==== ui ====

    @disnake.ui.button(label="Back", style=disnake.ButtonStyle.grey, row=4)
    async def back(self, _: disnake.ui.Button, inter: disnake.MessageInteraction):
        await self.defer_to(AuctionSettingsView, inter)

    # ==== content ====
    async def get_content(self):
        return await super().get_content()


class AuctionRaritiesView(SettingsMenuBase):

    # ==== ui ====

    @disnake.ui.button(label="Back", style=disnake.ButtonStyle.grey, row=4)
    async def back(self, _: disnake.ui.Button, inter: disnake.MessageInteraction):
        await self.defer_to(AuctionSettingsView, inter)

    # ==== content ====
    async def get_content(self):
        return await super().get_content()


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
        inputdict = deepcopy(inputtemplate)
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

    # ==== ui ====
    @disnake.ui.select(placeholder="Select DM Roles", min_values=0)
    async def select_dm_roles(
        self, select: disnake.ui.Select, inter: disnake.MessageInteraction
    ):
        if len(select.values) == 1 and select.values[0] == TOO_MANY_ROLES_SENTINEL:
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
