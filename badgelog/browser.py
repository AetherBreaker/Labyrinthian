import disnake
from disnake.ext import commands


async def create_browser(*args, **kwargs):
    bro = Browser(*args, **kwargs)
    await bro.before_send()
    return bro

class Browser(disnake.ui.View):
    def __init__(self, inter:disnake.ApplicationCommandInteraction, bot: commands.Bot, owner: disnake.User, guild: disnake.Guild):
        super().__init__(timeout=180)
        self.inter = inter
        self.bot = bot
        self.owner = owner
        self.guild = guild

    async def before_send(self):
        userlist = await self.bot.sdb[f"BLCharList_{self.guild.id}"].distinct()
        pass

