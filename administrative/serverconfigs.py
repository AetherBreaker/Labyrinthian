import disnake
from disnake.ext import commands

class Configs(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.slash_command()
    async def staff(self, inter: disnake.ApplicationCommandInteraction):
        pass

    @commands.slash_command()
    async def admin(self, inter: disnake.ApplicationCommandInteraction):
        pass

def setup(bot):
    bot.add_cog(Configs(bot))