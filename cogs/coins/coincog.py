import re
from typing import TYPE_CHECKING

import disnake
import rapidfuzz
from disnake.ext import commands
from utils.models.coinpurse import Coin, CoinPurse

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
        amount = await self.process_to_coinpurse(str(inter.guild.id), input)
        if len(amount) == 0:
            await inter.send("No matching currency types found", ephemeral=True)
            return
        uprefs = await self.bot.get_user_prefs(str(inter.author.id), validate=False)
        if not str(inter.guild.id) in uprefs.activechar:
            await inter.send("You have no active character!", ephemeral=True)
            return
        char = await self.bot.get_char_by_oid(uprefs.activechar[str(inter.guild.id)].id)
        if amount.baseval < 0 and abs(amount.baseval) > char.coinpurse.baseval:
            await inter.send("You don't have enough money for that!", ephemeral=True)
            return
        char.coinpurse = char.coinpurse + amount
        await char.commit(self.bot.dbcache)

    @coins.sub_command()
    async def pay(self, inter: disnake.ApplicationCommandInteraction):
        pass

    @coins.sub_command()
    async def set(self, inter: disnake.ApplicationCommandInteraction, input: str):
        amount = await self.process_to_coinpurse(str(inter.guild.id), input)
        if len(amount) == 0:
            await inter.send("No matching currency types found", ephemeral=True)
        await inter.send(f"amount={amount.coinlist}")

    # ==== helpers ====
    async def process_to_coinpurse(self, guild_id: str, input: str):
        settings: "ServerSettings" = await self.bot.get_server_settings(
            guild_id, validate=False
        )
        result = []
        items = re.split(r"[^a-zA-Z0-9'-]", input)
        for x in items:
            prefix = re.sub(r"[0-9\-]", "", x)
            cointypematch = rapidfuzz.process.extract(
                re.sub(r"[0-9]", "", x),
                [x.name for x in settings.coinconf]
                + [x.prefix for x in settings.coinconf],
                limit=8,
            )
            try:
                result.append(
                    Coin(
                        int(re.sub(r"[^0-9\-]", "", x)),
                        settings.coinconf.base,
                        next(
                            x
                            for x in settings.coinconf
                            if x.name == cointypematch[0][0]
                            or x.prefix == cointypematch[0][0]
                        ),
                        settings,
                    )
                )
            except StopIteration:
                continue
        result = sorted(result, key=lambda i: (i.type.rate, i.type.name, i.type.prefix))
        return CoinPurse(result, settings.coinconf)

    async def float_to_coinpurse(self):
        pass


def setup(bot: "Labyrinthian"):
    bot.add_cog(CoinsCog(bot))
