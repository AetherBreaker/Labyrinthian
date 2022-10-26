from typing import TYPE_CHECKING, Any, Callable

import disnake
from bson import ObjectId

from utils.ui.menu import MenuBase

if TYPE_CHECKING:
    from utils.models.settings.user import UserPreferences


class CharacterSelectPrompt(MenuBase):
    def __init__(
        self,
        owner: disnake.User,
        guild: disnake.Guild,
        author_prefs: "UserPreferences",
        target_prefs: "UserPreferences",
        success_func: Callable,
        func_kwargs: dict[str, Any],
    ) -> None:
        self.guild: disnake.Guild = guild
        self.authprefs: "UserPreferences" = author_prefs
        self.targprefs: "UserPreferences" = target_prefs
        self.func = success_func
        self.kwargs: dict[str, Any] = func_kwargs
        super().__init__(timeout=180, owner=owner)

    # ==== components ====
    @disnake.ui.select()
    async def character_select(
        self, select: disnake.ui.Select, inter: disnake.MessageInteraction
    ) -> None:
        self.submit_selection.disabled = False
        self._refresh_char_select()
        await self.refresh_content(inter)

    @disnake.ui.button(label="Submit", disabled=True, style=disnake.ButtonStyle.green)
    async def submit_selection(
        self, _: disnake.ui.Button, inter: disnake.MessageInteraction
    ):
        await inter.message.delete()
        await self.func(
            inter,
            recipient=ObjectId(self.character_select.options[0].value),
            **self.kwargs
        )
        pass

    # ==== helpers ====
    def _refresh_char_select(self) -> None:
        self.character_select.options.clear()
        for char, oid in reversed(
            self.targprefs.characters[str(self.guild.id)].items()
        ):  # display highest-first
            selected: bool = self.selval is not None and self.selval == char
            self.character_select.add_option(
                label=char, value=str(oid), default=selected
            )

    async def _before_send(self) -> None:
        self._refresh_char_select()

    # ==== content ====
    def get_content(self) -> dict:
        return {"content": "Please select a character."}
