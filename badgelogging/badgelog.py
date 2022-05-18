import disnake
from disnake.ext import commands
from disnake import Embed
#from enum import Enum
import datetime
from ..data.URLchecker import urlCheck

class Badges(commands.Cog):
	def __init__(self, bot):
		self.bot = bot

	nl = '\n'
	validClass = commands.option_enum(['Artificer', 'Barbarian', 'Bard', 'Blood Hunter', 'Cleric', 'Druid', 'Fighter', 'Monk', 'Paladin', 'Ranger', 'Rogue', 'Sorcerer', 'Warlock', 'Wizard'])

	@commands.slash_command(description="Log your characters badges.")
	async def badges(self, inter: disnake.ApplicationCommandInteraction):
		pass

	#creates a master badge log entry, used for tracking data about a character and generating badge log entries
	@badges.sub_command()
	async def create(
		self,
		inter: disnake.ApplicationCommandInteraction,
		sheetlink: str,
		charactername: str,
		starting_class: validClass,
		starting_class_level: int,
	):
		"""Creates a badge log for your character
		Parameters
		----------
		sheetlink: Valid character sheet URL.
		charactername: The name of your character.
		starting_class: Your character's starter class.
		starting_clas_level: The level of your character's starter class.
		"""
		existingEntries = await self.bot.mdb['BLCharList'].find({"user": inter.author.id, "character": charactername.casefold()}).to_list(None)
		if len(existingEntries) > 0:
			await inter.response.send_message(f"'{charactername}' already exists!")
		else:
			await self.bot.mdb['BLCharList'].insert_one({"user": inter.author.id, "sheet": sheetlink, "character": charactername.casefold(), "charlvl": starting_class_level, "classes": {"class1": starting_class}, "currentbadges": 0, "lastlog": None, "lastlogtime": datetime.datetime.now()})
			await inter.response.send_message(f"Registered {charactername}'s badge log with the Adventurers Coalition.")
		#await inter.response.send_message(embed = Embed(
		#	title=f"Creating {inter.author.name}'s badge log!",
		#	description=f"""<@{inter.author.id}>\n{sheetlink=}\n{starting_class=}\n{starting_class_level=}"""
		#))

	@badges.sub_command()
	async def edit(self, inter, charname: str, badgeinput: float):
		pass

	#master of the multiclass sub commands
	@badges.sub_command_group()
	async def multiclass(self, inter):
		pass

	#adds a multiclass entry to a characters badgelog master
	@multiclass.sub_command()
	async def add(self, inter, multiclassname: validClass, multiclasslevel: int):
		pass

	#removes a multiclass entry from a characters badgelog master
	@multiclass.sub_command()
	async def remove(self, inter, multiclassname: validClass):
		pass

	#updatese a multiclass entry in a characters badgelog master
	@multiclass.sub_command()
	async def update(self, inter, multiclassname: validClass, multiclasslevel: int):
		pass

	#returns a list of the invoking users character badge logs
	@badges.sub_command()
	async def charlist(self, inter):
		pass

	#creates a new log entry in a characters badge log
	#inputs:
	#	character name
	#	badgee input
	#	awarding dm
	@badges.sub_command()
	async def log(self, inter, charname: str, badgeinput: float, awardingdm: str):
		pass
	
	#returns a log of the selected characters most recent log entries
	@badges.sub_command()
	async def history(self, inter, charname: str):
		pass

def setup(bot):
	bot.add_cog(Badges(bot))