import disnake
from disnake.ext import commands
from disnake import Embed
import datetime
from data.URLchecker import urlCheck
import json
from errors.errors import noValidTemplate
from json import JSONDecodeError

class Badges(commands.Cog):
	def __init__(self, bot):
		self.bot = bot

	nl = '\n'
	validClass = commands.option_enum(['Artificer', 'Barbarian', 'Bard', 'Blood Hunter', 'Cleric', 'Druid', 'Fighter', 'Monk', 'Paladin', 'Ranger', 'Rogue', 'Sorcerer', 'Warlock', 'Wizard'])

	@commands.slash_command(description="Log your characters badges.")
	async def badges(self, inter: disnake.ApplicationCommandInteraction):
		pass

	#@badges.sub_command(checks=commands.has_permissions(administrator=True))
	#async def template(self, inter, templatedict: str):
	#	try:
	#		templatedict = json.loads(templatedict)
	#	except JSONDecodeError:
	#		return await inter.response.send_message("Error: Template not a valid JSON")
	#	for itr,x in enumerate(templatedict.keys()):
	#		if itr > 20:
	#			return await inter.response.send_message("Error: Template has too many entries")
	#		elif x != str(itr):
	#			return await inter.response.send_message("Error: Template keys are not a range of 1 through 20")
	#	if all([isinstance(x, (int, float)) for x in templatedict.values()]):
	#		templatedict.update({"setting": "bltemp"})
	#		self.bot.sdb[f"srvconf_{inter.guild.id}"].replace_one({"setting": "bltemp"}, templatedict, True)
	#	else:
	#		return await inter.response.send_message("Error: Template value is not of type integer or float")
			


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
				await self.bot.sdb[f"BLCharList_{inter.guild.id}"].insert_one({"user": str(inter.author.id), "sheet": sheetlink, "character": charname, "charlvl": startingclasslevel, "classes": {startingclass: startingclasslevel}, "currentbadges": 0, "expectedlevel": 1, "lastlog": None, "lastlogtime": datetime.datetime.now()})
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
		charlist = self.bot.sdb[f"BLCharList_{inter.guild.id}"].distinct("character", {"user": str(inter.author.id)})
		pass


	@badges.sub_command()
	async def charinfo(self, inter, charname: str):
		"""Displays your character's badgelog data.
		Parameters
		----------
		charname: The name of your character."""
		pass


	@charinfo.autocomplete("charname")
	async def autocomp_charnames(self, inter: disnake.ApplicationCommandInteraction, user_input: str):
		charlist = await self.bot.sdb[f"BLCharList_{inter.guild.id}"].distinct("character", {"user": str(inter.author.id)})
		return [name for name in charlist if user_input.casefold() in name]

	##creates a new log entry in a characters badge log
	##inputs:
	##	character name
	##	badgee input
	##	awarding dm
	#@badges.sub_command()
	#async def log(self, inter, charname: str, badgeinput: float, awardingdm: str):
	#	pass
	
	#@log.autocomplete("charname")
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