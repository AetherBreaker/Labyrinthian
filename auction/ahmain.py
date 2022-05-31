import disnake
from disnake.ext import commands
from administrative.serverconfigs import Configs
from auction.listingconstructor import ConstSender, send_const

class AuctionHouse(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @Configs.admin.sub_command_group()
    async def ah(self, inter: disnake.ApplicationCommandInteraction):
        pass

    @ah.sub_command()
    async def listingchan(self, inter: disnake.ApplicationCommandInteraction, channel: disnake.abc.GuildChannel):
        ahconf = await self.bot.sdb['srvconf'].find_one({"guild": str(inter.guild.id)})

    @ah.sub_command()
    async def setupchan(self, inter: disnake.ApplicationCommandInteraction, channel: disnake.abc.GuildChannel):
        pass

    @Configs.staff.sub_command_group(name="listing")
    async def stafflisting(self, inter: disnake.ApplicationCommandInteraction):
        pass

    @stafflisting.sub_command()
    async def remove(self, inter: disnake.ApplicationCommandInteraction, listing: str):
        pass



    @commands.slash_command()
    async def listing(self, inter: disnake.ApplicationCommandInteraction):
        pass

    @listing.sub_command()
    async def create(self, inter: disnake.ApplicationCommandInteraction):
        pass

    @commands.slash_command()
    async def testconsend(self, inter: disnake.ApplicationCommandInteraction):
        inter.response.defer()
        await send_const(inter)











def setup(bot):
    bot.add_cog(AuctionHouse(bot))