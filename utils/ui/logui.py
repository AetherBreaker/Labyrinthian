import abc
import asyncio
from typing import TYPE_CHECKING

import disnake
import inflect

from utils.models.errors import FormTimeoutError
from utils.ui.menu import MenuBase

if TYPE_CHECKING:
    from bot import Labyrinthian
    from utils.models.character import Character
    from utils.models.settings.guild import ServerSettings
    from utils.models.settings.user import UserPreferences
    from utils.models.xplog import XPLogBook


class LogMenuBase(MenuBase, abc.ABC):
    __menu_copy_attrs__ = ("bot", "guild", "settings", "uprefs")
    bot: "Labyrinthian"
    guild: disnake.Guild
    settings: "ServerSettings"
    uprefs: "UserPreferences"


class LogMenu(LogMenuBase):
    def __init__(self, privileged: bool, *args, **kwargs):
        self.priv = privileged
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
        privileged: bool = False,
    ):
        inst = cls(privileged=privileged, owner=owner, timeout=180)
        inst.bot = bot
        inst.guild = guild
        inst.settings = settings
        inst.uprefs = uprefs
        return inst

    # ==== ui ====
    @disnake.ui.button(emoji="⏪", style=disnake.ButtonStyle.blurple, disabled=True)
    async def first_page(self, _: disnake.ui.Button, inter: disnake.MessageInteraction):
        self.page = 0
        _.disabled = True
        self.previous_page.disabled = True
        self.next_page.disabled = False
        self.last_page.disabled = False
        await self.refresh_content(inter)

    @disnake.ui.button(emoji="◀", style=disnake.ButtonStyle.secondary, disabled=True)
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

    @disnake.ui.button(emoji="▶", style=disnake.ButtonStyle.secondary, disabled=True)
    async def next_page(self, _: disnake.ui.Button, inter: disnake.MessageInteraction):
        self.page += 1
        if self.page >= (len(self.pagelist) - 1):
            _.disabled = True
            self.last_page.disabled = True
        self.first_page.disabled = False
        self.previous_page.disabled = False
        await self.refresh_content(inter)

    @disnake.ui.button(emoji="⏩", style=disnake.ButtonStyle.blurple, disabled=True)
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
        await self.refresh_chardat(select.values[0])
        if not self.char:
            return
        if self.priv:
            for x in self.children:
                if isinstance(x, StaffArchiveCharButton):
                    x.disabled = False
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
                notneg = False if y.xpadded < 0 else True
                toybox.append(
                    f"{('<@'+y.user+'> at')*(self.char.user != y.user)} <t:{y.timestamp}:f>\n"
                    f"`{y.name} {'gained' if notneg else 'lost'} "
                    f"{y.prevxp}({'+'*notneg}{y.xpadded}) {p.plural(self.settings.xplabel)}` "
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

    async def refresh_chardat(self, name):
        self.selval = name
        self.char = await self.bot.get_character(
            str(self.guild.id), self.uprefs.user, self.selval, validate=False
        )
        if self.char:
            self.log = await self.bot.get_character_xplog(self.char.id)

    async def _before_send(self):
        disabled = True
        if str(self.guild.id) in self.uprefs.activechar:
            await self.refresh_chardat(self.uprefs.activechar[str(self.guild.id)].name)
            self.struct_log_embs()
            if len(self.pagelist) in (1, 0):
                self.first_page.disabled = True
                self.previous_page.disabled = True
                self.next_page.disabled = True
                self.last_page.disabled = True
            else:
                self.next_page.disabled = False
                self.last_page.disabled = False
            disabled = False
        if self.priv:
            self.add_item(StaffArchiveCharButton(disabled))
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


class StaffArchiveCharButton(disnake.ui.Button[LogMenu]):
    def __init__(self, disabled: bool):
        super().__init__(
            style=disnake.ButtonStyle.red,
            label="Archive Character",
            disabled=disabled,
            emoji="✖️",
            row=4,
        )

    async def callback(self, inter: disnake.MessageInteraction):
        await inter.response.send_modal(
            title="Confirmation",
            custom_id=f"{inter.id}character_archival_confirm",
            components=disnake.ui.TextInput(
                label="Confirm Character Archival",
                custom_id="confirm_archive",
                style=disnake.TextInputStyle.single_line,
                placeholder="Confirm",
                required=True,
                min_length=7,
                max_length=7,
            ),
        )
        try:
            modalinter: disnake.ModalInteraction = await self.view.bot.wait_for(
                "modal_submit",
                check=lambda i: i.custom_id == f"{inter.id}character_archival_confirm"
                and i.author.id == inter.author.id,
                timeout=180,
            )
        except asyncio.TimeoutError:
            raise FormTimeoutError
        if modalinter.text_values["confirm_archive"] == "Confirm":
            await self.view.char.archive(self.view.bot, self.view.uprefs)
            self.view.selval = None
            self.view.char = None
            self.view.log = None
            self.view.pagelist = []
            self.view.page = 0
            self.disabled = True
        else:
            await inter.send("Removal canceled", ephemeral=True)
        self.view._refresh_char_select()
        await self.view.refresh_content(modalinter)
