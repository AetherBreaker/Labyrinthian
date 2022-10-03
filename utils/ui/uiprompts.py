import asyncio
from typing import TYPE_CHECKING, Any, Dict, List, Mapping, NewType, Optional, Union

import disnake
from utils.ui.menu import MenuBase

if TYPE_CHECKING:
    from bot import Labyrinthian
    from utils.models.coinpurse import CoinPurse
    from utils.models.settings.user import UserPreferences


class CharacterSelectPrompt(MenuBase):
    def __init__(
        self,
        owner: disnake.User,
        guild: disnake.Guild,
        author_prefs: "UserPreferences",
        target_prefs: "UserPreferences",
        amount: "CoinPurse",
    ):
        self.owner = owner
        self.guild = guild
        self.authprefs = author_prefs
        self.targprefs = target_prefs
        self.amount = amount
        super().__init__(timeout=180)

    # ==== components ====
    @disnake.ui.select()
    async def character_select(
        self, select: disnake.ui.Select, inter: disnake.MessageCommandInteraction
    ) -> None:
        pass

    # ==== helpers ====
    def _refresh_char_select(self) -> None:
        self.character_select.options.clear()
        for char in reversed(
            self.targprefs.characters[str(self.guild.id)]
        ):  # display highest-first
            selected = self.selval is not None and self.selval == char
            self.select_char.add_option(label=char, default=selected)

    async def _before_send(self) -> None:
        self._refresh_char_select()

    # ==== content ====
    def get_content(self) -> dict:
        return {}
