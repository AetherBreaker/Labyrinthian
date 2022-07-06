from typing import TYPE_CHECKING
import disnake
from disnake.ext import commands


if TYPE_CHECKING:
    from bot import Labyrinthian


class DMCog(commands.Cog):
    def __init__(self, bot: "Labyrinthian"):
        self.bot = bot

    @commands.slash_command()
    async def dm(self, inter: disnake.ApplicationCommandInteraction):
        pass

    @dm.sub_command()
    async def xp(self, inter: disnake.ApplicationCommandInteraction):
        pass
