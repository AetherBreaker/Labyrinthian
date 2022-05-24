from typing import List

import disnake
from disnake.ext import commands

# Defines a simple paginator of buttons for the embed.
class LogBrowser(disnake.ui.View):
    def __init__(self, owner: disnake.User, guild: disnake.Guild, embeds: List[disnake.Embed]):
        super().__init__(timeout=None)
        self.embeds = embeds
        self.embed_count = 0
        self.owner = owner
        self.guild = guild

        self.first_page.disabled = True
        self.prev_page.disabled = True

        # Sets the footer of the embeds with their respective page numbers.
        for i, embed in enumerate(self.embeds):
            embed.set_footer(text=f"Page {i + 1} of {len(self.embeds)}")

    async def interaction_check(self, interaction: disnake.Interaction) -> bool:
        if interaction.user.id == self.owner.id:
            return True
        await interaction.response.send_message("You are not the owner of this menu.", ephemeral=True)
        return False

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

    @disnake.ui.button(emoji="❌", style=disnake.ButtonStyle.red)
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




            #@disnake.ui.select(placeholder="Character", row=4, min_values=0)
    #async def char_select(self, select: disnake.ui.Select, interation: disnake.Interaction):
    #    pass



    #@disnake.ui.select(placeholder="Select DM Roles", min_values=0)
    #async def select_dm_roles(self, select: disnake.ui.Select, interaction: disnake.Interaction):
    #    if len(select.values) == 1 and select.values[0] == TOO_MANY_CHARACTERS_SENTINEL:
    #        role_ids = await self._text_select_dm_roles(interaction)
    #    else:
    #        role_ids = list(map(int, select.values))
    #    self.settings.dm_roles = role_ids or None
    #    self._refresh_dm_role_select()
    #    await self.refresh_content(interaction)

    #async def _text_select_dm_roles(self, interaction: disnake.Interaction) -> Optional[List[int]]:
    #    self.select_dm_roles.disabled = True
    #    await self.refresh_content(interaction)
    #    await interaction.send(
    #        "Choose the DM roles by sending a message to this channel. You can mention the roles, or use a "
    #        "comma-separated list of role names or IDs. Type `reset` to reset the role list to the default.",
    #        ephemeral=True,
    #    )

    #    try:
    #        input_msg: disnake.Message = await self.bot.wait_for(
    #            "message",
    #            timeout=60,
    #            check=lambda msg: msg.author == interaction.author and msg.channel.id == interaction.channel_id,
    #        )
    #        with suppress(disnake.HTTPException):
    #            await input_msg.delete()

            #role_ids = {r.id for r in input_msg.role_mentions}
            #for stmt in input_msg.content.split(","):
            #    clean_stmt = stmt.strip()
            #    try:  # get role by id
            #        role_id = int(clean_stmt)
            #        maybe_role = self.guild.get_role(role_id)
            #    except ValueError:  # get role by name
            #        maybe_role = next((r for r in self.guild.roles if r.name.lower() == clean_stmt.lower()), None)
            #    if maybe_role is not None:
            #        role_ids.add(maybe_role.id)

    #        if role_ids:
    #            await interaction.send("The DM roles have been updated.", ephemeral=True)
    #            return list(role_ids)
    #        await interaction.send("No valid roles found. Use the select menu to try again.", ephemeral=True)
    #        return self.settings.dm_roles
    #    except asyncio.TimeoutError:
    #        await interaction.send("No valid roles found. Use the select menu to try again.", ephemeral=True)
    #        return self.settings.dm_roles
    #    finally:
    #        self.select_dm_roles.disabled = False

    #def _refresh_dm_role_select(self):
    #    """Update the options in the DM Role select to reflect the currently selected values."""
    #    self.select_dm_roles.options.clear()
    #    if len(self.guild.roles) > 25:
    #        self.select_dm_roles.add_option(
    #            label="Whoa, this server has a lot of roles! Click here to select them.", value=TOO_MANY_CHARACTERS_SENTINEL
    #        )
    #        return

    #    for role in reversed(self.guild.roles):  # display highest-first
    #        selected = self.settings.dm_roles is not None and role.id in self.settings.dm_roles
    #        self.select_dm_roles.add_option(label=role.name, value=str(role.id), emoji=role.emoji, default=selected)
    #    self.select_dm_roles.max_values = len(self.select_dm_roles.options)

    #async def refresh_content(self, interaction: disnake.Interaction, **kwargs):
    #    """Refresh the interaction's message with the current state of the menu."""
    #    content_kwargs = await self.get_content()
    #    if interaction.response.is_done():
    #        # using interaction feels cleaner, but we could probably do self.message.edit too
    #        await interaction.edit_original_message(view=self, **content_kwargs, **kwargs)
    #    else:
    #        await interaction.response.edit_message(view=self, **content_kwargs, **kwargs)