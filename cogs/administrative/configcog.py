from typing import TYPE_CHECKING, List

import disnake
from pydantic import ValidationError
import rapidfuzz
from cogs.characterlog.browser import create_CharSelect
from disnake.ext import commands
from utils import checks
from utils.ui.logui import LogMenu

from utils.ui.settingsui import SettingsNav


if TYPE_CHECKING:
    from bot import Labyrinthian
    from utils.models.settings.user import UserPreferences
    from utils.models.character import Character


class Configs(commands.Cog):
    def __init__(self, bot: "Labyrinthian") -> None:
        self.bot = bot

    # ==== top level commands ====
    @commands.slash_command(
        default_member_permissions=disnake.Permissions(permissions=268435456)
    )
    async def staff(self, inter: disnake.ApplicationCommandInteraction):
        pass

    @commands.slash_command(
        default_member_permissions=disnake.Permissions(permissions=8)
    )
    async def admin(self, inter: disnake.ApplicationCommandInteraction):
        pass

    # ==== sub commands ====
    @staff.sub_command()
    @commands.cooldown(3, 30.0, type=commands.BucketType.user)
    async def log_menu(
        self, inter: disnake.ApplicationCommandInteraction, user: disnake.Member
    ):
        """Display the badge log data of a user's characters.
        Can also archive users characters from this menu.
        Parameters
        ----------
        user: The user who's characters you wish to view."""
        charlist = await self.bot.charcache.find_distinct_chardat(
            str(inter.guild.id), str(user.id)
        )
        if not charlist:
            await inter.send(
                f"User {user.name} doesn't have any characters to view!", ephemeral=True
            )
            return
        uprefs = await self.bot.get_user_prefs(str(inter.author.id))
        settings = await self.bot.get_server_settings(str(inter.guild.id))
        ui = LogMenu.new(
            self.bot, settings, uprefs, inter.author, inter.guild, privileged=True
        )
        await ui.send_to(inter, ephemeral=True)

    @staff.sub_command()
    @commands.cooldown(3, 30.0, type=commands.BucketType.user)
    async def sheet(
        self,
        inter: disnake.ApplicationCommandInteraction,
        user: disnake.Member,
        name: str,
        sheetlink: str,
    ):
        """Update a users character sheet in their badge log.
        Parameters
        ----------
        user: The player of the character to be updated.
        name: The name of the character to update.
        sheetlink: The new character sheet link."""
        uprefs: "UserPreferences" = await self.bot.get_user_prefs(str(user.id))
        if not uprefs.characters[str(inter.guild.id)]:
            await inter.send(
                f"{user.name} has no existing character data.", ephemeral=True
            )
            return
        char: "Character" = await self.bot.get_character(
            str(inter.guild.id), str(user.id), name
        )
        if char is None:
            await inter.send(
                f'{user.name} has no character named "{name}".\n'
                f"Please double check the characters name using the admin log browser.\n"
                f"This field is case and punctuation sensitive.",
                ephemeral=True,
            )
            return
        try:
            char.sheet = sheetlink
            await inter.send(f"{user.name}'s character sheet URL has been updated.")
            await char.commit(self.bot.dbcache)
        except ValidationError as e:
            errlist = []
            for x in e.errors():
                errlist.append(f"{x['loc'][0]}:\n\t{x['msg']}")
            toybox = "\n".join(errlist)
            await inter.send(
                "This URL is not an accepted character sheet type.\n"
                "Please ensure that the link is from DnDBeyond, Dicecloud, or a valid GSheets character sheet."
                "Error:\n"
                f"{toybox}",
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

    # ==== autocompleters ====
    @sheet.autocomplete("name")
    async def autocomp_otheruser_names(
        self, inter: disnake.ApplicationCommandInteraction, user_input: str
    ):
        user = inter.filled_options["user"]
        charlist: List[str] = await self.bot.charcache.find_distinct_chardat(
            str(inter.guild.id), str(user.id)
        )
        if charlist:
            return [x[0] for x in rapidfuzz.process.extract(user_input, charlist)]


def setup(bot):
    bot.add_cog(Configs(bot))
