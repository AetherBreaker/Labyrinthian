import asyncio
from contextlib import suppress
from typing import List, Mapping, Optional

import disnake
from disnake.ext import commands

TOO_MANY_CHARACTERS_SENTINEL = "__special:too_many_characters"

# Defines a simple paginator of buttons for the embed.
class LogBrowser(disnake.ui.View):
    def __init__(self, bot: commands.Bot, owner: disnake.User, guild: disnake.Guild, charname: str, charlist: List, embeds: List[disnake.Embed]):
        super().__init__(timeout=None)
        self.embeds = embeds
        self.embed_count = 0
        self.owner = owner
        self.guild = guild
        self.bot = bot
        self.firstchar = charname
        self.charlist = charlist

        self.first_page.disabled = True
        self.prev_page.disabled = True

        # Sets the footer of the embeds with their respective page numbers.
        for i, embed in enumerate(self.embeds):
            embed.set_footer(text=f"Page {i + 1} of {len(self.embeds)}")

        self.selectOp = [disnake.SelectOption() for x in self.charlist]

    def _refresh_character_select(self):
        """Update the options in the DM Role select to reflect the currently selected values."""
        self.select_character.options.clear()
        if len(self.charlist) > 25:
            self.select_character.add_option(
                label="Whoa, you have a lot of characters! Click here to select one.", value=TOO_MANY_CHARACTERS_SENTINEL
            )
            return

        for char in self.charlist:  # display highest-first
            selected = self.firstchar
            self.select_character.add_option(label=char['character'], value=char, default=selected)
        self.select_character.max_values = len(self.select_character.options)

    async def interaction_check(self, interaction: disnake.Interaction) -> bool:
        if interaction.user.id == self.owner.id:
            return True
        await interaction.response.send_message("You are not the owner of this menu.", ephemeral=True)
        return False

    @disnake.ui.select(placeholder="Character", row=4, min_values=0, options=selectOp)
    async def select_character(self, select: disnake.ui.Select, interaction: disnake.Interaction):
        if len(select.values) == 1 and select.values[0] == TOO_MANY_CHARACTERS_SENTINEL:
            charname = await self._text_select_character(interaction)
        else:
            charname = select.values
        self._refresh_character_select()
        # await self.refresh_content(interaction)

    async def _text_select_character(self, interaction: disnake.Interaction) -> Optional[str]:
        self.select_character.disabled = True
        # await self.refresh_content(interaction)
        await interaction.send(
            "Choose the DM roles by sending a message to this channel. You can mention the roles, or use a "
            "comma-separated list of role names or IDs. Type `reset` to reset the role list to the default.",
            ephemeral=True,
        )

        try:
            input_msg: disnake.Message = await self.bot.wait_for(
                "message",
                timeout=60,
                check=lambda msg: msg.author == interaction.author and msg.channel.id == interaction.channel_id,
            )
            with suppress(disnake.HTTPException):
                await input_msg.delete()

            for x in self.charlist:
                if input_msg.casefold() == x['character'].casefold():
                    charname = x

            if charname:
                await interaction.send("Character selected.", ephemeral=True)
                return charname
            await interaction.send("No valid character found. Use the select menu to try again.", ephemeral=True)
            return 
        except asyncio.TimeoutError:
            await interaction.send("No valid character found. Use the select menu to try again.", ephemeral=True)
            return
        finally:
            self.select_character.disabled = False



    # async def refresh_content(self, interaction: disnake.Interaction, **kwargs):
    #     """Refresh the interaction's message with the current state of the menu."""
    #     content_kwargs = await self.get_content()
    #     if interaction.response.is_done():
    #         # using interaction feels cleaner, but we could probably do self.message.edit too
    #         await interaction.edit_original_message(view=self, **content_kwargs, **kwargs)
    #     else:
    #         await interaction.response.edit_message(view=self, **content_kwargs, **kwargs)

    @disnake.ui.button(emoji="⏪", style=disnake.ButtonStyle.blurple)
    async def first_page(self, button: disnake.ui.Button, interaction: disnake.MessageInteraction):
        self.embed_count = 0
        embed = self.embeds[self.embed_count]
        embed.set_footer(text=f"Page 1 of {len(self.embeds)}")

        self.first_page.disabled = True
        self.prev_page.disabled = True
        self.next_page.disabled = False
        self.last_page.disabled = False
        await interaction.response.edit_message(embed=embed, view=self)

    @disnake.ui.button(emoji="◀", style=disnake.ButtonStyle.secondary)
    async def prev_page(self, button: disnake.ui.Button, interaction: disnake.MessageInteraction):
        self.embed_count -= 1
        embed = self.embeds[self.embed_count]

        self.next_page.disabled = False
        self.last_page.disabled = False
        if self.embed_count == 0:
            self.first_page.disabled = True
            self.prev_page.disabled = True
        await interaction.response.edit_message(embed=embed, view=self)

    @disnake.ui.button(emoji="✖️", style=disnake.ButtonStyle.red)
    async def remove(self, button: disnake.ui.Button, interaction: disnake.MessageInteraction):
        await interaction.response.edit_message(view=None)

    @disnake.ui.button(emoji="▶", style=disnake.ButtonStyle.secondary)
    async def next_page(self, button: disnake.ui.Button, interaction: disnake.MessageInteraction):
        self.embed_count += 1
        embed = self.embeds[self.embed_count]

        self.first_page.disabled = False
        self.prev_page.disabled = False
        if self.embed_count == len(self.embeds) - 1:
            self.next_page.disabled = True
            self.last_page.disabled = True
        await interaction.response.edit_message(embed=embed, view=self)

    @disnake.ui.button(emoji="⏩", style=disnake.ButtonStyle.blurple)
    async def last_page(self, button: disnake.ui.Button, interaction: disnake.MessageInteraction):
        self.embed_count = len(self.embeds) - 1
        embed = self.embeds[self.embed_count]

        self.first_page.disabled = False
        self.prev_page.disabled = False
        self.next_page.disabled = True
        self.last_page.disabled = True
        await interaction.response.edit_message(embed=embed, view=self)




