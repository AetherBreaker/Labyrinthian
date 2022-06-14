from json import JSONDecodeError, loads
import traceback
from typing import TYPE_CHECKING, TypeVar

import disnake
from cogs.badgelog.browser import create_CharSelect
from disnake.ext import commands
from utils import checks
from utils.ui.settingsui import SettingsNav

_LabyrinthianT = TypeVar("_LabyrinthianT", bound=disnake.Client)
if TYPE_CHECKING:
    from bot import Labyrinthian

    _LabyrinthianT = Labyrinthian

class Configs(commands.Cog):
    def __init__(self, bot: _LabyrinthianT) -> None:
        self.bot = bot
        self.valid = [
            'Artificer',
            'Barbarian',
            'Bard',
            'Blood Hunter',
            'Cleric',
            'Druid',
            'Fighter',
            'Monk',
            'Paladin',
            'Ranger',
            'Rogue',
            'Sorcerer',
            'Warlock',
            'Wizard'
        ]

    validClass = commands.option_enum(['Artificer', 'Barbarian', 'Bard', 'Blood Hunter', 'Cleric', 'Druid', 'Fighter', 'Monk', 'Paladin', 'Ranger', 'Rogue', 'Sorcerer', 'Warlock', 'Wizard'])

    @commands.slash_command()
    async def staff(self, inter: disnake.ApplicationCommandInteraction):
        pass

    @commands.slash_command()
    async def admin(self, inter: disnake.ApplicationCommandInteraction):
        pass

    @staff.sub_command()
    @commands.cooldown(3, 30.0, type=commands.BucketType.user)
    async def browser(self, inter: disnake.ApplicationCommandInteraction, user: disnake.Member):
        """Display the badge log data of a user's characters.
        Parameters
        ----------
        charname: The name of your character."""
        datachk = await self.bot.dbcache.find_one(f"BLCharList_{inter.guild.id}", {"user": str(user.id)})
        if datachk is None:
            inter.response.send_message(f"{user.name} has no existing character data.", ephemeral=True)
        else:
            await create_CharSelect(inter, self.bot, inter.author, inter.guild, user, True)

    @staff.sub_command()
    @commands.cooldown(3, 30.0, type=commands.BucketType.user)
    async def sheet(self, inter: disnake.ApplicationCommandInteraction, user: disnake.Member, charname: str, sheetlink: str):
        """Update a users character sheet in their badge log.
        Parameters
        ----------
        user: The player of the character to be updated.
        charname: The name of the character to update.
        sheetlink: The new character sheet link."""
        userchk = await self.bot.dbcache.find_one(f"BLCharList_{inter.guild.id}", {"user": str(user.id)})
        if userchk is None:
            await inter.response.send_message(f"{user.name} has no existing character data.", ephemeral=True)
        else:
            charchk = await self.bot.dbcache.find_one(f"BLCharList_{inter.guild.id}", {"user": str(user.id), "character": charname})
            if charchk is None:
                await inter.response.send_message(f'{user.name} has no character named "{charname}".\nPlease double check the characters name using the admin log browser.\nThis field is case and punctuation sensitive.', ephemeral=True)
            else:
                if checks.urlCheck(sheetlink):
                    charchk['sheet'] = sheetlink
                    await self.bot.sdb[f'BLCharList_{inter.guild.id}'].replace_one({"user": str(user.id), "character": charname}, charchk)
                    await inter.response.send_message(f"{user.name}'s character sheet URL has been updated.")
                else:
                    await inter.response.send_message("This URL is not an accepted character sheet type.\nPlease ensure that the link is from DnDBeyond, Dicecloud, or a valid GSheets character sheet.", ephemeral=True)

    @admin.sub_command_group()
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
        role_ids = [str(r.id) for r in roleslist]
        srvconf = await self.bot.dbcache.find_one('srvconf', {"guild": str(inter.guild.id)})
        if srvconf is None:
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
        srvconf = await self.bot.dbcache.find_one('srvconf', {"guild": str(inter.guild.id)})
        if srvconf is None:
            srvconf = {"guild": str(inter.guild.id)}
            srvconf['dmroles'] = []
        else:
            for x in role_ids:
                if x in srvconf['dmroles']:
                    srvconf['dmroles'].remove(x)
        await self.bot.sdb['srvconf'].replace_one({"guild": str(inter.guild.id)}, srvconf, True)
        await inter.send("The DM roles have been updated.", ephemeral=True)

    @admin.sub_command_group(name="classes")
    async def serverclasses(self, inter: disnake.ApplicationCommandInteraction):
        pass

    @serverclasses.sub_command(name="add")
    @commands.cooldown(3, 30.0, type=commands.BucketType.user)
    async def addclass(self, inter: disnake.ApplicationCommandInteraction, classname: str=commands.Param(name="class"), classname2: str=commands.Param(name="class2", default=None), classname3: str=commands.Param(name="class3", default=None), classname4: str=commands.Param(name="class4", default=None)):
        """Add classes to the server class list."""
        await inter.response.defer()
        classlist=[classname]
        if classname2!=None:
            classlist.append(classname2)
        if classname3!=None:
            classlist.append(classname3)
        if classname4!=None:
            classlist.append(classname4)
        srvconf = await self.bot.dbcache.find_one('srvconf', {"guild": str(inter.guild.id)})
        if srvconf is None:
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
    async def removeclass(self, inter: disnake.ApplicationCommandInteraction, classname: str=commands.Param(name="class"), classname2: str=commands.Param(name="class2", default=None), classname3: str=commands.Param(name="class3", default=None), classname4: str=commands.Param(name="class4", default=None)):
        """remove classes to the server class list."""
        await inter.response.defer()
        classlist=[classname]
        if classname2!=None:
            classlist.append(classname2)
        if classname3!=None:
            classlist.append(classname3)
        if classname4!=None:
            classlist.append(classname4)
        srvconf = await self.bot.dbcache.find_one('srvconf', {"guild": str(inter.guild.id)})
        if srvconf is None:
            srvconf = {"guild": str(inter.guild.id)}
            srvconf['classlist'] = []
        else:
            for x in classlist:
                if x in srvconf['classlist']:
                    srvconf['classlist'].remove(x)
        await self.bot.sdb['srvconf'].replace_one({"guild": str(inter.guild.id)}, srvconf, True)
        await inter.send("The class list has been updated.", ephemeral=True)

    @admin.sub_command()
    @commands.cooldown(3, 30.0, type=commands.BucketType.user)
    async def badgetemplate(self, inter: disnake.ApplicationCommandInteraction, templatedict: str):
        try:
            bdgtemplate = loads(templatedict)
        except JSONDecodeError:
            return await inter.response.send_message(f"Error: Template not a valid JSON\n Traceback:```py\n{traceback.print_exc()}```")
        for itr,x in enumerate(bdgtemplate.keys()):
            if itr > 20:
                return await inter.response.send_message("Error: Template has too many entries")
            elif x != str(itr+1):
                return await inter.response.send_message("Error: Template keys are not a range of 1 through 20")
        if all([isinstance(x, (int, float)) for x in bdgtemplate.values()]):
            srvconf = await self.bot.dbcache.find_one('srvconf', {"guild": str(inter.guild.id)})
            srvconf['badgetemplate'] = bdgtemplate
            await self.bot.sdb['srvconf'].replace_one({"guild": str(inter.guild.id)}, srvconf, True)
            await inter.response.send_message("Badge template updated.")
        else:
            return await inter.response.send_message("Error: Template value is not of type integer or float")


    @staff.sub_command()
    async def removelisting(self, inter: disnake.ApplicationCommandInteraction, listing: str):
        pass

    @admin.sub_command()
    async def serversettings(self, inter: disnake.ApplicationCommandInteraction):
        settings = await self.bot.get_server_settings(str(inter.guild.id))
        settings_ui = SettingsNav.new(self.bot, inter.author, settings, inter.guild)
        await settings_ui.send_to(inter, ephemeral=True)

def setup(bot):
    bot.add_cog(Configs(bot))
