import disnake
from disnake.ext import commands
from disnake import Embed
from enum import Enum
import datetime
from badgelogging.URLchecker import urlCheck

class Badges(commands.Cog):
	def __init__(self, bot):
		self.bot = bot

	nl = '\n'
	validClass = commands.option_enum(['Artificer', 'Barbarian', 'Bard', 'Blood Hunter', 'Cleric', 'Druid', 'Fighter', 'Monk', 'Paladin', 'Ranger', 'Rogue', 'Sorcerer', 'Warlock', 'Wizard'])

	@commands.slash_command(description="Log your characters badges.")
	async def badges(self, inter: disnake.ApplicationCommandInteraction):
		pass

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
		if urlCheck(sheetlink):
			existingEntries = await self.bot.mdb['BLCharList'].find({"user": inter.author.id, "character": charactername.casefold()}).to_list(None)
			if len(existingEntries) > 0:
				await inter.response.send_message(f"'{charactername}' already exists!")
			else:
				await self.bot.mdb['BLCharList'].insert_one({"user": inter.author.id, "character": charactername.casefold(), "charlvl": starting_class_level, "classes": {"class1": starting_class}, "currentbadges": 0, "lastlog": None, "lastlogtime": datetime.datetime.now()})
				await inter.response.send_message(f"Registered {charactername}'s badge log with the Adventurers Coalition.")
		#await inter.response.send_message(embed = Embed(
		#	title=f"Creating {inter.author.name}'s badge log!",
		#	description=f"""<@{inter.author.id}>\n{sheetlink=}\n{starting_class=}\n{starting_class_level=}"""
		#))

def setup(bot):
	bot.add_cog(Badges(bot))



#firstmulticlass: validClass = None,
#firstmulticlass_level: int = 0,
#secondmulticlass: validClass = None,
#secondmulticlass_level: int = 0,
#thirdmulticlass: validClass = None,
#thirdmulticlass_level: int = 0,
#fourthmulticlass: validClass = None,
#fourthmulticlass_level: int = 0
#{nl+'firstmulticlass='+str(firstmulticlass) if firstmulticlass!=None else ''}{nl+'firstmulticlass_level='+str(firstmulticlass_level) if firstmulticlass_level!=0 else ''}{nl+'secondmulticlass='+str(secondmulticlass) if secondmulticlass!=None else ''}{nl+'secondmulticlass_level='+str(secondmulticlass_level) if secondmulticlass_level!=0 else ''}{nl+'thirdmulticlass='+str(thirdmulticlass) if thirdmulticlass!=None else ''}{nl+'thirdmulticlass_level='+str(thirdmulticlass_level) if thirdmulticlass_level!=0 else ''}{nl+'fourthmulticlass='+str(fourthmulticlass) if fourthmulticlass!=None else ''}{nl+'fourthmulticlass_level='+str(fourthmulticlass_level) if fourthmulticlass_level!=0 else ''}