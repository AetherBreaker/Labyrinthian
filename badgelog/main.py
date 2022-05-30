import time
from json import JSONDecodeError, loads
from string import Template

import disnake
from data.URLchecker import urlCheck
from disnake.ext import commands

from administrative.serverconfigs import Configs
from utilities.txtformatting import mkTable

from badgelog.browser import create_CharSelect


class Badges(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.valid = ['Artificer', 'Barbarian', 'Bard', 'Blood Hunter', 'Cleric', 'Druid', 'Fighter', 'Monk', 'Paladin', 'Ranger', 'Rogue', 'Sorcerer', 'Warlock', 'Wizard']

    validClass = commands.option_enum(['Artificer', 'Barbarian', 'Bard', 'Blood Hunter', 'Cleric', 'Druid', 'Fighter', 'Monk', 'Paladin', 'Ranger', 'Rogue', 'Sorcerer', 'Warlock', 'Wizard'])

    @commands.slash_command()
    @commands.cooldown(4, 1200.0, type=commands.BucketType.user)
    async def create(self, inter: disnake.ApplicationCommandInteraction, sheetlink: str, charname: str, startingclass: validClass, startingclasslevel: int = commands.Param(gt=0, le=20)):
        """Creates a badge log for your character
        Parameters
        ----------
        sheetlink: Valid character sheet URL.
        charname: The name of your character.
        startingclass: Your character's starter class.
        startingclasslevel: The level of your character's starter class."""
        srvconf = await self.bot.sdb[f'srvconf'].find_one({"guild": str(inter.guild.id)})
        validc = self.valid if srvconf is None else srvconf['classlist']
        if startingclass not in validc:
            await inter.response.send_message(f"{startingclass} is not a valid class, try using the autocompletion to select a class.")
        else:
            if urlCheck(sheetlink):
                character = await self.bot.sdb[f"BLCharList_{inter.guild.id}"].find_one({"user": str(inter.author.id), "character": charname})
                if character != None:
                    await inter.response.send_message(f"{charname}'s badge log already exists!")
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
                        "lastlogtime": time.time()
                    }
                    await self.bot.sdb[f"BLCharList_{inter.guild.id}"].insert_one(char)
                    await inter.response.send_message(f"Registered {charname}'s badge log with the Adventurers Coalition.")
                    Embed = {
                        "title": f"{charname}'s Adventurers ID'",
                        "description": f"Played by: <@{inter.author.id}>",
                        "color": disnake.Color.random().value,
                        "url": f"{char['sheet']}",
                        "fields": [
                            {
                                "name": "Badge Information:",
                                "value": f"Current Badges: {char['currentbadges']}\nExpected Level: {char['expectedlvl']}",
                                "inline": True
                            },
                            {
                                "name": "Class Levels:",
                                "value": '\n'.join([f'{x}: {y}' for x,y in char['classes'].items()]),
                                "inline": True
                            },
                            {
                                "name": f"Total Levels: {char['charlvl']}",
                                "value": "\u200B", 
                                "inline": True
                            }
                        ]
                    }
                    await inter.channel.send("Heres your adventurer's ID...", embed=disnake.Embed.from_dict(Embed))
            else:
                await inter.response.send_message("Sheet type does not match accepted formats, or is not a valid URL.")

    @create.autocomplete("startingclass")
    async def autocomp_class(self, inter: disnake.ApplicationCommandInteraction, user_input: str):
        srvconf = await self.bot.sdb[f'srvconf'].find_one({"guild": str(inter.guild.id)})
        validc = self.valid if srvconf is None else srvconf['classlist']
        return [name for name in validc if "".join(user_input.split()).casefold() in "".join(name.split()).casefold()]

    @commands.slash_command()
    @commands.cooldown(5, 30.0, type=commands.BucketType.user)
    async def rename(self, inter: disnake.ApplicationCommandInteraction, charname: str, newname: str):
        """Change your characters name!
        Parameters
        ----------
        charname: The name of your character.
        newname: Your characters new name."""
        character = await self.bot.sdb[f"BLCharList_{inter.guild.id}"].find_one({"user": str(inter.author.id), "character": charname})
        if character == None:
            await inter.response.send_message(f"{charname} doesn't exist!")
        else:
            character['character'] = newname
            await self.bot.sdb[f"BLCharList_{inter.guild.id}"].replace_one({"user":str(inter.author.id),"character":charname}, character)
            await inter.response.send_message(f"{charname}'s name changed to {newname}")

    @rename.autocomplete("charname")
    async def autocomp_charnames(self, inter: disnake.ApplicationCommandInteraction, user_input: str):
        charlist = await self.bot.sdb[f"BLCharList_{inter.guild.id}"].distinct("character", {"user": str(inter.author.id)})
        return [name for name in charlist if "".join(user_input.split()).casefold() in "".join(name.split()).casefold()]

    @commands.slash_command(description="Set your characters classes in their badge log.")
    async def classes(self, inter: disnake.ApplicationCommandInteraction):
        pass

    @classes.sub_command()
    @commands.cooldown(3, 30.0, type=commands.BucketType.user)
    async def add(self, inter: disnake.ApplicationCommandInteraction, charname: str, multiclassname: str, multiclasslevel: int = commands.Param(gt=0, le=20)):
        """Adds a multiclass to your character's badge log.
        Parameters
        ----------
        charname: The name of your character.
        multiclassname: The class your multiclassing into.
        multiclasslevel: The level of your new multiclass."""
        srvconf = await self.bot.sdb[f'srvconf'].find_one({"guild": str(inter.guild.id)})
        validc = self.valid if srvconf is None else srvconf['classlist']
        if multiclassname not in validc:
            await inter.response.send_message(f"{multiclassname} is not a valid class, try using the autocompletion to select a class.")
        else:
            character = await self.bot.sdb[f"BLCharList_{inter.guild.id}"].find_one({"user": str(inter.author.id), "character": charname})
            if character == None:
                await inter.response.send_message(f"{charname} doesn't exist!")
            elif len(character['classes']) < 5:
                if (sum(character['classes'].values())+multiclasslevel) > 20:
                    multiclasslevel -= (sum(character['classes'].values())+multiclasslevel)-20
                    if (sum(character['classes'].values())+multiclasslevel) > 20:
                        await inter.response.send_message(f"That level is too high")
                        return
                character['classes'][multiclassname] = multiclasslevel
                character['charlvl'] = sum(character['classes'].values())
                await self.bot.sdb[f"BLCharList_{inter.guild.id}"].replace_one({"user": str(inter.author.id), "character": charname}, character)
                await inter.response.send_message(f"{charname} multiclassed into {multiclassname}!")

    @add.autocomplete("charname")
    async def autocomp_charnames(self, inter: disnake.ApplicationCommandInteraction, user_input: str):
        charlist = await self.bot.sdb[f"BLCharList_{inter.guild.id}"].distinct("character", {"user": str(inter.author.id)})
        return [name for name in charlist if "".join(user_input.split()).casefold() in "".join(name.split()).casefold()]

    @add.autocomplete("multiclassname")
    async def autocomp_class(self, inter: disnake.ApplicationCommandInteraction, user_input: str):
        charname = inter.filled_options['charname']
        char = await self.bot.sdb[f"BLCharList_{inter.guild.id}"].find_one({"user": str(inter.author.id), "character": charname})
        srvconf = await self.bot.sdb[f'srvconf'].find_one({"guild": str(inter.guild.id)})
        validc = self.valid if srvconf is None else srvconf['classlist']
        validclasses = [x for x in validc if x not in char['classes']]
        return [name for name in validclasses if "".join(user_input.split()).casefold() in "".join(name.split()).casefold()]

    @classes.sub_command()
    @commands.cooldown(3, 30.0, type=commands.BucketType.user)
    async def remove(self, inter: disnake.ApplicationCommandInteraction, charname: str, multiclassname: str):
        """Removes a multiclass from your character's badge log.
        Parameters
        ----------
        charname: The name of your character.
        multiclassname: The class you wish to remove."""
        character = await self.bot.sdb[f"BLCharList_{inter.guild.id}"].find_one({"user": str(inter.author.id), "character": charname})
        if character == None:
            await inter.response.send_message(f"{charname} doesn't exist!")
        elif multiclassname not in character['classes'].keys():
            await inter.response.send_message(f"{charname} isn't {'an' if multiclassname == 'Artificer' else 'a'} {multiclassname}")
        else:
            character.pop(multiclassname)
            character['charlvl'] = sum(character['classes'].values())
            await self.bot.sdb[f"BLCharList_{inter.guild.id}"].replace_one({"user": str(inter.author.id), "character": charname}, character)
            await inter.response.send_message(f"{charname} is no longer a {multiclassname}")

    @remove.autocomplete("charname")
    async def autocomp_charnames(self, inter: disnake.ApplicationCommandInteraction, user_input: str):
        charlist = await self.bot.sdb[f"BLCharList_{inter.guild.id}"].distinct("character", {"user": str(inter.author.id)})
        return [name for name in charlist if "".join(user_input.split()).casefold() in "".join(name.split()).casefold()]

    @remove.autocomplete("multiclassname")
    async def autocomp_class(self, inter: disnake.ApplicationCommandInteraction, user_input: str):
        charname = inter.filled_options['charname']
        char = await self.bot.sdb[f"BLCharList_{inter.guild.id}"].find_one({"user": str(inter.author.id), "character": charname})
        validclasses = char['classes'].keys()
        return [name for name in validclasses if "".join(user_input.split()).casefold() in "".join(name.split()).casefold()]

    @classes.sub_command()
    @commands.cooldown(3, 30.0, type=commands.BucketType.user)
    async def update(self, inter: disnake.ApplicationCommandInteraction, charname: str, multiclassname: str, multiclasslevel: int = commands.Param(gt=0, le=20)):
        """Used to update the level of one of your characters multiclasses in their badge log.
        Parameters
        ----------
        charname: The name of your character.
        multiclassname: The class you're updating.
        multiclasslevel: The new level of your class."""
        character = await self.bot.sdb[f"BLCharList_{inter.guild.id}"].find_one({"user": str(inter.author.id), "character": charname})
        if character == None:
            await inter.response.send_message(f"{charname} doesn't exist!")
        elif multiclassname not in character['classes'].keys():
            await inter.response.send_message(f"{charname} isn't {'an' if multiclassname == 'Artificer' else 'a'} {multiclassname}")
        else:
            if (sum(character['classes'].values())+multiclasslevel) > 20:
                multiclasslevel -= (sum(character['classes'].values())+multiclasslevel)-20
                if (sum(character['classes'].values())+multiclasslevel) > 20:
                    await inter.response.send_message(f"That level is too high")
                    return
            character['classes'][multiclassname] = multiclasslevel
            character['charlvl'] = sum(character['classes'].values())
            await self.bot.sdb[f"BLCharList_{inter.guild.id}"].replace_one({"user": str(inter.author.id), "character": charname}, character)
            await inter.response.send_message(f"{charname} is no longer a {multiclassname}")

    @update.autocomplete("charname")
    async def autocomp_charnames(self, inter: disnake.ApplicationCommandInteraction, user_input: str):
        charlist = await self.bot.sdb[f"BLCharList_{inter.guild.id}"].distinct("character", {"user": str(inter.author.id)})
        return [name for name in charlist if "".join(user_input.split()).casefold() in "".join(name.split()).casefold()]

    @update.autocomplete("multiclassname")
    async def autocomp_class(self, inter: disnake.ApplicationCommandInteraction, user_input: str):
        charname = inter.filled_options['charname']
        char = await self.bot.sdb[f"BLCharList_{inter.guild.id}"].find_one({"user": str(inter.author.id), "character": charname})
        validclasses = char['classes'].keys()
        return [name for name in validclasses if "".join(user_input.split()).casefold() in "".join(name.split()).casefold()]

    # @commands.slash_command(name="character-list")
    # async def characterlist(self, inter: disnake.ApplicationCommandInteraction):
    #     """Displays a list of all the characters that you've created badge logs for."""
    #     charlist = await self.bot.sdb[f"BLCharList_{inter.guild.id}"].find({"user": str(inter.author.id)}).to_list(None)
    #     await inter.response.send_message(embed=disnake.Embed(
    #         title=f"{inter.author.display_name}'s characters:",
    #         description=mkTable.fromListofDicts(charlist, ["character", "charlvl", "expectedlvl", "currentbadges"], {"charlvl": 3, "expectedlvl": 4, "currentbadges": 3}, 43, '${character}|${charlvl}${expectedlvl}|${currentbadges}', '`', {"expectedlvl": '(${expectedlvl})'})
    #     ))

    @commands.slash_command(name="update-log")
    @commands.cooldown(3, 30.0, type=commands.BucketType.user)
    async def updatelog(self, inter: disnake.ApplicationCommandInteraction, charname: str, badgeinput: float, awardingdm: disnake.Member):
        """Adds an entry to your characters badge log
        Parameters
        ----------
        charname: The name of your character
        badgeinput: The amount of badges to add (or remove)
        awardingdm: The DM that awarded you badges, if fixing/adjusting your badges, select @Labyrinthian"""
        character = await self.bot.sdb[f"BLCharList_{inter.guild.id}"].find_one({"user": str(inter.author.id), "character": charname})
        srvconf = await self.bot.sdb['srvconf'].find_one({"guild": str(inter.guild.id)})
        if isinstance(character, type(None)):
            await inter.response.send_message(f"{charname} doesn't exist!")
        elif badgeinput == 0:
            await inter.response.send_message("You can't add zero badges!")
        elif not any([role.id in srvconf['dmroles'] for role in awardingdm.roles]) and not awardingdm == self.bot.user:
            await inter.response.send_message(f"<@{awardingdm.id}> isn't a DM!")
        else:
            timeStamp = int(time.time())
            newlog = {"charRefId": character['_id'], "user": str(inter.author.id), "character": charname, "previous badges": character['currentbadges'], "badges added": badgeinput, "awarding DM": awardingdm.id, "timestamp": timeStamp}
            objID = await self.bot.sdb[f"BadgeLogMaster_{inter.guild.id}"].insert_one(newlog)
            badgetemp = await self.bot.sdb['srvconf'].find_one({"guild": str(inter.guild.id)})
            badgetemp = badgetemp['badgetemplate']
            for x,y in badgetemp.items():
                if character['currentbadges']+badgeinput >= y:
                    character['expectedlvl'] = x
            character['lastlog'] = objID.inserted_id
            character['lastlogtimeStamp'] = timeStamp
            character['currentbadges'] += badgeinput
            await self.bot.sdb[f"BLCharList_{inter.guild.id}"].replace_one({"user": str(inter.author.id), "character": charname}, character, True)
            templstr = "$character lost badges $prev($input) to $awarding" if badgeinput < 0 else "$character was awarded badges $prev($input) by $awarding"
            mapping = {"character": f"{charname}", "prev": f"{character['currentbadges']-badgeinput}", "input": f"{'' if badgeinput < 0 else '+'}{badgeinput}", "awarding": f"<@{awardingdm.id}>"}
            await inter.response.send_message(embed=disnake.Embed(
                title=f"Badge log updated",
                description=f"{'' if character['user'] == newlog['user'] else '<@'+newlog['user']+'> at'} <t:{timeStamp}:f>\n{Template(templstr).substitute(**mapping)}"
            ))

    @updatelog.autocomplete("charname")
    async def autocomp_charnames(self, inter: disnake.ApplicationCommandInteraction, user_input: str):
        charlist = await self.bot.sdb[f"BLCharList_{inter.guild.id}"].distinct("character", {"user": str(inter.author.id)})
        return [name for name in charlist if "".join(user_input.split()).casefold() in "".join(name.split()).casefold()]

    @commands.slash_command(name="log-browser")
    @commands.cooldown(3, 30.0, type=commands.BucketType.user)
    async def logbrowser(self, inter: disnake.ApplicationCommandInteraction):
        """Displays your character's badgelog data.
        Parameters
        ----------
        charname: The name of your character."""
        await create_CharSelect(inter, self.bot, inter.author, inter.guild)

    @Configs.staff.sub_command()
    @commands.cooldown(3, 30.0, type=commands.BucketType.user)
    async def browser(self, inter: disnake.ApplicationCommandInteraction, user: disnake.Member):
        """Display the badge log data of a user's characters.
        Parameters
        ----------
        charname: The name of your character."""
        datachk = await self.bot.sdb[f'BLCharList_{inter.guild.id}'].find_one({"user": str(user.id)})
        if datachk is None:
            inter.response.send_message(f"{user.name} has no existing character data.", ephemeral=True)
        else:
            await create_CharSelect(inter, self.bot, inter.author, inter.guild, user, True)

    @Configs.staff.sub_command()
    @commands.cooldown(3, 30.0, type=commands.BucketType.user)
    async def sheet(self, inter: disnake.ApplicationCommandInteraction, user: disnake.Member, charname: str, sheetlink: str):
        """Update a users character sheet in their badge log.
        Parameters
        ----------
        user: The player of the character to be updated.
        charname: The name of the character to update.
        sheetlink: The new character sheet link."""
        userchk = await self.bot.sdb[f'BLCharList_{inter.guild.id}'].find_one({"user": str(user.id)})
        if userchk is None:
            await inter.response.send_message(f"{user.name} has no existing character data.", ephemeral=True)
        else:
            charchk = await self.bot.sdb[f'BLCharList_{inter.guild.id}'].find_one({"user": str(user.id), "character": charname})
            if charchk is None:
                await inter.response.send_message(f'{user.name} has no character named "{charname}".\nPlease double check the characters name using the admin log browser.\nThis field is case and punctuation sensitive.', ephemeral=True)
            else:
                if urlCheck(sheetlink):
                    charchk['sheet'] = sheetlink
                    await self.bot.sdb[f'BLCharList_{inter.guild.id}'].replace_one({"user": str(user.id), "character": charname}, charchk)
                    await inter.response.send_message(f"{user.name}'s character sheet URL has been updated.")
                else:
                    await inter.response.send_message("This URL is not an accepted character sheet type.\nPlease ensure that the link is from DnDBeyond, Dicecloud, or a valid GSheets character sheet.", ephemeral=True)

    @Configs.admin.sub_command_group()
    async def dmroles(self, inter: disnake.ApplicationCommandInteraction):
        pass

    @dmroles.sub_command(name="add")
    @commands.cooldown(3, 30.0, type=commands.BucketType.user)
    async def adddmrole(self, inter: disnake.ApplicationCommandInteraction, role: disnake.Role, role2: disnake.Role=None, role3: disnake.Role=None, role4: disnake.Role=None):
        """Choose roles to add to the list of DM roles."""
        await inter.response.defer()
        roleslist=[role]
        if role2!=None:
            roleslist.append(role2)
        if role3!=None:
            roleslist.append(role3)
        if role4!=None:
            roleslist.append(role4)
        role_ids = [r.id for r in roleslist]
        srvconf = await self.bot.sdb['srvconf'].find_one({"guild": str(inter.guild.id)})
        if srvconf == None:
            srvconf = {"guild": str(inter.guild.id)}
            srvconf['dmroles'] = []
        else:
            for x in role_ids:
                if x not in srvconf['dmroles']:
                    srvconf['dmroles'].append(x)
        await self.bot.sdb['srvconf'].replace_one({"guild": str(inter.guild.id)}, srvconf, True)
        await inter.send("The DM roles have been updated.", ephemeral=True)
    
    @dmroles.sub_command(name="remove")
    @commands.cooldown(3, 30.0, type=commands.BucketType.user)
    async def removedmrole(self, inter: disnake.ApplicationCommandInteraction, role: disnake.Role, role2: disnake.Role=None, role3: disnake.Role=None, role4: disnake.Role=None):
        """Choose roles to add to the list of DM roles."""
        await inter.response.defer()
        roleslist=[role]
        if role2!=None:
            roleslist.append(role2)
        if role3!=None:
            roleslist.append(role3)
        if role4!=None:
            roleslist.append(role4)
        role_ids = {r.id for r in roleslist}
        srvconf = await self.bot.sdb['srvconf'].find_one({"guild": str(inter.guild.id)})
        if srvconf == None:
            srvconf = {"guild": str(inter.guild.id)}
            srvconf['dmroles'] = []
        else:
            for x in role_ids:
                if x in srvconf['dmroles']:
                    srvconf['dmroles'].remove(x)
        await self.bot.sdb['srvconf'].replace_one({"guild": str(inter.guild.id)}, srvconf, True)
        await inter.send("The DM roles have been updated.", ephemeral=True)

    @Configs.admin.sub_command_group(name="classes")
    async def serverclasses(self, inter: disnake.ApplicationCommandInteraction):
        pass

    @serverclasses.sub_command(name="add")
    @commands.cooldown(3, 30.0, type=commands.BucketType.user)
    async def addclass(self, inter: disnake.ApplicationCommandInteraction, classname: str=commands.Param(name="class"), classname2: str=commands.Param(name="class", default=None), classname3: str=commands.Param(name="class", default=None), classname4: str=commands.Param(name="class", default=None)):
        """Add classes to the server class list."""
        await inter.response.defer()
        classlist=[classname]
        if classname2!=None:
            classlist.append(classname2)
        if classname3!=None:
            classlist.append(classname3)
        if classname4!=None:
            classlist.append(classname4)
        srvconf = await self.bot.sdb['srvconf'].find_one({"guild": str(inter.guild.id)})
        if srvconf == None:
            srvconf = {"guild": str(inter.guild.id)}
            srvconf['classlist'] = []
        else:
            for x in classlist:
                if x not in srvconf['classlist']:
                    srvconf['classlist'].append(x)
        await self.bot.sdb['srvconf'].replace_one({"guild": str(inter.guild.id)}, srvconf, True)
        await inter.send("The class list has been updated.", ephemeral=True)
    
    @serverclasses.sub_command(name="remove")
    @commands.cooldown(3, 30.0, type=commands.BucketType.user)
    async def removeclass(self, inter: disnake.ApplicationCommandInteraction, classname: str=commands.Param(name="class"), classname2: str=commands.Param(name="class", default=None), classname3: str=commands.Param(name="class", default=None), classname4: str=commands.Param(name="class", default=None)):
        """remove classes to the server class list."""
        await inter.response.defer()
        classlist=[classname]
        if classname2!=None:
            classlist.append(classname2)
        if classname3!=None:
            classlist.append(classname3)
        if classname4!=None:
            classlist.append(classname4)
        srvconf = await self.bot.sdb['srvconf'].find_one({"guild": str(inter.guild.id)})
        if srvconf == None:
            srvconf = {"guild": str(inter.guild.id)}
            srvconf['classlist'] = []
        else:
            for x in classlist:
                if x in srvconf['classlist']:
                    srvconf['classlist'].remove(x)
        await self.bot.sdb['srvconf'].replace_one({"guild": str(inter.guild.id)}, srvconf, True)
        await inter.send("The class list has been updated.", ephemeral=True)

    @Configs.admin.sub_command()
    @commands.cooldown(3, 30.0, type=commands.BucketType.user)
    async def badgetemplate(self, inter: disnake.ApplicationCommandInteraction, templatedict: str):
        try:
            bdgtemplate = loads(templatedict)
        except JSONDecodeError:
            return await inter.response.send_message("Error: Template not a valid JSON")
        for itr,x in enumerate(bdgtemplate.keys()):
            if itr > 20:
                return await inter.response.send_message("Error: Template has too many entries")
            elif x != str(itr+1):
                return await inter.response.send_message("Error: Template keys are not a range of 1 through 20")
        if all([isinstance(x, (int, float)) for x in bdgtemplate.values()]):
            srvconf = await self.bot.sdb['srvconf'].find_one({"guild": str(inter.guild.id)})
            srvconf['badgetemplate'] = bdgtemplate
            await self.bot.sdb['srvconf'].replace_one({"guild": str(inter.guild.id)}, srvconf, True)
            await inter.response.send_message("Badge template updated.")
        else:
            return await inter.response.send_message("Error: Template value is not of type integer or float")

def setup(bot):
    bot.add_cog(Badges(bot))
