from copy import deepcopy
from time import time
from typing import TYPE_CHECKING, List

import disnake
import inflect
import rapidfuzz
from disnake.ext import commands
from pydantic import ValidationError
from pymongo.results import InsertOneResult
from utils.models.character import Character
from utils.models.coinpurse import CoinPurse
from utils.models.settings.user import ActiveCharacter
from utils.models.xplog import XPLogEntry
from utils.ui.logui import LogMenu

if TYPE_CHECKING:
    from bot import Labyrinthian
    from utils.models.settings.guild import ServerSettings
    from utils.models.settings.user import UserPreferences
    from utils.MongoCache import UpdateResultFacade


class CharacterLog(
    commands.Cog,
    slash_command_attrs={
        "default_member_permissions": disnake.Permissions(permissions=3072)
    },
):
    def __init__(self, bot: "Labyrinthian"):
        self.bot = bot

    # ==== top lvl commands ====
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
        charlist = await self.bot.charcache.find_distinct_chardat(
            str(inter.guild.id), str(inter.author.id)
        )
        if len(charlist) >= 25:
            await inter.send(
                "You have reached the character cap, please contact a staff member to remove one "
                "of your pre-existing character.",
                ephemeral=True,
            )
            return
        settings: "ServerSettings" = await self.bot.get_server_settings(
            str(inter.guild.id), validate=False
        )
        errlist = []
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
                coinpurse=CoinPurse.from_dict(
                    {
                        "coinlist": settings.coinconf.create_empty_coinlist(),
                        "config": settings.coinconf,
                    }
                ),
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
            result: "UpdateResultFacade" = await char.commit(self.bot.dbcache)
            uprefs: "UserPreferences" = await self.bot.get_user_prefs(
                str(inter.author.id)
            )
            if str(inter.guild.id) not in uprefs.characters:
                uprefs.characters[str(inter.guild.id)] = {}
            uprefs.characters[str(inter.guild.id)][name] = result.inserted_id
            uprefs.activechar[str(inter.guild.id)] = ActiveCharacter(
                name=name, id=result.inserted_id
            )
            await uprefs.commit(self.bot.dbcache)
            if f"{inter.guild.id}{inter.author.id}" in self.bot.charcache:
                self.bot.charcache.pop(f"{inter.guild.id}{inter.author.id}")
            if settings.loggingchar:
                self.bot.dispatch("character_created", settings, inter.author, char)
            await inter.send(f"Registered {name} with the Adventurers Coalition.")
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
            await inter.send(
                "Heres your adventurer's ID...",
                embed=embed,
            )

    @commands.slash_command()
    @commands.cooldown(5, 30.0, type=commands.BucketType.user)
    async def rename(
        self, inter: disnake.ApplicationCommandInteraction, name: str, new_name: str
    ):
        """Change your character's name.
        Parameters
        ----------
        name: The name of your character.
        new_name: Your character's new name."""
        char: "Character" = await self.bot.get_character(
            str(inter.guild.id), str(inter.author.id), name
        )
        if char is None:
            await inter.send(f"{name} doesn't exist!", ephemeral=True)
        else:
            char.name = new_name
            await char.commit(self.bot.dbcache)
            if f"{inter.guild.id}{inter.author.id}" in self.bot.charcache:
                self.bot.charcache.pop(f"{inter.guild.id}{inter.author.id}")
            uprefs = await self.bot.get_user_prefs(str(inter.author.id))
            if uprefs.activechar[str(inter.guild.id)].name == name:
                uprefs.activechar[str(inter.guild.id)].name = new_name
            uprefs.characters[str(inter.guild.id)][new_name] = uprefs.characters[
                str(inter.guild.id)
            ].pop(name)
            uprefs.commit(self.bot.dbcache)
            await inter.send(f"{name}'s name changed to {new_name}")
            settings = await self.bot.get_server_settings(
                str(inter.guild.id), validate=False
            )
            if settings.loggingchar:
                self.bot.dispatch(
                    "character_renamed", settings, inter.author, name, new_name
                )

    @commands.slash_command()
    @commands.cooldown(5, 30.0, type=commands.BucketType.user)
    async def xp(
        self,
        inter: disnake.ApplicationCommandInteraction,
        name: str,
        xp: float,
        dm: disnake.Member,
    ):
        """Adds an entry to your character's xp log.
        Parameters
        ----------
        name: The name of your character
        xp: The amount of xp to add (or remove)
        dm: The DM that awarded you xp, if fixing/adjusting your xp, select @Labyrinthian"""
        char: "Character" = await self.bot.get_character(
            str(inter.guild.id), str(inter.author.id), name
        )
        settings: ServerSettings = await self.bot.get_server_settings(
            str(inter.guild.id), validate=False
        )
        if char is None:
            await inter.send(f"{name} doesn't exist!", ephemeral=True)
            return
        if xp == 0:
            await inter.send("You can't add zero badges!", ephemeral=True)
            return
        if not settings.is_dm(dm) and not dm == self.bot.user:
            await inter.send(f"<@{dm.id}> isn't a DM!", ephemeral=True)
            return
        timestamp = int(time())
        newlog = XPLogEntry(
            charref=char.id,
            user=char.user,
            guild=char.guild,
            name=char.name,
            prevxp=char.xp,
            xpadded=xp,
            dm=dm.id,
            timestamp=timestamp,
        )
        result: "InsertOneResult" = await newlog.commit(self.bot.dbcache)
        char.xp += xp
        char.lastlog.id = result.inserted_id
        char.lastlog.time = timestamp
        await char.commit(self.bot.dbcache)
        p = inflect.engine()
        outputstr = (
            f"{name} lost {p.plural(settings.xplabel)} {char.xp-xp}({xp}) <@{dm.id}>"
            if xp < 0
            else f"{name} was awarded {p.plural(settings.xplabel)} {char.xp-xp}(+{xp}) <@{dm.id}>"
        )
        sendstr = f"<@{newlog.user}> at <t:{timestamp}:f>\n{outputstr}"
        await inter.send(
            embed=disnake.Embed(
                title=f"{settings.xplabel} log updated",
                description=sendstr,
            )
        )
        if settings.loggingxp:
            self.bot.dispatch("xp_changed", settings, inter.author, sendstr, xp < 0)

    @commands.slash_command()
    @commands.cooldown(3, 30.0, type=commands.BucketType.user)
    async def log(self, inter: disnake.ApplicationCommandInteraction):
        """Displays your character's badgelog data.
        Parameters
        ----------
        name: The name of your character."""
        charlist = await self.bot.charcache.find_distinct_chardat(
            str(inter.guild.id), str(inter.author.id)
        )
        if not charlist:
            await inter.send("You don't have any characters to view!", ephemeral=True)
            return
        uprefs = await self.bot.get_user_prefs(str(inter.author.id), validate=False)
        settings = await self.bot.get_server_settings(
            str(inter.guild.id), validate=False
        )
        ui = LogMenu.new(self.bot, settings, uprefs, inter.author, inter.guild)
        await ui.send_to(inter)

    @commands.slash_command()
    @commands.cooldown(5, 30.0, type=commands.BucketType.user)
    async def swap(self, inter: disnake.ApplicationCommandInteraction, name: str):
        """Used to swap your active character.
        Parameters
        ----------
        name: The name of your character."""
        charlist = await self.bot.charcache.find_distinct_chardat(
            str(inter.guild.id), str(inter.author.id)
        )
        if name not in charlist:
            await inter.send(f"{name} doesn't exist!", ephemeral=True)
            return
        uprefs: "UserPreferences" = await self.bot.get_user_prefs(str(inter.author.id))
        if name == uprefs.activechar[str(inter.guild.id)].name:
            await inter.send("That character is already active!", ephemeral=True)
            return
        newchar = ActiveCharacter(
            name=name, id=uprefs.characters[str(inter.guild.id)][name]
        )
        settings = await self.bot.get_server_settings(
            str(inter.guild.id), validate=False
        )
        if settings.loggingchar is not None:
            self.bot.dispatch(
                "changed_character",
                settings,
                inter.author,
                newchar,
                uprefs.activechar[str(inter.guild.id)],
            )
        uprefs.activechar[str(inter.guild.id)] = newchar
        await uprefs.commit(self.bot.dbcache)
        await inter.send(f"Active character changed to {name}")

    # ==== command families ====
    @commands.slash_command(name="class", description="Set your characters classes.")
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
        classset = deepcopy(char.multiclasses)
        classlist = await self._get_classlist(str(inter.guild.id))
        classlist = [x for x in classlist if x not in char.multiclasses]
        if multiclass_name not in classlist:
            await inter.send(
                f"{multiclass_name} is not a valid class in this server, try using "
                f"the autocompletion to select a class.",
                ephemeral=True,
            )
            return
        if len(char.multiclasses) >= 5:
            await inter.send(f"You can't have more than 5 classes!", ephemeral=True)
            return
        if multiclass_level < 1:
            await inter.send("You can't have a level less than zero.", ephemeral=True)
            return
        char.multiclasses[multiclass_name] = multiclass_level
        await char.commit(self.bot.dbcache)
        await inter.send(f"{name} multiclassed into {multiclass_name}!")
        settings: "ServerSettings" = await self.bot.get_server_settings(
            str(inter.guild.id), validate=False
        )
        if settings.loggingchar:
            self.bot.dispatch(
                "class_added", settings, inter.user, char, classset, multiclass_name
            )

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
        classset = deepcopy(char.multiclasses)
        if multiclass_name not in char.multiclasses:
            await inter.send(
                f"{name} isn't {'an' if multiclass_name == 'Artificer' else 'a'} {multiclass_name}",
                ephemeral=True,
            )
            return
        char.multiclasses.pop(multiclass_name)
        await char.commit(self.bot.dbcache)
        await inter.send(f"{name} is no longer a {multiclass_name}")
        settings: "ServerSettings" = await self.bot.get_server_settings(
            str(inter.guild.id), validate=False
        )
        if settings.loggingchar:
            self.bot.dispatch(
                "class_removed", settings, inter.user, char, classset, multiclass_name
            )

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
        classlvl = deepcopy(char.multiclasses[multiclass_name])
        char.multiclasses[multiclass_name] = multiclass_level
        await char.commit(self.bot.dbcache)
        await inter.send(
            f"{name}'s {multiclass_name} level changed to {multiclass_level}"
        )
        settings: "ServerSettings" = await self.bot.get_server_settings(
            str(inter.guild.id), validate=False
        )
        if settings.loggingchar:
            self.bot.dispatch(
                "class_updated", settings, inter.user, char, multiclass_name, classlvl
            )

    # ==== autocompletion ====
    @create.autocomplete("starting_class")
    async def autocomp_all_classes(
        self, inter: disnake.ApplicationCommandInteraction, user_input: str
    ):
        classlist = await self._get_classlist(str(inter.guild.id))
        if classlist:
            return [x[0] for x in rapidfuzz.process.extract(user_input, classlist)]

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
        if charlist:
            return [x[0] for x in rapidfuzz.process.extract(user_input, charlist)]

    @swap.autocomplete("name")
    async def autocomp_inactive_names(
        self, inter: disnake.ApplicationCommandInteraction, user_input: str
    ):
        charlist: List[str] = await self.bot.charcache.find_distinct_chardat(
            str(inter.guild.id), str(inter.author.id)
        )
        if charlist:
            uprefs: "UserPreferences" = await self.bot.get_user_prefs(
                str(inter.author.id)
            )
            return [
                x[0]
                for x in rapidfuzz.process.extract(user_input, charlist)
                if x[0] != uprefs.activechar[str(inter.guild.id)].name
            ]

    @add.autocomplete("multiclass_name")
    async def autocomp_remaining_classes(
        self, inter: disnake.ApplicationCommandInteraction, user_input: str
    ):
        name = inter.filled_options["name"]
        char: "Character" = await self.bot.get_character(
            str(inter.guild.id), str(inter.author.id), name, validate=False
        )
        if char:
            classlist = await self._get_classlist(str(inter.guild.id))
            classlist = [x for x in classlist if x not in char.multiclasses]
            return [x[0] for x in rapidfuzz.process.extract(user_input, classlist)]

    @remove.autocomplete("multiclass_name")
    @update.autocomplete("multiclass_name")
    async def autocomp_existing_classes(
        self, inter: disnake.ApplicationCommandInteraction, user_input: str
    ):
        name = inter.filled_options["name"]
        char: "Character" = await self.bot.get_character(
            str(inter.guild.id), str(inter.author.id), name, validate=False
        )
        if char:
            return [
                x[0]
                for x in rapidfuzz.process.extract(
                    user_input, list(char.multiclasses.keys()), limit=8
                )
            ]

    # ==== helpers ====
    async def _get_classlist(self, guild_id):
        settings: "ServerSettings" = await self.bot.get_server_settings(
            str(guild_id), validate=False
        )
        return settings.classlist


def setup(bot: "Labyrinthian"):
    bot.add_cog(CharacterLog(bot))
