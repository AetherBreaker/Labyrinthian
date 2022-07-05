import abc
from dis import dis
from typing import TYPE_CHECKING

import disnake
import inflect

from utils.ui.menu import MenuBase


if TYPE_CHECKING:
    from bot import Labyrinthian
    from utils.models.settings.user import UserPreferences
    from utils.models.xplog import XPLogBook
    from utils.models.character import Character
    from utils.models.settings.guild import ServerSettings


class LogMenuBase(MenuBase, abc.ABC):
    __menu_copy_attrs__ = ("bot", "guild", "settings", "uprefs")
    bot: "Labyrinthian"
    guild: disnake.Guild
    settings: "ServerSettings"
    uprefs: "UserPreferences"


class LogMenu(LogMenuBase):
    def __init__(self, *args, **kwargs):
        self.selval = None
        self.char: "Character" = None
        self.log: "XPLogBook" = None
        self.pagelist = []
        self.page = 0
        super().__init__(*args, **kwargs)

    @classmethod
    def new(
        cls,
        bot: "Labyrinthian",
        settings: "ServerSettings",
        uprefs: "UserPreferences",
        owner: disnake.User,
        guild: disnake.Guild,
    ):
        inst = cls(owner=owner, timeout=180)
        inst.bot = bot
        inst.guild = guild
        inst.settings = settings
        inst.uprefs = uprefs
        return inst

    # ==== ui ====
    @disnake.ui.button(emoji="⏪", style=disnake.ButtonStyle.blurple)
    async def first_page(self, _: disnake.ui.Button, inter: disnake.MessageInteraction):
        self.page = 0
        _.disabled = True
        self.previous_page.disabled = True
        self.next_page.disabled = False
        self.last_page.disabled = False
        await self.refresh_content(inter)

    @disnake.ui.button(emoji="◀", style=disnake.ButtonStyle.secondary)
    async def previous_page(
        self, _: disnake.ui.Button, inter: disnake.MessageInteraction
    ):
        self.page -= 1
        if self.page <= 0:
            _.disabled = True
            self.first_page.disabled = True
        self.next_page.disabled = False
        self.last_page.disabled = False
        await self.refresh_content(inter)

    @disnake.ui.button(emoji="✖️", style=disnake.ButtonStyle.red)
    async def close_view(self, _: disnake.ui.Button, inter: disnake.MessageInteraction):
        await self.on_timeout()

    @disnake.ui.button(emoji="▶", style=disnake.ButtonStyle.secondary)
    async def next_page(self, _: disnake.ui.Button, inter: disnake.MessageInteraction):
        self.page += 1
        if self.page >= (len(self.pagelist) - 1):
            _.disabled = True
            self.last_page.disabled = True
        self.first_page.disabled = False
        self.previous_page.disabled = False
        await self.refresh_content(inter)

    @disnake.ui.button(emoji="⏩", style=disnake.ButtonStyle.blurple)
    async def last_page(self, _: disnake.ui.Button, inter: disnake.MessageInteraction):
        self.page = len(self.pagelist) - 1
        self.first_page.disabled = False
        self.previous_page.disabled = False
        self.next_page.disabled = True
        _.disabled = True
        await self.refresh_content(inter)

    @disnake.ui.select(
        placeholder="Select Character", row=3, min_values=1, max_values=1
    )
    async def select_char(
        self, select: disnake.ui.Select, inter: disnake.MessageInteraction
    ):
        if select.values[0] is None:
            self.page = 0
            self.pagelist = None
            await self.refresh_content(inter)
            return
        self.selval = select.values[0]
        self.char = await self.bot.get_character(
            str(self.guild.id), str(self.owner.id), self.selval
        )
        self.log = await self.bot.get_character_xplog(self.char.id)
        self.struct_log_embs()
        if len(self.pagelist) in (1, 0):
            self.first_page.disabled = True
            self.previous_page.disabled = True
            self.next_page.disabled = True
            self.last_page.disabled = True
        else:
            self.next_page.disabled = False
            self.last_page.disabled = False
        self._refresh_char_select()
        await self.refresh_content(inter)

    # ==== helpers ====
    def struct_log_embs(self):
        if not self.log:
            self.pagelist = []
            self.page = 0
            return
        p = inflect.engine()
        pagelist = []
        for x in self.log.paginate(4):
            toybox = []
            for y in x:
                isneg = True if y.xpadded < 0 else False
                toybox.append(
                    f"{('<@'+y.user+'> at')*(self.char.user != y.user)} <t:{y.timestamp}:f>\n"
                    f"`{y.name} {'lost' if isneg else 'gained'} "
                    f"{y.prevxp}({'+'*isneg}{y.xpadded}) {p.plural(self.settings.xplabel)}` "
                    f"Approved by: <@{y.dm}>"
                )
            pagelist.append("\n\n".join(toybox))
        self.pagelist = pagelist
        self.page = 0

    # ==== content ====
    def _refresh_char_select(self):
        self.select_char.options.clear()
        for char in reversed(
            self.uprefs.characters[str(self.guild.id)]
        ):  # display highest-first
            selected = self.selval is not None and self.selval == char
            self.select_char.add_option(label=char, default=selected)

    async def _before_send(self):
        disabled = False
        if str(self.guild.id) in self.uprefs.activechar:
            self.log = await self.bot.get_character_xplog(
                self.uprefs.activechar[str(self.guild.id)].id
            )
            self.selval = self.uprefs.activechar[str(self.guild.id)].name
            self.char = await self.bot.get_character(
                str(self.guild.id), str(self.owner.id), self.selval
            )
            self.struct_log_embs()
            disabled = True
        if str(self.owner.id) != self.uprefs.user:
            self.add_item(StaffDeleteCharButton(disabled))
        self._refresh_char_select()

    async def get_content(self):
        p = inflect.engine()
        embeds = []
        if not self.char:
            embeds.append(
                disnake.Embed(
                    title=(
                        "Character Log Menu"
                        if str(self.owner.id) == self.uprefs.user
                        else "Staff Log Menu"
                    ),
                    description=(
                        "Select a character."
                        if str(self.owner.id) == self.uprefs.user
                        else f"Select one of <@{self.uprefs.user}>'s characters below."
                    ),
                    color=disnake.Color.random().value,
                )
                .add_field(
                    name=f"{self.settings.xplabel} Information:",
                    value=f"Current {p.plural(self.settings.xplabel)}: \nExpected Level: ",
                    inline=True,
                )
                .add_field(name="Class Levels:", value="\u200B", inline=True)
                .add_field(name="Total Levels:", value="\u200B", inline=True)
            )
        else:
            embeds.append(
                disnake.Embed(
                    title=f"{self.char.name}'s Info'",
                    description=(
                        "Click the embed title for the sheet link.\n"
                        f"Played by: <@{self.char.user}>."
                    ),
                    color=disnake.Color.random().value,
                    url=f"{self.char.sheet}",
                )
                .add_field(
                    name=f"{self.settings.xplabel} Information:",
                    value=(
                        f"Current {p.plural(self.settings.xplabel)}: {self.char.xp}\n"
                        f"Expected Level: {self.char.expected_level}"
                    ),
                    inline=True,
                )
                .add_field(
                    name="Class Levels:",
                    value="\n".join(
                        [f"{x}: {y}" for x, y in self.char.multiclasses.items()]
                    ),
                    inline=True,
                )
                .add_field(
                    name=f"Total Levels: {self.char.level}", value="\u200B", inline=True
                )
                .add_field(
                    name=f"{self.settings.xplabel} log",
                    value=(
                        self.pagelist[self.page]
                        if self.pagelist
                        else "This character doesn't have any entries yet..."
                    ),
                )
            )
            if self.pagelist:
                embeds[0].set_footer(
                    text=f"Page {self.page + 1} of {len(self.pagelist)}"
                )
        return {"embeds": embeds}


class StaffDeleteCharButton(disnake.ui.Button[LogMenu]):
    def __init__(self, disabled: bool):
        super().__init__(
            style=disnake.ButtonStyle.red,
            label="Delete Character",
            disabled=disabled,
            emoji="✖️",
            row=4,
        )

    async def callback(self, _: disnake.ui.Button, inter: disnake.MessageInteraction):
        pass
