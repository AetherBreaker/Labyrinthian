from typing import TYPE_CHECKING
import disnake
from disnake.ext import commands


if TYPE_CHECKING:
    from bot import Labyrinthian


class CoinsCog(commands.Cog):
    def __init__(self, bot: "Labyrinthian"):
        self.bot = bot

    # ==== top commands ====
    @commands.slash_command()
    async def coins(self, inter: disnake.ApplicationCommandInteraction):
        pass

    # ==== sub commands ====
    @coins.sub_command()
    async def mod(self, inter: disnake.ApplicationCommandInteraction):
        pass

    @coins.sub_command()
    async def pay(self, inter: disnake.ApplicationCommandInteraction):
        pass

    @coins.sub_command()
    async def set(self, inter: disnake.ApplicationCommandInteraction):
        pass

    # ==== helpers ====
    def process_input(self, input):
        pass


def setup(bot: "Labyrinthian"):
    bot.add_cog(CoinsCog(bot))
