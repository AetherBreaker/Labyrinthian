import itertools
import re
from typing import TYPE_CHECKING

import disnake
import inflect
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
        if not uprefs.has_valid_activechar(str(inter.guild.id)):
            await inter.send("You have no active character!", ephemeral=True)
            return

        char = await self.bot.get_char_by_oid(uprefs.activechar[str(inter.guild.id)].id)

        if amount.baseval < 0 and abs(amount.baseval) > char.coinpurse.baseval:
            await inter.send("You don't have enough money for that!", ephemeral=True)
            return

        char.coinpurse = char.coinpurse.combine_batch(amount)

        totalresult = char.coinpurse.baseval
        totalchange = char.coinpurse.basechangeval
        p = inflect.engine()
        result = (
            disnake.Embed(
                title=f"{char.name}'s Coinpurse",
                description=char.coinpurse.display_operation,
                color=disnake.Colour.random(),
            )
            .add_field(name="Total Value", value=char.coinpurse.display_operation_total)
            .set_thumbnail(
                "https://www.dndbeyond.com/attachments/thumbnails/3/929/650/358/scag01-04.png"
            )
        )
        await inter.send(embed=result)

        await char.commit(self.bot.dbcache)

    @coins.sub_command()
    async def pay(self, inter: disnake.ApplicationCommandInteraction):
        pass

    @coins.sub_command()
    async def set(self, inter: disnake.ApplicationCommandInteraction, input: str):
        pass

    @coins.sub_command()
    async def convert(
        self,
        inter: disnake.ApplicationCommandInteraction,
        toggle: str = commands.Param(default=None, choices=["On", "Off"]),
    ):
        uprefs = await self.bot.get_user_prefs(str(inter.author.id))
        if toggle:
            uprefs.coinconvert = True if toggle == "On" else False
            await uprefs.commit(self.bot.dbcache)
            await inter.send(
                f"Automatic coin conversion {'enabled' if toggle == 'On' else 'disabled'}"
            )
        else:
            if not uprefs.has_valid_activechar(str(inter.guild.id)):
                await inter.send("You have no active character!", ephemeral=True)
                return
            char = await self.bot.get_char_by_oid(
                uprefs.activechar[str(inter.guild.id)].id
            )
            char.coinpurse.convert()
            await char.commit(self.bot.dbcache)
            totalresult = char.coinpurse.baseval
            totalchange = char.coinpurse.basechangeval
            p = inflect.engine()
            result = (
                disnake.Embed(
                    title=f"{char.name}'s Coinpurse",
                    description=char.coinpurse.display_operation,
                    color=disnake.Colour.random(),
                )
                .add_field(
                    name="Total Value", value=char.coinpurse.display_operation_total
                )
                .set_thumbnail(
                    "https://www.dndbeyond.com/attachments/thumbnails/3/929/650/358/scag01-04.png"
                )
            )
            await inter.send(embed=result)

    # ==== autocompletion ====

    # ==== helpers ====
    async def process_to_coinpurse(
        self, guild_id: str, input: str, coerce_positive: bool = False
    ):
        settings: "ServerSettings" = await self.bot.get_server_settings(
            guild_id, validate=False
        )
        tables = []
        result = {}
        items = re.split(r"[^a-zA-Z0-9'\-\.]", input)
        for enum, item in enumerate(items):
            if re.search(r"-$", item):
                if enum < (len(items) - 1) and not re.match(r"[-]+", items[enum + 1]):
                    items[enum + 1] = "-" + items[enum + 1]
            count = re.sub(r"[^\-\d\.\s]|[^\d]*$", "", item)
            if coerce_positive:
                count = abs(float(count))
            prefix = re.sub(r"[0-9\-\.]", "", item)
            cointypematch = rapidfuzz.process.extractOne(
                settings.coinconf.base.prefix if prefix == "" else prefix,
                itertools.chain.from_iterable(
                    (x.name, x.prefix) for x in settings.coinconf
                ),
            )[0]
            tables.append(
                CoinPurse.valuedict_from_count(
                    count,
                    disnake.utils.find(
                        lambda ctype: ctype.name == cointypematch
                        or ctype.prefix == cointypematch,
                        settings.coinconf,
                    ),
                    settings.coinconf,
                )
            )
        for tab in next(iter(tables)):
            result[tab] = sum(x[tab] for x in tables if x[tab] != 0)
        return CoinPurse.from_simple_dict(result, settings.coinconf)


def setup(bot: "Labyrinthian"):
    bot.add_cog(CoinsCog(bot))
