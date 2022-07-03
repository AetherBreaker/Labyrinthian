from string import Template
from time import time
from typing import TYPE_CHECKING, Any, Dict, List

import disnake
from pydantic import ValidationError
import rapidfuzz
from cogs.badgelog.browser import create_CharSelect
from disnake.ext import commands
from pymongo.results import InsertOneResult
from utils.models.settings.character import Character


if TYPE_CHECKING:
    from bot import Labyrinthian
    from utils.models.settings.guild import ServerSettings


class Badges(commands.Cog):
    def __init__(self, bot: "Labyrinthian"):
        self.bot = bot

    # ==== standalone commands ====
    @commands.slash_command()
    @commands.cooldown(4, 1200.0, type=commands.BucketType.user)
    async def create(
        self,
        inter: disnake.ApplicationCommandInteraction,
        sheetlink: str,
        name: str,
        starting_class: str,
        starting_class_level: int,
    ):
        """Creates a badge log for your character
        Parameters
        ----------
        sheetlink: Valid character sheet URL.
        name: The name of your character.
        starting_class: Your character's starter class.
        starting_class_level: The level of your character's starter class."""
        settings: "ServerSettings" = await self.bot.get_server_settings(
            str(inter.guild.id)
        )
        errlist = []
        charlist = await self.bot.charcache.find_distinct_chardat(
            str(inter.guild.id), str(inter.author.id)
        )
        if name in charlist:
            errlist.append(f"name:\n\t{name} already exists!")
        try:
            char = Character(
                settings=settings,
                user=str(inter.author.id),
                guild=str(inter.guild.id),
                name=name,
                sheet=sheetlink,
                multiclasses={starting_class: starting_class_level},
            )
        except ValidationError as e:
            for x in e.errors():
                errlist.append(f"{x['loc'][0]}:\n\t{x['msg']}")
        if errlist:
            err = "While trying to create your character, the following error(s) occurred:\n"
            err += "\n".join(errlist)
            await inter.send(err, ephemeral=True)
            return
        else:
            await char.commit(self.bot.dbcache)
            self.bot.charcache.pop(f"{inter.guild.id}{inter.author.id}")
            await inter.response.send_message(
                f"Registered {name}'s badge log with the Adventurers Coalition."
            )
            embed = (
                disnake.Embed(
                    title=f"{name}'s Adventurers ID'",
                    description=f"Played by: <@{inter.author.id}>",
                    color=disnake.Color.random().value,
                    url=f"{char.sheet}",
                )
                .add_field(
                    name=f"{settings.xplabel} Information:",
                    value=f"Current Badges: {char.xp}\nExpected Level: {char.expected_level}",
                    inline=True,
                )
                .add_field(
                    name="Classes:",
                    value="\n".join(
                        [f"{x}: {y}" for x, y in char.multiclasses.items()]
                    ),
                    inline=True,
                )
                .add_field(
                    name=f"Total Levels: {char.level}", value="\u200B", inline=True
                )
            )
            await inter.channel.send(
                "Heres your adventurer's ID...",
                embed=embed,
            )

    @commands.slash_command()
    @commands.cooldown(5, 30.0, type=commands.BucketType.user)
    async def rename(
        self, inter: disnake.ApplicationCommandInteraction, name: str, newname: str
    ):
        """Change your character's name.
        Parameters
        ----------
        name: The name of your character.
        newname: Your character's new name."""
        character: "Character" = await self.bot.get_character(
            str(inter.guild.id), str(inter.author.id), name
        )
        if character is None:
            await inter.send(f"{name} doesn't exist!", ephemeral=True)
        else:
            character.name = newname
            await character.commit(self.bot.dbcache)
            await inter.send(f"{name}'s name changed to {newname}")

    @commands.slash_command(name="update-log")
    @commands.cooldown(3, 30.0, type=commands.BucketType.user)
    async def xp(
        self,
        inter: disnake.ApplicationCommandInteraction,
        name: str,
        badgeinput: float,
        awardingdm: disnake.Member,
    ):
        """Adds an entry to your characters badge log
        Parameters
        ----------
        name: The name of your character
        badgeinput: The amount of badges to add (or remove)
        awardingdm: The DM that awarded you badges, if fixing/adjusting your badges, select @Labyrinthian"""
        character: Dict[str, Any] = await self.bot.dbcache.find_one(
            f"BLCharList_{inter.guild.id}",
            {"user": str(inter.author.id), "character": name},
        )
        serverconf: ServerSettings = self.bot.get_server_settings(str(inter.guild.id))
        if character is None:
            await inter.response.send_message(f"{name} doesn't exist!")
        elif badgeinput == 0:
            await inter.response.send_message("You can't add zero badges!")
        elif not serverconf.is_dm(awardingdm) and not awardingdm == self.bot.user:
            await inter.response.send_message(f"<@{awardingdm.id}> isn't a DM!")
        else:
            timeStamp = int(time())
            newlog = {
                "charRefId": character["_id"],
                "user": str(inter.author.id),
                "character": name,
                "previous badges": character["currentbadges"],
                "badges added": badgeinput,
                "awarding DM": awardingdm.id,
                "timestamp": timeStamp,
            }
            objID: InsertOneResult = await self.bot.dbcache.insert_one(
                f"BadgeLogMaster_{inter.guild.id}", newlog
            )
            badgetemp: Dict[str, Any] = await self.bot.dbcache.find_one(
                "srvconf", {"guild": str(inter.guild.id)}
            )
            badgetemp = badgetemp["badgetemplate"]
            for x, y in badgetemp.items():
                if character["currentbadges"] + badgeinput >= y:
                    character["expectedlvl"] = x
            character["lastlog"] = objID.inserted_id
            character["lastlogtimeStamp"] = timeStamp
            character["currentbadges"] += badgeinput
            await self.bot.sdb[f"BLCharList_{inter.guild.id}"].replace_one(
                {"user": str(inter.author.id), "character": name}, character, True
            )
            templstr = (
                "$character lost badges $prev($input) to $awarding"
                if badgeinput < 0
                else "$character was awarded badges $prev($input) by $awarding"
            )
            mapping = {
                "character": f"{name}",
                "prev": f"{character['currentbadges']-badgeinput}",
                "input": f"{'' if badgeinput < 0 else '+'}{badgeinput}",
                "awarding": f"<@{awardingdm.id}>",
            }
            await inter.response.send_message(
                embed=disnake.Embed(
                    title=f"Badge log updated",
                    description=f"{'' if character['user'] == newlog['user'] else '<@'+newlog['user']+'> at'} <t:{timeStamp}:f>\n{Template(templstr).substitute(**mapping)}",
                )
            )

    @commands.slash_command(name="log-browser")
    @commands.cooldown(3, 30.0, type=commands.BucketType.user)
    async def character(self, inter: disnake.ApplicationCommandInteraction):
        """Displays your character's badgelog data.
        Parameters
        ----------
        name: The name of your character."""
        await create_CharSelect(inter, self.bot, inter.author, inter.guild)

    # ==== command families ====
    @commands.slash_command(
        name="class", description="Set your characters classes in their badge log."
    )
    async def classes(self, _: disnake.ApplicationCommandInteraction):
        pass

    @classes.sub_command()
    @commands.cooldown(3, 30.0, type=commands.BucketType.user)
    async def add(
        self,
        inter: disnake.ApplicationCommandInteraction,
        name: str,
        multiclass_name: str,
        multiclass_level: int,
    ):
        """Adds a multiclass to your character log.
        Parameters
        ----------
        name: The name of your character.
        multiclass_name: The class your multiclassing into.
        multiclass_level: The level of your new multiclass."""
        char: "Character" = await self.bot.get_character(
            str(inter.guild.id), str(inter.author.id), name
        )
        if char is None:
            await inter.send(f"{name} doesn't exist!", ephemeral=True)
            return
        classlist = await self._get_classlist(str(inter.guild.id))
        classlist = [x for x in classlist if x not in char.multiclasses]
        if multiclass_name not in classlist:
            await inter.send(
                f"{multiclass_name} is not a valid class, try using the autocompletion to select a class.",
                ephemeral=True,
            )
            return
        if len(char["classes"]) >= 5:
            await inter.send(f"You can't have more than 5 classes!", ephemeral=True)
            return
        if multiclass_level < 1:
            await inter.send("You can't have a level less than zero.", ephemeral=True)
            return
        char.multiclasses[multiclass_name] = multiclass_level
        await char.commit(self.bot.dbcache)
        await inter.send(f"{name} multiclassed into {multiclass_name}!")

    @classes.sub_command()
    @commands.cooldown(3, 30.0, type=commands.BucketType.user)
    async def remove(
        self,
        inter: disnake.ApplicationCommandInteraction,
        name: str,
        multiclass_name: str,
    ):
        """Removes a multiclass from your character log.
        Parameters
        ----------
        name: The name of your character.
        multiclass_name: The class you wish to remove."""
        char: "Character" = await self.bot.get_character(
            str(inter.guild.id), str(inter.author.id), name
        )
        if char is None:
            await inter.send(f"{name} doesn't exist!", ephemeral=True)
            return
        if multiclass_name not in char.multiclasses:
            await inter.send(
                f"{name} isn't {'an' if multiclass_name == 'Artificer' else 'a'} {multiclass_name}",
                ephemeral=True,
            )
            return
        char.multiclasses.pop(multiclass_name)
        await char.commit(self.bot.dbcache)
        await inter.send(f"{name} is no longer a {multiclass_name}")

    @classes.sub_command()
    @commands.cooldown(3, 30.0, type=commands.BucketType.user)
    async def update(
        self,
        inter: disnake.ApplicationCommandInteraction,
        name: str,
        multiclass_name: str,
        multiclass_level: int = commands.Param(gt=0, le=20),
    ):
        """Used to update the level of your character's multiclasses.
        Parameters
        ----------
        name: The name of your character.
        multiclass_name: The class you're updating.
        multiclass_level: The new level of your class."""
        char: "Character" = await self.bot.get_character(
            str(inter.guild.id), str(inter.author.id), name
        )
        if char is None:
            await inter.send(f"{name} doesn't exist!", ephemeral=True)
            return
        if multiclass_name not in char.multiclasses:
            await inter.send(
                f"{name} isn't {'an' if multiclass_name == 'Artificer' else 'a'} {multiclass_name}",
                ephemeral=True,
            )
            return
        if multiclass_level < 1:
            await inter.send("You can't have a level less than zero.", ephemeral=True)
            return
        char.multiclasses[multiclass_name] = multiclass_level
        char.commit(self.bot.dbcache)
        await inter.send(
            f"{name}'s {multiclass_name} level changed to {multiclass_level}"
        )

    # ==== autocompletion ====
    @create.autocomplete("starting_class")
    async def autocomp_all_classes(
        self, inter: disnake.ApplicationCommandInteraction, user_input: str
    ):
        classlist = await self._get_classlist(str(inter.guild.id))
        return [x[0] for x in rapidfuzz.process.extract(user_input, classlist, limit=8)]

    @rename.autocomplete("name")
    @add.autocomplete("name")
    @remove.autocomplete("name")
    @update.autocomplete("name")
    @xp.autocomplete("name")
    async def autocomp_names(
        self, inter: disnake.ApplicationCommandInteraction, user_input: str
    ):
        charlist: List[str] = await self.bot.charcache.find_distinct_chardat(
            str(inter.guild.id), str(inter.author.id)
        )
        return [x[0] for x in rapidfuzz.process.extract(user_input, charlist, limit=8)]

    @add.autocomplete("multiclass_name")
    async def autocomp_remaining_classes(
        self, inter: disnake.ApplicationCommandInteraction, user_input: str
    ):
        name = inter.filled_options["name"]
        char: "Character" = await self.bot.get_character(
            str(inter.guild.id), str(inter.author.id), name
        )
        classlist = await self._get_classlist(str(inter.guild.id))
        classlist = [x for x in classlist if x not in char.multiclasses]
        return [x[0] for x in rapidfuzz.process.extract(user_input, classlist, limit=8)]

    @remove.autocomplete("multiclass_name")
    @update.autocomplete("multiclass_name")
    async def autocomp_existing_classes(
        self, inter: disnake.ApplicationCommandInteraction, user_input: str
    ):
        name = inter.filled_options["name"]
        char: "Character" = await self.bot.get_character(
            str(inter.guild.id), str(inter.author.id), name
        )
        return [
            x[0]
            for x in rapidfuzz.process.extract(
                user_input, list(char.multiclasses.keys()), limit=8
            )
        ]

    # ==== helpers ====
    async def _get_classlist(self, guild_id):
        settings: "ServerSettings" = await self.bot.get_server_settings(str(guild_id))
        return settings.classlist


def setup(bot):
    bot.add_cog(Badges(bot))
