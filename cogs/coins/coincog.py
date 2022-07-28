import re
from typing import TYPE_CHECKING
import disnake
from disnake.ext import commands
import rapidfuzz
from utils.functions import search

from utils.models.coinpurse import Coin


if TYPE_CHECKING:
    from bot import Labyrinthian
    from utils.models.settings.guild import ServerSettings


class CoinsCog(commands.Cog):
    def __init__(self, bot: "Labyrinthian"):
        self.bot = bot

    # ==== top commands ====
    @commands.slash_command()
    async def coins(self, inter: disnake.ApplicationCommandInteraction):
        pass

    # ==== sub commands ====
    @coins.sub_command()
    async def mod(self, inter: disnake.ApplicationCommandInteraction, input: str):
        try:
            coin = await self.process_to_coin(str(inter.guild.id), input)
        except StopIteration:
            await inter.send("No matching currency type found", ephemeral=True)

    @coins.sub_command()
    async def pay(self, inter: disnake.ApplicationCommandInteraction):
        pass

    @coins.sub_command()
    async def set(self, inter: disnake.ApplicationCommandInteraction):
        pass

    # ==== helpers ====
    async def process_to_coin(self, guild_id: str, input: str):
        settings: "ServerSettings" = await self.bot.get_server_settings(
            guild_id, validate=False
        )
        cointypematch = rapidfuzz.process.extract(
            re.sub(r"[0-9]", "", input.strip()),
            [x.name for x in settings.coinconf] + [x.prefix for x in settings.coinconf],
            limit=8,
        )
        print(cointypematch)
        output = Coin(
            int(re.sub(r"[^0-9\-]", "", input)),
            settings.coinconf.base,
            next(
                x
                for x in settings.coinconf
                if x.name == cointypematch[0][0] or x.prefix == cointypematch[0][0]
            ),
            settings,
        )
        return output


def setup(bot: "Labyrinthian"):
    bot.add_cog(CoinsCog(bot))
