import disnake
from disnake.ext import commands
from administrative.serverconfigs import Configs
from auction.listingconstructor import ConstSender, send_const

class AuctionHouse(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.slash_command()
    async def listing(self, inter: disnake.ApplicationCommandInteraction):
        pass

    @listing.sub_command()
    async def create(self, inter: disnake.ApplicationCommandInteraction):
        pass

    @commands.slash_command()
    async def testconsend(self, inter: disnake.ApplicationCommandInteraction):
        await send_const(inter)











def setup(bot):
    bot.add_cog(AuctionHouse(bot))