import disnake
from disnake.ext import commands
from disnake import Embed
import datetime
from data.URLchecker import urlCheck
import json
from utilities.errors import noValidTemplate
from json import JSONDecodeError
from utilities.txtformatting import mkTable
from badgelogging.badgelogbrowser import Browser

class Badges(commands.Cog):
	def __init__(self, bot):
		self.bot = bot
		self.dmlist = []

	nl = '\n'
	validClass = commands.option_enum(['Artificer', 'Barbarian', 'Bard', 'Blood Hunter', 'Cleric', 'Druid', 'Fighter', 'Monk', 'Paladin', 'Ranger', 'Rogue', 'Sorcerer', 'Warlock', 'Wizard'])

	@commands.slash_command(default_member_permissions=disnake.Permissions(administrator=True))
	async def dmroles(self, inter: disnake.ApplicationCommandInteraction):
		pass

	@dmroles.sub_command(name="add")
	async def addrole(self, inter: disnake.ApplicationCommandInteraction, role: disnake.Role, role2: disnake.Role=None, role3: disnake.Role=None, role4: disnake.Role=None):
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
	async def removerole(self, inter: disnake.ApplicationCommandInteraction, role: disnake.Role, role2: disnake.Role=None, role3: disnake.Role=None, role4: disnake.Role=None):
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

	@commands.Cog.listener()
	async def on_ready(self):
		for x in self.bot.guilds:
			srvconf = await self.bot.sdb['srvconf'].find_one({"guild": str(x.id)})
			if not isinstance(srvconf, type(None)):
				dmroles=[]
				dmusers = []
				for z in srvconf['dmroles']:
					dmroles.append(x.get_role(z))
				for y in x.members:
					if any(item in y.roles for item in dmroles):
						dmusers.append(y.id)
				if len(dmusers)>0:
					try:
						for y in dmusers:
							if y not in srvconf['DMs']:
								srvconf['DMs'].append(y)
					except KeyError:
						srvconf['DMs'] = []
						for y in dmusers:
							srvconf['DMs'].append(y)
					await self.bot.sdb['srvconf'].replace_one({"guild": str(x.id)}, srvconf, True)

	@commands.Cog.listener()
	async def on_member_update(self, before, after):
		srvconf = await self.bot.sdb['srvconf'].find_one({"guild": str(after.guild.id)})
		if not isinstance(srvconf, type(None)):
			if any(item.id in srvconf['dmroles'] for item in after.roles) and not any(item.id in srvconf['dmroles'] for item in before.roles):
				await self.bot.sdb['srvconf'].update_one({"guild": str(after.guild.id)}, {'$addToSet': {'DMs': after.id}}, True)
			if any(item.id in srvconf['dmroles'] for item in before.roles) and not any(item.id in srvconf['dmroles'] for item in after.roles):
				await self.bot.sdb['srvconf'].update_one({"guild": str(after.guild.id)}, {'$pull': {'DMs': after.id}}, True)

	@commands.slash_command(default_member_permissions=8)
	async def badgetemplate(self, inter: disnake.ApplicationCommandInteraction, templatedict: str):
		try:
			templatedict = json.loads(templatedict)
		except JSONDecodeError:
			return await inter.response.send_message("Error: Template not a valid JSON")
		for itr,x in enumerate(templatedict.keys()):
			if itr > 20:
				return await inter.response.send_message("Error: Template has too many entries")
			elif x != str(itr):
				return await inter.response.send_message("Error: Template keys are not a range of 1 through 20")
		if all([isinstance(x, (int, float)) for x in templatedict.values()]):
			templatedict.update({"setting": "bltemp"})
			await self.bot.sdb[f"srvconf_{inter.guild.id}"].replace_one({"setting": "bltemp"}, templatedict, True)
		else:
			return await inter.response.send_message("Error: Template value is not of type integer or float")

	@commands.slash_command(description="Log your characters badges.")
	async def badges(self, inter: disnake.ApplicationCommandInteraction):
		pass

	#creates a master badge log entry, used for tracking data about a character and generating badge log entries
	@badges.sub_command()
	async def create(self, inter: disnake.ApplicationCommandInteraction, sheetlink: str, charname: str, startingclass: validClass, startingclasslevel: int):
		"""Creates a badge log for your character
		Parameters
		----------
		sheetlink: Valid character sheet URL.
		charname: The name of your character.
		startingclass: Your character's starter class.
		startingclasslevel: The level of your character's starter class."""
		if urlCheck(sheetlink):
			character = await self.bot.sdb[f"BLCharList_{inter.guild.id}"].find_one({"user": str(inter.author.id), "character": charname})
			if character != None:
				await inter.response.send_message(f"{charname}'s badge log already exists!")
			else:
				await self.bot.sdb[f"BLCharList_{inter.guild.id}"].insert_one({"user": str(inter.author.id), "sheet": sheetlink, "character": charname, "charlvl": startingclasslevel, "classes": {startingclass: startingclasslevel}, "currentbadges": 0, "expectedlvl": 1, "lastlog": None, "lastlogtime": datetime.datetime.now()})
				await inter.response.send_message(f"Registered {charname}'s badge log with the Adventurers Coalition.")
		else:
			await inter.response.send_message("Sheet type does not match accepted formats, or is not a valid URL.")

	@badges.sub_command()
	async def rename(self, inter, charname: str, newname: str):
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
		return [name for name in charlist if user_input.casefold() in name]

	#master of the class sub commands
	@badges.sub_command_group(description="Set your characters classes in their badge log.")
	async def classes(self, inter):
		pass

	#adds a multiclass entry to a characters badgelog master
	@classes.sub_command()
	async def add(self, inter, charname: str, multiclassname: validClass, multiclasslevel: int):
		"""Adds a multiclass to your character's badge log.
		Parameters
		----------
		charname: The name of your character.
		multiclassname: The class your multiclassing into.
		multiclasslevel: The level of your new multiclass."""
		character = await self.bot.sdb[f"BLCharList_{inter.guild.id}"].find_one({"user": str(inter.author.id), "character": charname})
		if character == None:
			await inter.response.send_message(f"{charname} doesn't exist!")
		elif len(character['classes']) < 5:
			character['classes'][multiclassname] = multiclasslevel
			character['charlvl'] = sum(character['classes'].values())
			await self.bot.sdb[f"BLCharList_{inter.guild.id}"].replace_one({"user": str(inter.author.id), "character": charname}, character)
			await inter.response.send_message(f"{charname} multiclassed into {multiclassname}!")

	@add.autocomplete("charname")
	async def autocomp_charnames(self, inter: disnake.ApplicationCommandInteraction, user_input: str):
		charlist = await self.bot.sdb[f"BLCharList_{inter.guild.id}"].distinct("character", {"user": str(inter.author.id)})
		return [name for name in charlist if user_input.casefold() in name]

	#removes a multiclass entry from a characters badgelog master
	@classes.sub_command()
	async def remove(self, inter, charname: str, multiclassname: validClass):
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
		return [name for name in charlist if user_input.casefold() in name]

	#updatese a multiclass entry in a characters badgelog master
	@classes.sub_command()
	async def update(self, inter, charname: str, multiclassname: validClass, multiclasslevel: int):
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
			character['classes'][multiclassname] = multiclasslevel
			character['charlvl'] = sum(character['classes'].values())
			await self.bot.sdb[f"BLCharList_{inter.guild.id}"].replace_one({"user": str(inter.author.id), "character": charname}, character)
			await inter.response.send_message(f"{charname} is no longer a {multiclassname}")

	@update.autocomplete("charname")
	async def autocomp_charnames(self, inter: disnake.ApplicationCommandInteraction, user_input: str):
		charlist = await self.bot.sdb[f"BLCharList_{inter.guild.id}"].distinct("character", {"user": str(inter.author.id)})
		return [name for name in charlist if user_input.casefold() in name]

	#returns a list of the invoking users character badge logs
	@badges.sub_command(description="Displays a list of all the characters that you've created badge logs for.")
	async def charlist(self, inter):
		charlist =await self.bot.sdb[f"BLCharList_{inter.guild.id}"].find({"user": str(inter.author.id)}).to_list(None)
		#charlist = list(charlist)
		output = disnake.Embed(
			title=f"{inter.author.display_name}'s characters:",
			description=mkTable.fromListofDicts(charlist, ["character", "charlvl", "expectedlvl", "currentbadges"], {"charlvl": 3, "expectedlvl": 4, "currentbadges": 3}, 43, '${character}|${charlvl}${expectedlvl}|${currentbadges}', '`', {"expectedlvl": '(${expectedlvl})'})
		)
		await inter.response.send_message(embed=output)

	#creates a new log entry in a characters badge log
	#inputs:
	#	character name
	#	badgee input
	#	awarding dm
	@badges.sub_command()
	async def log(self, inter, charname: str, badgeinput: float, awardingdm: disnake.Member):
		pass
	
	# @log.autocomplete("charname")
	# async def autocomp_charnames(self, inter: disnake.ApplicationCommandInteraction, user_input: str):
	# 	charlist = await self.bot.sdb[f"BLCharList_{inter.guild.id}"].distinct("character", {"user": str(inter.author.id)})
	# 	return [name for name in charlist if user_input.casefold() in name]

	@log.autocomplete('awardingdm')
	async def autocomp_dmnames(self, inter: disnake.ApplicationCommandInteraction, user_input: str):
		dbvar = await self.bot.sdb['dmusers'].find_one({"guild": str(inter.guild.id)})
		dbvar = dbvar['DMs']
		dmlist = []
		for x in dbvar:
			dmlist.append(f"@{inter.guild.get_member(x).name}{inter.guild.get_member(x).discriminator}")
		return [user for user in dmlist if user_input in user]

	#@badges.sub_command()
	#async def charinfo(self, inter, charname: str):
	#	"""Displays your character's badgelog data.
	#	Parameters
	#	----------
	#	charname: The name of your character."""
	#	charslist = await self.bot.sdb[f"BLCharList_{inter.guild.id}"].find({"user": str(inter.author.id)}).to_list(None)
	#	badgelog = await self.bot.sdb[f"BadgeLog_{inter.guild.id}"].find({"user": str(inter.author.id)}).to_list(None)
	#	initchar = list(filter(lambda item: item['character'] == f"{charname}", charslist))
	#	initlog = list(filter(lambda item: item['character'] == f"{charname}", badgelog))
	#	embed = [
	#		disnake.Embed(
	#			title="",
	#			description="",)]
	#	await inter.response.send_message(embed=embed, view=Browser(inter, charslist=charslist, badgelog=badgelog, owner=inter.author, guild=inter.guild, charname=charname))


	#@charinfo.autocomplete("charname")
	#async def autocomp_charnames(self, inter: disnake.ApplicationCommandInteraction, user_input: str):
	#	charlist = await self.bot.sdb[f"BLCharList_{inter.guild.id}"].distinct("character", {"user": str(inter.author.id)})
	#	return [name for name in charlist if user_input.casefold() in name]

	##returns a log of the selected characters most recent log entries
	#@badges.sub_command()
	#async def history(self, inter, charname: str):
	#	pass
	
	#@history.autocomplete("charname")
	#async def autocomp_charnames(self, inter: disnake.ApplicationCommandInteraction, user_input: str):
	#	charlist = await self.bot.sdb[f"BLCharList_{inter.guild.id}"].distinct("character", {"user": str(inter.author.id)})
	#	return [name for name in charlist if user_input.casefold() in name]

def setup(bot):
	bot.add_cog(Badges(bot))