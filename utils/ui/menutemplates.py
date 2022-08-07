import asyncio

import disnake
from utils.models.errors import FormTimeoutError
from utils.ui.menu import MenuBase


class SelectandModify(MenuBase):
    select_items: disnake.ui.Select

    def __init__(self, *args, **kwargs):
        self.selected: str = None
        super().__init__(*args, **kwargs)

    # ==== ui ====
    @disnake.ui.button(label="Reset Settings", style=disnake.ButtonStyle.red, row=0)
    async def reset_button(
        self, _: disnake.ui.Button, inter: disnake.MessageInteraction
    ):
        await inter.response.send_modal(
            title="Confirm Reset",
            custom_id=f"{inter.id}reset_confirmation_modal",
            components=disnake.ui.TextInput(
                label="Confirmation:",
                custom_id="reset_confirmation_input",
                placeholder="Confirm",
                min_length=7,
                max_length=7,
            ),
        )
        try:
            modalinter: disnake.ModalInteraction = await inter.bot.wait_for(
                "modal_submit",
                check=lambda i: i.custom_id == f"{inter.id}reset_confirmation_modal"
                and i.author.id == inter.author.id,
                timeout=180,
            )
        except asyncio.TimeoutError:
            raise FormTimeoutError
        await self.confirmation_callback(inter, modalinter)

    @disnake.ui.select(placeholder="Select Item", min_values=1, max_values=1, row=2)
    async def select_items(
        self, select: disnake.ui.Select, inter: disnake.MessageInteraction
    ):
        if self.selected != select.values[0]:
            self.selected = select.values[0]
            self.process_selection()
            self.refresh_select()
            await self.refresh_content(inter)

    # ==== magic config methods ====
    async def confirmation_callback(
        self, inter: disnake.MessageInteraction, modalinter: disnake.ModalInteraction
    ):
        """
        This is called to handle the callback for the reset confirmation modal.
        """
        pass

    # ==== handlers ====
    def process_selection(self):
        """
        This is called to process the results of a select interaction.
        selection results can be found in "self.select_items.values"
        self.matched and self.matchindex are defined for optionally holding processing results.

        This also sets up the list operation buttons every time the select is interacted
        or at the end of item removal.

        Each button optionally accepts button configuration inputs like:
        label,
        style,
        row,
        emoji,
        url
        """
        pass

    async def add(self, inter: disnake.MessageInteraction):
        """
        Handles the callback of the Add button.
        """
        pass

    async def edit(self, inter: disnake.MessageInteraction):
        """
        Handles the callback of the Edit button.
        """
        pass

    async def remove(self, inter: disnake.MessageInteraction):
        """
        Handles the callback of the Remove button.
        """
        pass

    # ==== helpers ====
    def _clear_specific_items(self, *args):
        for x in self.children.copy():
            if isinstance(x, args):
                self.remove_item(x)

    # ==== content ====
    def refresh_select(self):
        """Update the options in the select to reflect the currently selected values."""
        pass


class AddButton(disnake.ui.Button[MenuBase]):
    def __init__(
        self,
        style: disnake.ButtonStyle = disnake.ButtonStyle.green,
        label: str = "Add",
        emoji: str = "",
        row: int = 3,
        *args,
        **kwargs,
    ):
        if emoji == "":
            emoji = None
        super().__init__(
            *args, style=style, label=label, emoji=emoji, row=row, **kwargs
        )

    async def callback(self, inter: disnake.MessageInteraction):
        await self.view.add(inter)


class EditButton(disnake.ui.Button[MenuBase]):
    def __init__(
        self,
        style: disnake.ButtonStyle = disnake.ButtonStyle.grey,
        label: str = "Edit",
        emoji: str = "",
        row: int = 3,
        *args,
        **kwargs,
    ):
        if emoji == "":
            emoji = None
        super().__init__(
            *args, style=style, label=label, emoji=emoji, row=row, **kwargs
        )

    async def callback(self, inter: disnake.MessageInteraction):
        await self.view.edit(inter)


class RemoveButton(disnake.ui.Button[MenuBase]):
    def __init__(
        self,
        style: disnake.ButtonStyle = disnake.ButtonStyle.red,
        label: str = "Remove",
        emoji: str = "",
        row: int = 3,
        *args,
        **kwargs,
    ):
        if emoji == "":
            emoji = None
        super().__init__(
            *args, style=style, label=label, emoji=emoji, row=row, **kwargs
        )

    async def callback(self, inter: disnake.MessageInteraction):
        await self.view.remove(inter)
