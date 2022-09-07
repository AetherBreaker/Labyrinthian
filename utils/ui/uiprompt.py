import asyncio
from typing import (
    TYPE_CHECKING,
    Any,
    Coroutine,
    Dict,
    List,
    Mapping,
    NewType,
    Optional,
    Union,
)
import disnake
from disnake.ext import commands


if TYPE_CHECKING:
    from bot import Labyrinthian


ComponentID = NewType("ComponentID", str)


class UIPrompt:
    def __init__(
        self,
        bot: "Labyrinthian",
        owner: disnake.User,
        custom_ids: List[ComponentID],
        components: List[disnake.ui.Item],
        input_required: bool = True,
    ):
        self.bot = bot
        self.owner = owner
        self.ids = custom_ids
        self.message = None
        self.rows: List[disnake.ui.ActionRow] = []
        templist = []
        submit_button = disnake.ui.Button(
            style=disnake.ButtonStyle.green,
            label="Submit",
            disabled=input_required,
            custom_id="prompt_submit",
            emoji="✅",
        )
        for component in components:
            if isinstance(component, disnake.ui.Select):
                self.rows.append(disnake.ui.ActionRow(component))
                continue
            if len(templist) < 5:
                templist.append(component)
            else:
                self.rows.append(disnake.ui.ActionRow(*templist))
                templist = []
        try:
            self.rows[-1].append_item(submit_button)
        except ValueError:
            self.rows.append(disnake.ui.ActionRow(submit_button))

    async def on_timeout(self):
        await self.message.channel.send(
            "Information prompt timed out, please try again", ephemeral=True
        )

    async def interaction_check(self, interaction: disnake.Interaction) -> bool:
        if interaction.user.id == self.owner.id:
            return False
        await interaction.response.send_message(
            "You are not the owner of this menu.", ephemeral=True
        )
        return True

    async def listen(
        self, timeout: int = 300
    ) -> Dict[ComponentID, Union[List[str], bool]]:
        output = {}
        try:
            while True:
                inter: disnake.MessageInteraction = await self.bot.wait_for(
                    "message_interaction",
                    check=lambda inter: inter.component.custom_id in self.ids,
                    timeout=timeout,
                )
                if inter.component.custom_id not in self.ids:
                    continue
                if await self.interaction_check(inter):
                    continue
                if inter.component.custom_id == "prompt_submit":
                    break
                if isinstance(inter.component, disnake.SelectMenu):
                    output[inter.component.custom_id] = inter.values
                    await self.refresh_content(inter)
                if sorted(list(output)) == sorted(self.ids):
                    break
        except asyncio.TimeoutError:
            await self.on_timeout()
        await self.message.delete()
        return output or None

    # ==== content ====
    async def get_content(self) -> Mapping:
        """Return a mapping of kwargs to send when sending the view."""
        return {"content": "test"}

    async def _before_send(self):
        """
        Called exactly once, immediately before a menu is sent or deferred to for the first time.
        Use this method to remove any Items that should not be sent or make any attribute adjustments.
        Note that disnake.ui.view#L170 sets each callback's name to its respective Item instance, which will have been
        resolved by the time this method is reached. You may have to let the type checker know about this.
        """
        pass

    # ==== helpers ====
    async def send_prompt(
        self,
        destination: Union[disnake.abc.Messageable, disnake.Interaction],
        *args,
        **kwargs
    ) -> Optional[disnake.Message]:
        """Sends this ActionRow to a given destination."""
        await self._before_send()
        if isinstance(destination, disnake.abc.Messageable):
            self.message = await destination.send(*args, components=self.rows, **kwargs)
        else:
            await destination.send(*args, components=self.rows, **kwargs)
            self.message = await destination.original_message()
        return self.message

    async def refresh_content(
        self, interaction: disnake.Interaction, forceedit: bool = False, **kwargs
    ):
        """Refresh the interaction's message with the current state of the menu."""
        content_kwargs = await self.get_content()
        if interaction.response.is_done():
            await interaction.edit_original_message(
                view=self, **content_kwargs, **kwargs
            )
        else:
            await interaction.response.edit_message(
                view=self, **content_kwargs, **kwargs
            )

    # ==== construction ====
    @classmethod
    def from_dict(
        cls,
        bot: "Labyrinthian",
        interaction: disnake.ApplicationCommandInteraction,
        components: List[Dict[str, Any]],
        input_required: bool = True,
    ):
        complist = [
            data
            if isinstance(data, (disnake.ui.Select, disnake.ui.Button))
            else (
                disnake.ui.Select(**data)
                if "options" in data
                else disnake.ui.Button(**data)
            )
            for data in components
        ]
        idlist: List[ComponentID] = [
            data.custom_id
            if isinstance(data, (disnake.ui.Select, disnake.ui.Button))
            else data["custom_id"]
            for data in components
        ]
        return cls(bot, interaction.author, idlist, complist, input_required)