import disnake
from disnake.ext import commands
import logging
from disnake import Embed

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

validClasses = ['artificer', 'barbarian', 'bard', 'druid', 'cleric', 'ranger', 'fighter', 'paladin', 'blood hunter', 'sorcerer', 'warlock', 'wizard']
nl = '\n'

@bot.slash_command(description="Logs your characters badges.")
async def badgelog(inter):
	pass

@badgelog.sub_command(description="Creates a badge log for your character")
async def create(
	inter,
	sheetlink: str,
	starting_class: str,
	starting_class_level: int,
	multiclass1: str = None,
	multiclass1_level: int = 0,
	multiclass2: str = None,
	multiclass2_level: int = 0,
	multiclass3: str = None,
	multiclass3_level: int = 0,
	multiclass4: str = None,
	multiclass4_level: int = 0
):
	await inter.response.send_message(embed = Embed(
		title=f"Creating {'username here'}'s badge log!",
		description=f"""{sheetlink=}\n{starting_class=}\n{starting_class_level=}{nl+'multiclass1='+str(multiclass1) if multiclass1!=None else ''}{nl+'multiclass1_level='+str(multiclass1_level) if multiclass1_level!=0 else ''}{nl+'multiclass2='+str(multiclass2) if multiclass2!=None else ''}{nl+'multiclass2_level='+str(multiclass2_level) if multiclass2_level!=0 else ''}{nl+'multiclass3='+str(multiclass3) if multiclass3!=None else ''}{nl+'multiclass3_level='+str(multiclass3_level) if multiclass3_level!=0 else ''}{nl+'multiclass4='+str(multiclass4) if multiclass4!=None else ''}{nl+'multiclass4_level='+str(multiclass4_level) if multiclass4_level!=0 else ''}"""
	))

@create.autocomplete("starting_class")
async def validclasses_autocomp(inter: disnake.CommandInteraction, string: str):
	string = string.casefold()
	return [chClass for chClass in validClasses if string in chClass.casefold()]

@create.autocomplete("multiclass1")
async def validclasses_autocomp(inter: disnake.CommandInteraction, string: str):
	string = string.casefold()
	return [chClass for chClass in validClasses if string in chClass.casefold()]

@create.autocomplete("multiclass2")
async def validclasses_autocomp(inter: disnake.CommandInteraction, string: str):
	string = string.casefold()
	return [chClass for chClass in validClasses if string in chClass.casefold()]

@create.autocomplete("multiclass3")
async def validclasses_autocomp(inter: disnake.CommandInteraction, string: str):
	string = string.casefold()
	return [chClass for chClass in validClasses if string in chClass.casefold()]

@create.autocomplete("multiclass4")
async def validclasses_autocomp(inter: disnake.CommandInteraction, string: str):
	string = string.casefold()
	return [chClass for chClass in validClasses if string in chClass.casefold()]



bot.run('OTc0NTQyMTY0MjQ1NzU3OTcy.GdAvmG.DeKmgiiivoTUcrITPEUjm_E18wsKAJuQLx7sBs')