from typing import TYPE_CHECKING, NewType
import disnake
from disnake.ext import commands
import inflect


if TYPE_CHECKING:
    from bot import Labyrinthian
    from utils.models.settings.user import ActiveCharacter
    from utils.models.settings.guild import ServerSettings
    from utils.models.character import Character


UserID = NewType("UserID", str)
GuildID = NewType("GuildID", str)
CharacterName = NewType("CharacterName", str)


class Logging(commands.Cog):
    def __init__(self, bot: "Labyrinthian"):
        self.bot = bot

    @commands.Cog.listener("on_changed_character")
    async def log_charchange(
        self,
        settings: "ServerSettings",
        user: disnake.User,
        newchar: "ActiveCharacter",
        oldchar: "ActiveCharacter",
    ):
        newchar: "Character" = await self.bot.get_char_by_oid(
            newchar.id, validate=False
        )
        oldchar: "Character" = await self.bot.get_char_by_oid(
            oldchar.id, validate=False
        )
        p = inflect.engine()
        embed = (
            disnake.Embed(title=f"{user.name} changed characters")
            .set_author(name=user.name, icon_url=user.display_avatar.url)
            .add_field(
                name="Previous Character:",
                value=f"[**{oldchar.name}**]({oldchar.sheet})",
                inline=True,
            )
            .add_field(
                name="Current Character:",
                value=f"[**{newchar.name}**]({newchar.sheet})",
                inline=True,
            )
            .add_field(name="\u200b", value="\u200b", inline=True)
            .add_field(
                name=f"{settings.xplabel} Information:",
                value=(
                    f"Current {p.plural(settings.xplabel)}: {oldchar.xp}\n"
                    f"Expected Level: {oldchar.expected_level}"
                ),
                inline=True,
            )
            .add_field(
                name=f"{settings.xplabel} Information:",
                value=(
                    f"Current {p.plural(settings.xplabel)}: {newchar.xp}\n"
                    f"Expected Level: {newchar.expected_level}"
                ),
                inline=True,
            )
            .add_field(name="\u200b", value="\u200b", inline=True)
            .add_field(
                name="Class Levels:",
                value="\n".join([f"{x}: {y}" for x, y in oldchar.multiclasses.items()]),
                inline=True,
            )
            .add_field(
                name="Class Levels:",
                value="\n".join([f"{x}: {y}" for x, y in newchar.multiclasses.items()]),
                inline=True,
            )
            .add_field(name="\u200b", value="\u200b", inline=True)
            .add_field(
                name=f"Total Levels: {oldchar.level}", value="\u200B", inline=True
            )
            .add_field(
                name=f"Total Levels: {newchar.level}", value="\u200B", inline=True
            )
            .add_field(name="\u200b", value="\u200b", inline=True)
        )
        destination: disnake.TextChannel = self.bot.get_channel(
            int(settings.loggingchar)
        )
        await destination.send(
            f"<@{user.id}>",
            allowed_mentions=disnake.AllowedMentions.none(),
            embed=embed,
        )

    @commands.Cog.listener("on_something")
    async def log_charcreate(
        self,
    ):
        pass

    @commands.slash_command()
    async def testcmd(self, inter: disnake.ApplicationCommandInteraction):
        """test a command"""
        settings = await self.bot.get_settings_no_valid(str(inter.guild.id))
        destination: disnake.TextChannel = self.bot.get_channel(
            int(settings.loggingchar)
        )
        await destination.send(
            "<@200632489998417929>", allowed_mentions=disnake.AllowedMentions.none()
        )


def setup(bot: "Labyrinthian"):
    bot.add_cog(Logging(bot))
