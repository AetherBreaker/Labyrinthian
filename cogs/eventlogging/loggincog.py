from typing import TYPE_CHECKING, Dict, NewType

import disnake
import inflect
from disnake.ext import commands

if TYPE_CHECKING:
    from bot import Labyrinthian
    from utils.models.character import Character
    from utils.models.settings.guild import ServerSettings
    from utils.models.settings.user import ActiveCharacter


UserID = NewType("UserID", str)
GuildID = NewType("GuildID", str)
CharacterName = NewType("CharacterName", str)


class Logging(commands.Cog):
    def __init__(self, bot: "Labyrinthian"):
        self.bot = bot

    # ==== character cmd logging ====
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

    @commands.Cog.listener("on_character_created")
    async def log_charcreate(
        self, settings: "ServerSettings", user: disnake.User, character: "Character"
    ):
        p = inflect.engine()
        embed = (
            disnake.Embed(title=f"{user.name} created a new character.")
            .set_author(name=user.name, icon_url=user.display_avatar.url)
            .add_field(
                name="New Character:",
                value=f"[**{character.name}**]({character.sheet})",
            )
            .add_field(
                name=f"{settings.xplabel} Information:",
                value=(
                    f"Current {p.plural(settings.xplabel)}: {character.xp}\n"
                    f"Expected Level: {character.expected_level}"
                ),
            )
            .add_field(
                name="Class Levels:",
                value="\n".join(
                    [f"{x}: {y}" for x, y in character.multiclasses.items()]
                ),
            )
            .add_field(name=f"Total Levels: {character.level}", value="\u200B")
        )
        destination: disnake.TextChannel = self.bot.get_channel(
            int(settings.loggingchar)
        )
        await destination.send(
            f"<@{user.id}>",
            allowed_mentions=disnake.AllowedMentions.none(),
            embed=embed,
        )

    @commands.Cog.listener("on_character_renamed")
    async def log_charrename(
        self, settings: "ServerSettings", user: disnake.User, oldname: str, newname: str
    ):
        embed = (
            disnake.Embed(title=f"{user.name} renamed a character")
            .add_field(name="Previous Name:", value=oldname, inline=True)
            .add_field(name="New Name:", value=newname, inline=True)
        )
        destination: disnake.TextChannel = self.bot.get_channel(
            int(settings.loggingchar)
        )
        await destination.send(
            f"<@{user.id}>",
            allowed_mentions=disnake.AllowedMentions.none(),
            embed=embed,
        )

    @commands.Cog.listener("on_xp_changed")
    async def log_xp(
        self,
        settings: "ServerSettings",
        user: disnake.User,
        xpentry: str,
        subtracting: bool,
    ):
        p = inflect.engine()
        embed = disnake.Embed(
            title=f"{user.name} {'removed' if subtracting else 'added'} {p.plural(settings.xplabel)}",
            description=xpentry,
        )
        destination: disnake.TextChannel = self.bot.get_channel(int(settings.loggingxp))
        await destination.send(
            f"<@{user.id}>",
            allowed_mentions=disnake.AllowedMentions.none(),
            embed=embed,
        )

    @commands.Cog.listener("on_class_added")
    async def log_class_add(
        self,
        settings: "ServerSettings",
        user: disnake.User,
        character: "Character",
        oldclasses: Dict[str, int],
        newclass: str,
    ):
        embed = (
            disnake.Embed(
                title=f"{user.name} multiclassed {character.name} into {newclass}"
            )
            .add_field(
                name="Old Classes:",
                value="\n".join([f"{x}: {y}" for x, y in oldclasses.items()]),
                inline=True,
            )
            .add_field(
                name="New Classes:",
                value="\n".join(
                    [f"{x}: {y}" for x, y in character.multiclasses.items()]
                ),
                inline=True,
            )
        )
        destination: disnake.TextChannel = self.bot.get_channel(
            int(settings.loggingchar)
        )
        await destination.send(
            f"<@{user.id}>",
            allowed_mentions=disnake.AllowedMentions.none(),
            embed=embed,
        )

    @commands.Cog.listener("on_class_removed")
    async def log_class_removed(
        self,
        settings: "ServerSettings",
        user: disnake.User,
        character: "Character",
        oldclasses: Dict[str, int],
        classname: str,
    ):
        embed = (
            disnake.Embed(
                title=f"{user.name} removed {classname} from {character.name}"
            )
            .add_field(
                name="Old Classes:",
                value="\n".join([f"{x}: {y}" for x, y in oldclasses.items()]),
                inline=True,
            )
            .add_field(
                name="New Classes:",
                value="\n".join(
                    [f"{x}: {y}" for x, y in character.multiclasses.items()]
                ),
                inline=True,
            )
        )
        destination: disnake.TextChannel = self.bot.get_channel(
            int(settings.loggingchar)
        )
        await destination.send(
            f"<@{user.id}>",
            allowed_mentions=disnake.AllowedMentions.none(),
            embed=embed,
        )

    @commands.Cog.listener("on_class_updated")
    async def log_class_updated(
        self,
        settings: "ServerSettings",
        user: disnake.User,
        character: "Character",
        classname: str,
        classlvl: int,
    ):
        p = inflect.engine()
        embed = (
            disnake.Embed(
                title=f"{user.name} updated {p.plural(character.name)} {classname} to lvl {classlvl}"
            )
            .add_field(
                name="Previous Level:",
                value=f"{classname}: {classlvl}",
                inline=True,
            )
            .add_field(
                name="New Level:",
                value=f"{classname}: {character.multiclasses[classname]}",
                inline=True,
            )
        )
        destination: disnake.TextChannel = self.bot.get_channel(
            int(settings.loggingchar)
        )
        await destination.send(
            f"<@{user.id}>",
            allowed_mentions=disnake.AllowedMentions.none(),
            embed=embed,
        )

    # ==== auction logging ====


def setup(bot: "Labyrinthian"):
    bot.add_cog(Logging(bot))
