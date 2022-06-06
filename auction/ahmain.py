import asyncio
from datetime import datetime
from random import randint
import traceback
from typing import TYPE_CHECKING, Any, Dict, List, TypeVar
import disnake
from disnake.ext import commands
from administrative.serverconfigs import Configs
from auction.ahlisting import ListingActionRow
from auction.listingconstructor import ConstSender, send_const

_LabyrinthianT = TypeVar("_LabyrinthianT", bound=disnake.Client)
if TYPE_CHECKING:
    from bot import Labyrinthian

    _LabyrinthianT = Labyrinthian

errorfrmt = "ansi\n\u001b[1;40;31m"

class AuctionHouse(commands.Cog):
    def __init__(self, bot: _LabyrinthianT):
        self.bot = bot

    @commands.Cog.listener("on_button_click")
    async def auction_listener(self, inter: disnake.MessageInteraction):
        buttonids = ["auction_bid_lowest", "auction_bid_custom", "auction_buy_now"]
        if not inter.component.custom_id in buttonids:
            return

        srvconf: Dict[str, Any] = await self.bot.sdb['srvconf'].find_one({"guild": str(inter.guild.id)})
        charlist: List[str] = await self.bot.sdb[f'BLCharList_{inter.guild.id}'].distinct("character", {"user": str(inter.author.id)})
        listingdat: Dict[str, Any] = await self.bot.sdb['auction_listings'].find_one({"listingid": str(inter.message.id)})
        if len(charlist) < 1:
            await inter.send(f"<@{inter.author.id}> You don't have any characters!\nYou must have a registered character to use the auction house!", ephemeral=True)
            return
        elif listingdat is None:
            await inter.send(f"<@{inter.author.id}> This listing seems to be broken, or its data has been lost, please contact the listing owner or a staff member for assistance.", ephemeral=True)
            return

        if listingdat['enddate']<disnake.utils.utcnow().replace(tzinfo=None):
            await inter.message.delete()
            await inter.send(f"<@{inter.author.id}> Sorry, that auction has ended!", ephemeral=True)
            listingdat["embed"]['fields'][:3]
            if listingdat["topbidder"] != 'None':
                winner: disnake.User = await self.bot.get_user(listingdat['topbidder'])
            embed = (
                disnake.Embed.from_dict(listingdat['embed'])
                .add_field(name=f"Winner: {listingdat['topbidchar']}({winner.name}{winner.discriminator})" if listingdat['topbidder'] != 'None' else 'No bids')
                .add_field(name="Ended", value='\u200B')
            ) 
            auctionendstr = f"Item was bought by {listingdat['topbidchar']} (<@{winner.id}>)" if listingdat["topbidder"] != 'None' else "Item didn't sell"
            auctionlogchan: disnake.abc.GuildChannel = await self.bot.get_channel(srvconf['ahinternal'])
            await auctionlogchan.send(auctionendstr, embed=embed)
            listowner: disnake.User = self.bot.get_user(listingdat['usertrack'][0])
            trackermsg: disnake.Message = await listowner.fetch_message(listingdat['usertrack'][1])
            await trackermsg.edit(auctionendstr, embed=embed)
            await self.bot.sdb['auction_listings'].delete_one({"listingid": str(inter.message.id)})
            return

        modal_components = [
            disnake.ui.Select(
                custom_id="auction_inter_charname",
                placeholder="Select Character",
                options=[disnake.SelectOption(label=x) for x in charlist]
            )
        ]
        if "bid_custom" in inter.component.custom_id:
            modal_components.append(
                disnake.ui.TextInput(
                    custom_id="auction_bid_amount",
                    label="Bid Amount",
                    placeholder="Must outbid by atleast 50gp",
                    value=f"{listingdat['highestbid']+50}",
                    style=disnake.TextInputStyle.single_line,
                    max_length=20
                )
            )
        rand = randint(111111, 9999999)
        await inter.response.send_modal(
            title="Select Character" if "bid_custom" not in inter.component.custom_id else "Custom Bid",
            components=modal_components,
            custom_id=f"{rand}auction_char_modal"
        )

        try:
            modal_inter: disnake.ModalInteraction = await self.bot.wait_for(
                "modal_submit",
                check=lambda i: i.custom_id == f"{rand}auction_char_modal" and i.author.id == inter.author.id,
                timeout=180,
            )
        except asyncio.TimeoutError:
            await inter.send(f"<@{inter.author.id}> It seems your form timed out, if you see this message, it is most likely because you took too long to fill out the form.\n\nPlease try again.\nError Traceback:\n```ansi\n\u001b[1;40;32m{traceback.format_exc()}```", ephemeral=True)
            return

        listingfinished = False
        embed = disnake.Embed.from_dict(listingdat['embed'])
        charname = modal_inter.data['components'][0]['components'][0]['values'][0]
        listingdat['topbidchar'] = charname
        listingdat['topbidder'] = str(inter.author.id)
        if inter.component.custom_id == buttonids[0]:
            listingdat["highestbid"] += 50
            embed.set_field_at(
                3,
                name=f"Top Bidder: {charname} (@{inter.author.name}{inter.author.discriminator})",
                value=f"Highest Bid: {listingdat['highestbid']} gp"
            )
            listingdat["embed"] = embed.to_dict()
            if listingdat['buynow'] != None:
                if listingdat["highestbid"] >= listingdat["buynow"]:
                    listingfinished = True
        elif inter.component.custom_id == buttonids[1]:
            try:
                bidamount = int(modal_inter.data['components'][1]['components'][0]['value'])
            except (ValueError, TypeError):
                await inter.send(f"<@{inter.author.id}> It seems your starting bid couldn't be converted to a whole number, heres the error traceback:\n```{errorfrmt}{traceback.format_exc()}```", ephemeral=True)
                return

            if bidamount < listingdat['highestbid']:
                await inter.send(f"<@{inter.author.id}> That bid is too low, you must outbid the previous bid by atleast {srvconf['outbidthreshold']} gold pieces of more.", ephemeral=True)
                return

            listingdat['highestbid'] = bidamount
            embed.set_field_at(
                3,
                name=f"Top Bidder: {charname} (@{inter.author.name}{inter.author.discriminator})",
                value=f"Highest Bid: {listingdat['highestbid']} gp"
            )
            listingdat['embed'] = embed.to_dict()

        if listingfinished:
            await inter.
            listingdat["embed"]['fields'][:3]
            if listingdat["topbidder"] != 'None':
                winner: disnake.User = await self.bot.get_user(listingdat['topbidder'])
            embed = (
                disnake.Embed.from_dict(listingdat['embed'])
                .add_field(name=f"Winner: {listingdat['topbidchar']}({winner.name}{winner.discriminator})" if listingdat['topbidder'] != 'None' else 'No bids')
                .add_field(name="Ended", value='\u200B')
            ) 
            auctionendstr = f"Item was bought by {listingdat['topbidchar']} (<@{winner.id}>)" if listingdat["topbidder"] != 'None' else "Item didn't sell"
            auctionlogchan: disnake.abc.GuildChannel = await self.bot.get_channel(srvconf['ahinternal'])
            await auctionlogchan.send(auctionendstr, embed=embed)
            listowner: disnake.User = self.bot.get_user(listingdat['usertrack'][0])
            trackermsg: disnake.Message = await listowner.fetch_message(listingdat['usertrack'][1])
            await trackermsg.edit(auctionendstr, embed=embed)
            await self.bot.sdb['auction_listings'].delete_one({"listingid": str(inter.message.id)})
        else:
            listowner: disnake.User = self.bot.get_user(listingdat['usertrack'][0])
            trackermsg: disnake.Message = await listowner.fetch_message(listingdat['usertrack'][1])
            await trackermsg.edit(embed=embed)
            await modal_inter.response.edit_message(embed=embed, components=ListingActionRow(listingdat))
            self.bot.sdb['auction_listings'].replace_one({"listingid": str(inter.message.id)}, listingdat)

    async def update_user_auctiontracker(self, listingdat: Dict[str, Any]):
        pass

    async def auction_won_msg(self, listingdat: Dict[str, Any]):
        pass

    async def auction_log_bid(self, listingdat: Dict[str, Any]):
        pass

    async def auction_log_bought(self):
        pass

    async def auction_done_log(self):
        pass

    async def auction_cancelled_log(self):
        pass

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