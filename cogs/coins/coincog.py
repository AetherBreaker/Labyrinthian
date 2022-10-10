import itertools
import re
from typing import TYPE_CHECKING, NewType, Tuple

import disnake
import inflect
import rapidfuzz
from disnake.ext import commands

from utils.models.coinpurse import CoinPurse
from utils.ui.uiprompts import CharacterSelectPrompt

if TYPE_CHECKING:
    from bot import Labyrinthian
    from utils.models.character import Character
    from utils.models.settings.guild import ServerSettings
    from utils.models.settings.user import UserPreferences


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
        amount, uprefs, char = await self.run_prechecks(inter, input)
        if not amount or not uprefs or not char:
            return
        if amount.baseval < 0 and abs(amount.baseval) > char.coinpurse.baseval:
            await inter.send("You don't have enough money for that!", ephemeral=True)
            return
        char.coinpurse.combine_batch(amount)
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
    async def pay(
        self,
        inter: disnake.ApplicationCommandInteraction,
        target_user: disnake.Member,
        input: str,
    ):
        amount, authprefs, char = await self.run_prechecks(inter, input)
        if not amount or not authprefs or not char:
            return
        if amount.baseval < 0 and abs(amount.baseval) > char.coinpurse.baseval:
            await inter.send("You don't have enough money for that!", ephemeral=True)
            return
        targprefs = await self.bot.get_user_prefs(str(target_user.id), validate=False)
        p = inflect.engine()
        components = [
            disnake.ui.Select(
                custom_id="target_character_select",
                placeholder=f"Select one of {p.plural(target_user.name)} characters.",
                min_values=1,
                max_values=1,
                options=[
                    disnake.SelectOption(label=character, value=str(objid))
                    for character, objid in targprefs.characters[
                        str(inter.guild.id)
                    ].items()
                ],
            )
        ]
        prompt = UIPrompt.from_dict(self.bot, inter, components, wait_for_submit=True)
        await prompt.send_prompt(inter)
        data = await prompt.listen()
        print(data)

    @coins.sub_command()
    async def set(self, inter: disnake.ApplicationCommandInteraction, input: str):
        amount, uprefs, char = await self.run_prechecks(inter, input)
        if not amount or not uprefs or not char:
            return
        char.coinpurse.set_coins(amount)
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
            if not char:
                await inter.send("You have no active character!", ephemeral=True)
                return
            char.coinpurse.convert()
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
            await char.commit(self.bot.dbcache)

    # ==== autocompletion ====

    # ==== helpers ====
    async def run_prechecks(
        self, inter: disnake.ApplicationCommandInteraction, input
    ) -> Tuple["CoinPurse", "UserPreferences", "Character"]:
        amount = await self.process_to_coinpurse(str(inter.guild.id), input)
        if len(amount) == 0:
            await inter.send("No matching currency types found", ephemeral=True)
            return None, None, None
        uprefs = await self.bot.get_user_prefs(str(inter.author.id), validate=False)
        if not uprefs.has_valid_activechar(str(inter.guild.id)):
            await inter.send("You have no active character!", ephemeral=True)
            return None, None, None
        char = await self.bot.get_char_by_oid(uprefs.activechar[str(inter.guild.id)].id)
        if not char:
            await inter.send("You have no active character!", ephemeral=True)
            return None, None, None
        return amount, uprefs, char

    async def process_to_coinpurse(
        self,
        guild_id: str,
        input: str,
        coerce_positive: bool = False,
        force_int: bool = False,
    ):
        settings: "ServerSettings" = await self.bot.get_server_settings(
            guild_id, validate=False
        )
        tables = []
        result = {}
        input = re.sub(r"((?<=-) +)|([ \.]+(?=[a-zA-Z\.]+))|((?<= ) +)", "", input)
        items = re.split(r"[^a-zA-Z0-9'\-\.]", input)
        for enum, item in enumerate(items):
            if re.search(r"-$", item):
                if enum < (len(items) - 1) and not re.match(r"[-]+", items[enum + 1]):
                    items[enum + 1] = "-" + items[enum + 1]
            count = re.sub(r"[^\-\d\.\s]|[^\d]*$", "", item)
            if coerce_positive:
                count = abs(float(count))
            if force_int:
                count = int(count)
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
