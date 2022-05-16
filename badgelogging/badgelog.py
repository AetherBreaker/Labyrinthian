import disnake
from disnake.ext import commands
from disnake import Embed
from enum import Enum

nl = '\n'

class validClass(str, Enum):
	Artificer = 'Artificer'
	Barbarian = 'Barbarian'
	Bard = 'Bard'
	BloodHunter = 'Blood Hunter'
	Cleric = 'Cleric'
	Druid = 'Druid'
	Fighter = 'Fighter'
	Monk = 'Monk'
	Paladin = 'Paladin'
	Ranger = 'Ranger'
	Rogue = 'Rogue'
	Sorcerer = 'Sorcerer'
	Warlock = 'Warlock'
	Wizard = 'Wizard'

@commands.slash_command(description="Logs your characters badges.")
async def badgelog(inter: disnake.ApplicationCommandInteraction):
	pass

@badgelog.sub_command()
async def create(
	inter: disnake.ApplicationCommandInteraction,
	sheetlink: str,
	starting_class: validClass,
	starting_class_level: int,
	firstmulticlass: validClass = None,
	firstmulticlass_level: int = 0,
	secondmulticlass: validClass = None,
	secondmulticlass_level: int = 0,
	thirdmulticlass: validClass = None,
	thirdmulticlass_level: int = 0,
	fourthmulticlass: validClass = None,
	fourthmulticlass_level: int = 0
):
	"""Creates a badge log for your character
	Parameters
	----------
	sheetlink: Valid character sheet URL.
	starting_class: Your very first class level.
	"""
	await inter.response.send_message(embed = Embed(
		title=f"Creating {inter.author.name}'s badge log!",
		description=f"""<@{inter.author.id}>\n{sheetlink=}\n{starting_class=}\n{starting_class_level=}{nl+'firstmulticlass='+str(firstmulticlass) if firstmulticlass!=None else ''}{nl+'firstmulticlass_level='+str(firstmulticlass_level) if firstmulticlass_level!=0 else ''}{nl+'secondmulticlass='+str(secondmulticlass) if secondmulticlass!=None else ''}{nl+'secondmulticlass_level='+str(secondmulticlass_level) if secondmulticlass_level!=0 else ''}{nl+'thirdmulticlass='+str(thirdmulticlass) if thirdmulticlass!=None else ''}{nl+'thirdmulticlass_level='+str(thirdmulticlass_level) if thirdmulticlass_level!=0 else ''}{nl+'fourthmulticlass='+str(fourthmulticlass) if fourthmulticlass!=None else ''}{nl+'fourthmulticlass_level='+str(fourthmulticlass_level) if fourthmulticlass_level!=0 else ''}"""
	))

def setup(bot):
	bot.add_slash_command(badgelog)