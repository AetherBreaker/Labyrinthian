import traceback
from typing import TYPE_CHECKING, TypeVar

import disnake
from cogs.characterlog.browser import create_CharSelect
from disnake.ext import commands
from utils import checks
from utils.models.errors import FormTimeoutError
from utils.ui.settingsui import SettingsNav


if TYPE_CHECKING:
    from bot import Labyrinthian


class Configs(commands.Cog):
    def __init__(self, bot: "Labyrinthian") -> None:
        self.bot = bot

    @commands.slash_command()
    async def staff(self, inter: disnake.ApplicationCommandInteraction):
        pass

    @commands.slash_command()
    async def admin(self, inter: disnake.ApplicationCommandInteraction):
        pass

    @staff.sub_command()
    @commands.cooldown(3, 30.0, type=commands.BucketType.user)
    async def browser(
        self, inter: disnake.ApplicationCommandInteraction, user: disnake.Member
    ):
        """Display the badge log data of a user's characters.
        Parameters
        ----------
        charname: The name of your character."""
        datachk = await self.bot.dbcache.find_one(
            f"BLCharList_{inter.guild.id}", {"user": str(user.id)}
        )
        if datachk is None:
            inter.response.send_message(
                f"{user.name} has no existing character data.", ephemeral=True
            )
        else:
            await create_CharSelect(
                inter, self.bot, inter.author, inter.guild, user, True
            )

    @staff.sub_command()
    @commands.cooldown(3, 30.0, type=commands.BucketType.user)
    async def sheet(
        self,
        inter: disnake.ApplicationCommandInteraction,
        user: disnake.Member,
        charname: str,
        sheetlink: str,
    ):
        """Update a users character sheet in their badge log.
        Parameters
        ----------
        user: The player of the character to be updated.
        charname: The name of the character to update.
        sheetlink: The new character sheet link."""
        userchk = await self.bot.dbcache.find_one(
            f"BLCharList_{inter.guild.id}", {"user": str(user.id)}
        )
        if userchk is None:
            await inter.response.send_message(
                f"{user.name} has no existing character data.", ephemeral=True
            )
        else:
            charchk = await self.bot.dbcache.find_one(
                f"BLCharList_{inter.guild.id}",
                {"user": str(user.id), "character": charname},
            )
            if charchk is None:
                await inter.response.send_message(
                    f'{user.name} has no character named "{charname}".\nPlease double check the characters name using the admin log browser.\nThis field is case and punctuation sensitive.',
                    ephemeral=True,
                )
            else:
                if checks.urlCheck(sheetlink):
                    charchk["sheet"] = sheetlink
                    await self.bot.sdb[f"BLCharList_{inter.guild.id}"].replace_one(
                        {"user": str(user.id), "character": charname}, charchk
                    )
                    await inter.response.send_message(
                        f"{user.name}'s character sheet URL has been updated."
                    )
                else:
                    await inter.response.send_message(
                        "This URL is not an accepted character sheet type.\nPlease ensure that the link is from DnDBeyond, Dicecloud, or a valid GSheets character sheet.",
                        ephemeral=True,
                    )

    @staff.sub_command()
    async def removelisting(
        self, inter: disnake.ApplicationCommandInteraction, listing: str
    ):
        pass

    @admin.sub_command()
    async def serversettings(self, inter: disnake.ApplicationCommandInteraction):
        settings = await self.bot.get_server_settings(str(inter.guild.id))
        settings_ui = SettingsNav.new(self.bot, inter.author, settings, inter.guild)
        await settings_ui.send_to(inter, ephemeral=True)


def setup(bot):
    bot.add_cog(Configs(bot))
