import disnake
from disnake.ext import commands
import logging

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
    # In the list above you can specify the IDs of your test guilds.
    # Why is this kwarg called test_guilds? This is because you're not meant to use
    # local registration in production, since you may exceed the rate limits.
)

@bot.slash_command(description="Responds with 'World'")
async def hello(inter):
    await inter.response.send_message("World")

@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')

bot.run('OTc0NTQyMTY0MjQ1NzU3OTcy.GdAvmG.DeKmgiiivoTUcrITPEUjm_E18wsKAJuQLx7sBs')
