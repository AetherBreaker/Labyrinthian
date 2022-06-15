from http import server
from string import Template
from time import time
from typing import TYPE_CHECKING, Any, Dict, List, TypeVar

import disnake
from cogs.badgelog.browser import create_CharSelect
from disnake.ext import commands
from pymongo.results import InsertOneResult
from utils.checks import urlCheck
from utils.settings.guild import ServerSettings

_LabyrinthianT = TypeVar("_LabyrinthianT", bound=disnake.Client)
if TYPE_CHECKING:
    from bot import Labyrinthian

    _LabyrinthianT = Labyrinthian


class Badges(commands.Cog):
    def __init__(self, bot: _LabyrinthianT):
        self.bot = bot
        self.valid = [
            "Artificer",
            "Barbarian",
            "Bard",
            "Blood Hunter",
            "Cleric",
            "Druid",
            "Fighter",
            "Monk",
            "Paladin",
            "Ranger",
            "Rogue",
            "Sorcerer",
            "Warlock",
            "Wizard",
        ]

    async def validateClass(self, guildID):
        """Returns a list of valid classes from classlist in the server config if exists, otherwise the Badges default valid classes.
        Parameters
        ----------
        self: The Badges class. It may be better to move this within the class.
        guildID: Put inter.guild.id here."""
        srvconf: Dict[str, Any] = await self.bot.dbcache.find_one(
            "srvconf", {"guild": str(guildID)}
        )
        if "classlist" in srvconf:
            if srvconf["classlist"]:
                validc = srvconf["classlist"]
            else:
                validc = self.valid
        else:
            validc = self.valid
        return validc

    @commands.slash_command()
    @commands.cooldown(4, 1200.0, type=commands.BucketType.user)
    async def create(
        self,
        inter: disnake.ApplicationCommandInteraction,
        sheetlink: str,
        charname: str,
        startingclass: str,
        startingclasslevel: int = commands.Param(gt=0, le=20),
    ):
        """Creates a badge log for your character
        Parameters
        ----------
        sheetlink: Valid character sheet URL.
        charname: The name of your character.
        startingclass: Your character's starter class.
        startingclasslevel: The level of your character's starter class."""
        validc = await self.validateClass(inter.guild.id)
        if startingclass not in validc:
            await inter.response.send_message(
                f"{startingclass} is not a valid class, try using the autocompletion to select a class."
            )
        else:
            if urlCheck(sheetlink):
                character: Dict[str, Any] = await self.bot.dbcache.find_one(
                    f"BLCharList_{inter.guild.id}",
                    {"user": str(inter.author.id), "character": charname},
                )
                if character != None:
                    await inter.response.send_message(
                        f"{charname}'s badge log already exists!"
                    )
                else:
                    char = {
                        "user": str(inter.author.id),
                        "sheet": sheetlink,
                        "character": charname,
                        "charlvl": startingclasslevel,
                        "classes": {
                            startingclass: startingclasslevel,
                        },
                        "currentbadges": 0,
                        "expectedlvl": 1,
                        "lastlog": None,
                        "lastlogtime": time(),
                    }
                    await self.bot.sdb[f"BLCharList_{inter.guild.id}"].insert_one(char)
                    self.bot.charcache.pop(f"{inter.guild.id}{inter.author.id}")
                    await inter.response.send_message(
                        f"Registered {charname}'s badge log with the Adventurers Coalition."
                    )
                    Embed = {
                        "title": f"{charname}'s Adventurers ID'",
                        "description": f"Played by: <@{inter.author.id}>",
                        "color": disnake.Color.random().value,
                        "url": f"{char['sheet']}",
                        "fields": [
                            {
                                "name": "Badge Information:",
                                "value": f"Current Badges: {char['currentbadges']}\nExpected Level: {char['expectedlvl']}",
                                "inline": True,
                            },
                            {
                                "name": "Class Levels:",
                                "value": "\n".join(
                                    [f"{x}: {y}" for x, y in char["classes"].items()]
                                ),
                                "inline": True,
                            },
                            {
                                "name": f"Total Levels: {char['charlvl']}",
                                "value": "\u200B",
                                "inline": True,
                            },
                        ],
                    }
                    await inter.channel.send(
                        "Heres your adventurer's ID...",
                        embed=disnake.Embed.from_dict(Embed),
                    )
            else:
                await inter.response.send_message(
                    "Sheet type does not match accepted formats, or is not a valid URL."
                )

    @create.autocomplete("startingclass")
    async def autocomp_class(
        self, inter: disnake.ApplicationCommandInteraction, user_input: str
    ):
        validc = await self.validateClass(inter.guild.id)
        return [
            name
            for name in validc
            if "".join(user_input.split()).casefold()
            in "".join(name.split()).casefold()
        ]

    @commands.slash_command()
    @commands.cooldown(5, 30.0, type=commands.BucketType.user)
    async def rename(
        self, inter: disnake.ApplicationCommandInteraction, charname: str, newname: str
    ):
        """Change your characters name!
        Parameters
        ----------
        charname: The name of your character.
        newname: Your characters new name."""
        character: Dict[str, Any] = await self.bot.dbcache.find_one(
            f"BLCharList_{inter.guild.id}",
            {"user": str(inter.author.id), "character": charname},
        )
        if character is None:
            await inter.response.send_message(f"{charname} doesn't exist!")
        else:
            character["character"] = newname
            await self.bot.sdb[f"BLCharList_{inter.guild.id}"].replace_one(
                {"user": str(inter.author.id), "character": charname}, character
            )
            await inter.response.send_message(f"{charname}'s name changed to {newname}")

    @rename.autocomplete("charname")
    async def autocomp_charnames(
        self, inter: disnake.ApplicationCommandInteraction, user_input: str
    ):
        charlist: List[str] = await self.bot.charcache.find_distinct_chardat(
            str(inter.guild.id), str(inter.author.id)
        )
        return [
            name
            for name in charlist
            if "".join(user_input.split()).casefold()
            in "".join(name.split()).casefold()
        ]

    @commands.slash_command(
        description="Set your characters classes in their badge log."
    )
    async def classes(self, inter: disnake.ApplicationCommandInteraction):
        pass

    @classes.sub_command()
    @commands.cooldown(3, 30.0, type=commands.BucketType.user)
    async def add(
        self,
        inter: disnake.ApplicationCommandInteraction,
        charname: str,
        multiclassname: str,
        multiclasslevel: int = commands.Param(gt=0, le=20),
    ):
        """Adds a multiclass to your character's badge log.
        Parameters
        ----------
        charname: The name of your character.
        multiclassname: The class your multiclassing into.
        multiclasslevel: The level of your new multiclass."""
        srvconf: Dict[str, Any] = await self.bot.dbcache.find_one(
            "srvconf", {"guild": str(inter.guild.id)}
        )
        validc = (
            self.valid
            if srvconf is None or "classlist" not in srvconf
            else srvconf["classlist"]
        )
        if multiclassname not in validc:
            await inter.response.send_message(
                f"{multiclassname} is not a valid class, try using the autocompletion to select a class."
            )
        else:
            character: Dict[str, Any] = await self.bot.dbcache.find_one(
                f"BLCharList_{inter.guild.id}",
                {"user": str(inter.author.id), "character": charname},
            )
            if character is None:
                await inter.response.send_message(f"{charname} doesn't exist!")
            elif len(character["classes"]) < 5:
                if (sum(character["classes"].values()) + multiclasslevel) > 20:
                    multiclasslevel -= (
                        sum(character["classes"].values()) + multiclasslevel
                    ) - 20
                    if (sum(character["classes"].values()) + multiclasslevel) > 20:
                        await inter.response.send_message(f"That level is too high")
                        return
                character["classes"][multiclassname] = multiclasslevel
                character["charlvl"] = sum(character["classes"].values())
                await self.bot.sdb[f"BLCharList_{inter.guild.id}"].replace_one(
                    {"user": str(inter.author.id), "character": charname}, character
                )
                await inter.response.send_message(
                    f"{charname} multiclassed into {multiclassname}!"
                )

    @add.autocomplete("charname")
    async def autocomp_charnames(
        self, inter: disnake.ApplicationCommandInteraction, user_input: str
    ):
        charlist: List[str] = await self.bot.charcache.find_distinct_chardat(
            str(inter.guild.id), str(inter.author.id)
        )
        return [
            name
            for name in charlist
            if "".join(user_input.split()).casefold()
            in "".join(name.split()).casefold()
        ]

    @add.autocomplete("multiclassname")
    async def autocomp_class(
        self, inter: disnake.ApplicationCommandInteraction, user_input: str
    ):
        charname = inter.filled_options["charname"]
        char: Dict[str, Any] = await self.bot.dbcache.find_one(
            f"BLCharList_{inter.guild.id}",
            {"user": str(inter.author.id), "character": charname},
        )
        validc = await self.validateClass(inter.guild.id)
        validclasses = (
            [x for x in validc if x not in char["classes"]]
            if char is not None
            else validc
        )
        return [
            name
            for name in validclasses
            if "".join(user_input.split()).casefold()
            in "".join(name.split()).casefold()
        ]

    @classes.sub_command()
    @commands.cooldown(3, 30.0, type=commands.BucketType.user)
    async def remove(
        self,
        inter: disnake.ApplicationCommandInteraction,
        charname: str,
        multiclassname: str,
    ):
        """Removes a multiclass from your character's badge log.
        Parameters
        ----------
        charname: The name of your character.
        multiclassname: The class you wish to remove."""
        character: Dict[str, Any] = await self.bot.dbcache.find_one(
            f"BLCharList_{inter.guild.id}",
            {"user": str(inter.author.id), "character": charname},
        )
        if character is None:
            await inter.response.send_message(f"{charname} doesn't exist!")
        elif multiclassname not in character["classes"].keys():
            await inter.response.send_message(
                f"{charname} isn't {'an' if multiclassname == 'Artificer' else 'a'} {multiclassname}"
            )
        else:
            character["classes"].pop(multiclassname)
            character["charlvl"] = sum(character["classes"].values())
            await self.bot.sdb[f"BLCharList_{inter.guild.id}"].replace_one(
                {"user": str(inter.author.id), "character": charname}, character
            )
            await inter.response.send_message(
                f"{charname} is no longer a {multiclassname}"
            )

    @remove.autocomplete("charname")
    async def autocomp_charnames(
        self, inter: disnake.ApplicationCommandInteraction, user_input: str
    ):
        charlist: List[str] = await self.bot.charcache.find_distinct_chardat(
            str(inter.guild.id), str(inter.author.id)
        )
        return [
            name
            for name in charlist
            if "".join(user_input.split()).casefold()
            in "".join(name.split()).casefold()
        ]

    @remove.autocomplete("multiclassname")
    async def autocomp_class(
        self, inter: disnake.ApplicationCommandInteraction, user_input: str
    ):
        charname = inter.filled_options["charname"]
        char: Dict[str, Any] = await self.bot.dbcache.find_one(
            f"BLCharList_{inter.guild.id}",
            {"user": str(inter.author.id), "character": charname},
        )
        validclasses = char["classes"].keys()
        return [
            name
            for name in validclasses
            if "".join(user_input.split()).casefold()
            in "".join(name.split()).casefold()
        ]

    @classes.sub_command()
    @commands.cooldown(3, 30.0, type=commands.BucketType.user)
    async def update(
        self,
        inter: disnake.ApplicationCommandInteraction,
        charname: str,
        multiclassname: str,
        multiclasslevel: int = commands.Param(gt=0, le=20),
    ):
        """Used to update the level of one of your characters multiclasses in their badge log.
        Parameters
        ----------
        charname: The name of your character.
        multiclassname: The class you're updating.
        multiclasslevel: The new level of your class."""
        character: Dict[str, Any] = await self.bot.dbcache.find_one(
            f"BLCharList_{inter.guild.id}",
            {"user": str(inter.author.id), "character": charname},
        )
        if character is None:
            await inter.response.send_message(f"{charname} doesn't exist!")
        elif multiclassname not in character["classes"].keys():
            await inter.response.send_message(
                f"{charname} isn't {'an' if multiclassname == 'Artificer' else 'a'} {multiclassname}"
            )
        else:
            if (sum(character["classes"].values()) + multiclasslevel) > 20:
                multiclasslevel -= (
                    sum(character["classes"].values()) + multiclasslevel
                ) - 20
                if (sum(character["classes"].values()) + multiclasslevel) > 20:
                    await inter.response.send_message(f"That level is too high")
                    return
            character["classes"][multiclassname] = multiclasslevel
            character["charlvl"] = sum(character["classes"].values())
            await self.bot.sdb[f"BLCharList_{inter.guild.id}"].replace_one(
                {"user": str(inter.author.id), "character": charname}, character
            )
            await inter.response.send_message(
                f"{charname}'s {multiclassname} level changed to {multiclasslevel}"
            )

    @update.autocomplete("charname")
    async def autocomp_charnames(
        self, inter: disnake.ApplicationCommandInteraction, user_input: str
    ):
        charlist: List[str] = await self.bot.charcache.find_distinct_chardat(
            str(inter.guild.id), str(inter.author.id)
        )
        return [
            name
            for name in charlist
            if "".join(user_input.split()).casefold()
            in "".join(name.split()).casefold()
        ]

    @update.autocomplete("multiclassname")
    async def autocomp_class(
        self, inter: disnake.ApplicationCommandInteraction, user_input: str
    ):
        charname = inter.filled_options["charname"]
        char: Dict[str, Any] = await self.bot.dbcache.find_one(
            f"BLCharList_{inter.guild.id}",
            {"user": str(inter.author.id), "character": charname},
        )
        validclasses = char["classes"].keys()
        return [
            name
            for name in validclasses
            if "".join(user_input.split()).casefold()
            in "".join(name.split()).casefold()
        ]

    @commands.slash_command(name="update-log")
    @commands.cooldown(3, 30.0, type=commands.BucketType.user)
    async def updatelog(
        self,
        inter: disnake.ApplicationCommandInteraction,
        charname: str,
        badgeinput: float,
        awardingdm: disnake.Member,
    ):
        """Adds an entry to your characters badge log
        Parameters
        ----------
        charname: The name of your character
        badgeinput: The amount of badges to add (or remove)
        awardingdm: The DM that awarded you badges, if fixing/adjusting your badges, select @Labyrinthian"""
        character: Dict[str, Any] = await self.bot.dbcache.find_one(
            f"BLCharList_{inter.guild.id}",
            {"user": str(inter.author.id), "character": charname},
        )
        serverconf: ServerSettings = self.bot.get_server_settings(str(inter.guild.id))
        if character is None:
            await inter.response.send_message(f"{charname} doesn't exist!")
        elif badgeinput == 0:
            await inter.response.send_message("You can't add zero badges!")
        elif not serverconf.is_dm(awardingdm) and not awardingdm == self.bot.user:
            await inter.response.send_message(f"<@{awardingdm.id}> isn't a DM!")
        else:
            timeStamp = int(time())
            newlog = {
                "charRefId": character["_id"],
                "user": str(inter.author.id),
                "character": charname,
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
                {"user": str(inter.author.id), "character": charname}, character, True
            )
            templstr = (
                "$character lost badges $prev($input) to $awarding"
                if badgeinput < 0
                else "$character was awarded badges $prev($input) by $awarding"
            )
            mapping = {
                "character": f"{charname}",
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

    @updatelog.autocomplete("charname")
    async def autocomp_charnames(
        self, inter: disnake.ApplicationCommandInteraction, user_input: str
    ):
        charlist: List[str] = await self.bot.charcache.find_distinct_chardat(
            str(inter.guild.id), str(inter.author.id)
        )
        return [
            name
            for name in charlist
            if "".join(user_input.split()).casefold()
            in "".join(name.split()).casefold()
        ]

    @commands.slash_command(name="log-browser")
    @commands.cooldown(3, 30.0, type=commands.BucketType.user)
    async def logbrowser(self, inter: disnake.ApplicationCommandInteraction):
        """Displays your character's badgelog data.
        Parameters
        ----------
        charname: The name of your character."""
        await create_CharSelect(inter, self.bot, inter.author, inter.guild)


def setup(bot):
    bot.add_cog(Badges(bot))
