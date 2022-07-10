from typing import TYPE_CHECKING, NewType
import disnake
from disnake.ext import commands


if TYPE_CHECKING:
    from bot import Labyrinthian
    from utils.models.settings.user import ActiveCharacter


UserID = NewType("UserID", str)
GuildID = NewType("GuildID", str)
CharacterName = NewType("CharacterName", str)


class Logging(commands.Cog):
    def __init__(self, bot: "Labyrinthian"):
        self.bot = bot

    @commands.Cog.listener("on_changed_character")
    async def log_charchange(
        self,
        guild: disnake.Guild,
        user: disnake.User,
        newchar: "ActiveCharacter",
        oldchar: "ActiveCharacter",
    ):
        pass
