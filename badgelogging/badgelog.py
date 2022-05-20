import disnake
from disnake.ext import commands
from disnake import Embed
import datetime
from data.URLchecker import urlCheck
import json
from errors.errors import noValidTemplate

class Badges(commands.Cog):
	def __init__(self, bot):
		self.bot = bot

	nl = '\n'
	validClass = commands.option_enum(['Artificer', 'Barbarian', 'Bard', 'Blood Hunter', 'Cleric', 'Druid', 'Fighter', 'Monk', 'Paladin', 'Ranger', 'Rogue', 'Sorcerer', 'Warlock', 'Wizard'])

	@commands.slash_command(description="Log your characters badges.")
	async def badges(self, inter: disnake.ApplicationCommandInteraction):
		pass

	@badges.sub_command(checks=[commands.has_permissions(administrator=True)])
	async def template(self, inter, templatedict: str):
		jason = {}
		try:
			jason = json.load(templatedict)
		except noValidTemplate:
			return await inter.response.send_message("Error: Template not a valid JSON")
		for iter,x in enumerate(jason.keys()):
			if iter > 20:
				return await inter.response.send_message("Error: Template has too many entries")
			elif x != str(iter):
				return await inter.response.send_message("Error: Template keys are not a range of 1 through 20")
		if all([isinstance(x, (int, float)) for x in jason.values()]):
			jason.update({"setting": "bltemp"})
			self.bot.sdb[f"srvconf_{inter.guild.id}"].replace_one({"setting": "bltemp"}, jason, True)
		else:
			return await inter.response.send_message("Error: Template value is not of type integer or float")
			


	#creates a master badge log entry, used for tracking data about a character and generating badge log entries
	@badges.sub_command()
	async def create(self, inter: disnake.ApplicationCommandInteraction, sheetlink: str, charname: str, startingclass: validClass, startingclasslevel: int):
		"""Creates a badge log for your character
		Parameters
		----------
		sheetlink: Valid character sheet URL.
		charname: The name of your character.
		startingclass: Your character's starter class.
		startingclasslevel: The level of your character's starter class.
		"""
		if urlCheck(sheetlink):
			character = await self.bot.sdb[f"BLCharList_{inter.guild.id}"].find_one({"user": str(inter.author.id), "character": charname})
			if character != None:
				await inter.response.send_message(f"{charname}'s badge log already exists!")
			else:
				await self.bot.sdb[f"BLCharList_{inter.guild.id}"].insert_one({"user": str(inter.author.id), "sheet": sheetlink, "character": charname, "charlvl": startingclasslevel, "classes": {startingclass: startingclasslevel}, "currentbadges": 0, "expectedlevel": 1, "lastlog": None, "lastlogtime": datetime.datetime.now()})
				await inter.response.send_message(f"Registered {charname}'s badge log with the Adventurers Coalition.")
		else:
			inter.response.send_message("Sheet type does not match accepted formats, or is not a valid URL.")
		#await inter.response.send_message(embed = Embed(
		#	title=f"Creating {inter.author.name}'s badge log!",
		#	description=f"""<@{inter.author.id}>\n{sheetlink=}\n{startingclass=}\n{startingclass=}"""
		#))

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
		print(inter.author.id)
		charlist = await self.bot.sdb[f"BLCharList_{inter.guild.id}"].distinct("character", {"user": str(inter.author.id)})
		return [name for name in charlist if user_input.casefold() in name]

	#master of the class sub commands
	@badges.sub_command_group(description="Set your characters classes in their badge log.")
	async def classes(self, inter):
		pass

	#adds a multiclass entry to a characters badgelog master
	@classes.sub_command()
	async def add(self, inter, charname: str, multiclassname: validClass, multiclasslevel: int):
		"""Adds a multiclass to your characters badge log.
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
		print(inter.author.id)
		charlist = await self.bot.sdb[f"BLCharList_{inter.guild.id}"].distinct("character", {"user": str(inter.author.id)})
		return [name for name in charlist if user_input.casefold() in name]

	##removes a multiclass entry from a characters badgelog master
	#@classes.sub_command()
	#async def remove(self, inter, charname: str, multiclassname: validClass):
	#	pass

	#@remove.autocomplete("charname")
	#async def autocomp_charnames(self, inter: disnake.ApplicationCommandInteraction, user_input: str):
	#	print(inter.author.id)
	#	charlist = await self.bot.sdb[f"BLCharList_{inter.guild.id}"].distinct("character", {"user": str(inter.author.id)})
	#	return [name for name in charlist if user_input.casefold() in name]

	##updatese a multiclass entry in a characters badgelog master
	#@classes.sub_command()
	#async def update(self, inter, charname: str, multiclassname: validClass, multiclasslevel: int):
	#	pass

	#@update.autocomplete("charname")
	#async def autocomp_charnames(self, inter: disnake.ApplicationCommandInteraction, user_input: str):
	#	print(inter.author.id)
	#	charlist = await self.bot.sdb[f"BLCharList_{inter.guild.id}"].distinct("character", {"user": str(inter.author.id)})
	#	return [name for name in charlist if user_input.casefold() in name]

	##returns a list of the invoking users character badge logs
	#@badges.sub_command()
	#async def charlist(self, inter):
	#	pass

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
	#	print(inter.author.id)
	#	charlist = await self.bot.sdb[f"BLCharList_{inter.guild.id}"].distinct("character", {"user": str(inter.author.id)})
	#	return [name for name in charlist if user_input.casefold() in name]

	##returns a log of the selected characters most recent log entries
	#@badges.sub_command()
	#async def history(self, inter, charname: str):
	#	pass
	
	#@history.autocomplete("charname")
	#async def autocomp_charnames(self, inter: disnake.ApplicationCommandInteraction, user_input: str):
	#	print(inter.author.id)
	#	charlist = await self.bot.sdb[f"BLCharList_{inter.guild.id}"].distinct("character", {"user": str(inter.author.id)})
	#	return [name for name in charlist if user_input.casefold() in name]

def setup(bot):
	bot.add_cog(Badges(bot))