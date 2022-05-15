import disnake
import logging
import os
from disnake.ext import commands
from disnake import Embed
from enum import Enum
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)

intents = disnake.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(
	command_prefix="'",
	test_guilds=[915674780303249449, 951225215801757716],
	sync_commands_debug=True,
	intents=intents,
	owner_ids=['200632489998417929', '136583737931595777']
)

@bot.slash_command(description="Responds with 'World'")
async def hello(inter):
	await inter.response.send_message("World")

@bot.event
async def on_ready():
	print(f'We have logged in as {bot.user}')

#validClasses = ['artificer', 'barbarian', 'bard', 'druid', 'cleric', 'ranger', 'fighter', 'paladin', 'blood hunter', 'sorcerer', 'warlock', 'wizard']
nl = '\n'

#async def validclasses_autocomp(inter, string: str) -> List[str]:
#	return [chClass for chClass in validClasses if string.casefold() in chClass.casefold()]

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


@bot.slash_command(description="Logs your characters badges.")
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
		title=f"Creating {'username here'}'s badge log!",
		description=f"""{sheetlink=}\n{starting_class=}\n{starting_class_level=}{nl+'firstmulticlass='+str(firstmulticlass) if firstmulticlass!=None else ''}{nl+'firstmulticlass_level='+str(firstmulticlass_level) if firstmulticlass_level!=0 else ''}{nl+'secondmulticlass='+str(secondmulticlass) if secondmulticlass!=None else ''}{nl+'secondmulticlass_level='+str(secondmulticlass_level) if secondmulticlass_level!=0 else ''}{nl+'thirdmulticlass='+str(thirdmulticlass) if thirdmulticlass!=None else ''}{nl+'thirdmulticlass_level='+str(thirdmulticlass_level) if thirdmulticlass_level!=0 else ''}{nl+'fourthmulticlass='+str(fourthmulticlass) if fourthmulticlass!=None else ''}{nl+'fourthmulticlass_level='+str(fourthmulticlass_level) if fourthmulticlass_level!=0 else ''}"""
	))

#@create.autocomplete("starting_class")
#async def validclasses_autocomp(inter: disnake.CommandInteraction, string: str):
#	string = string.casefold()
#	return [chClass for chClass in validClasses if string in chClass.casefold()]

#@create.autocomplete("firstmulticlass")
#async def validclasses_autocomp(inter: disnake.CommandInteraction, string: str):
#	string = string.casefold()
#	return [chClass for chClass in validClasses if string in chClass.casefold()]

#@create.autocomplete("secondmulticlass")
#async def validclasses_autocomp(inter: disnake.CommandInteraction, string: str):
#	string = string.casefold()
#	return [chClass for chClass in validClasses if string in chClass.casefold()]

#@create.autocomplete("thirdmulticlass")
#async def validclasses_autocomp(inter: disnake.CommandInteraction, string: str):
#	string = string.casefold()
#	return [chClass for chClass in validClasses if string in chClass.casefold()]

#@create.autocomplete("fourthmulticlass")
#async def validclasses_autocomp(inter: disnake.CommandInteraction, string: str):
#	string = string.casefold()
#	return [chClass for chClass in validClasses if string in chClass.casefold()]

load_dotenv()

bot.run(os.getenv('TOKEN'))