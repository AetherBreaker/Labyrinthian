import asyncio
from cProfile import label
from datetime import datetime, timezone
from random import randint
import traceback
from turtle import title
from typing import TYPE_CHECKING, Any, Dict, List, TypeVar
import disnake
from disnake.ext import commands
from pyparsing import Optional
from administrative.serverconfigs import Configs
from auction.handlers import AuctionHandler, ListingHandler
from auction.auction_listing import ListingActionRow
from auction.auction_constructor import ConstSender, send_const

_LabyrinthianT = TypeVar("_LabyrinthianT", bound=disnake.Client)
if TYPE_CHECKING:
    from bot import Labyrinthian

    _LabyrinthianT = Labyrinthian



class AuctionHouse(commands.Cog):
    def __init__(self, bot: _LabyrinthianT):
        self.bot = bot

    @commands.Cog.listener("on_button_click")
    async def listing_listener(self, inter: disnake.MessageInteraction):
        buttonids = ["auction_bid_lowest", "auction_bid_custom", "auction_buy_now"]
        if not inter.component.custom_id in buttonids:
            return

        listingfinished = False
        srvconf: Dict[str, Any] = await self.bot.sdb['srvconf'].find_one({"guild": str(inter.guild.id)})
        charlist: List[str] = await self.bot.sdb[f'BLCharList_{inter.guild.id}'].distinct("character", {"user": str(inter.author.id)})
        listingdat: Dict[str, Any] = await self.bot.sdb['auction_listings'].find_one({"listingid": str(inter.message.id)})
        if len(charlist) < 1:
            await inter.send(f"<@{inter.author.id}> You don't have any characters!\nYou must have a registered character to use the auction house!", ephemeral=True)
            return
        elif listingdat is None:
            await inter.send(f"<@{inter.author.id}> This listing seems to be broken, or its data has been lost, please contact the listing owner or a staff member for assistance.", ephemeral=True)
            return
        # elif str(inter.author.id) == listingdat['userid']:
        #     await inter.send(f"<@{inter.author.id}> You can't bid on your own auctions!", ephemeral=True)
        elif listingdat['enddate'].replace(tzinfo=timezone.utc)<disnake.utils.utcnow():
            await inter.message.delete()
            await inter.send(f"<@{inter.author.id}> Sorry, that auction has ended!", ephemeral=True)
            listingfinished = True

        if not listingfinished:
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
                        max_length=9
                    )
                )
            rand = randint(111111, 9999999)
            if inter.component.custom_id == buttonids[0]:
                modtitle = "Minimum Bid: Select Character"
            elif inter.component.custom_id == buttonids[1]:
                modtitle = "Custom Bid: Select Character"
            elif inter.component.custom_id == buttonids[2]:
                modtitle = "Buy Now: Select Character"
            await inter.response.send_modal(
                title=modtitle,
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

            listingdat['topbidchar'] = modal_inter.data['components'][0]['components'][0]['values'][0]
            listingdat['topbidder'] = str(inter.author.id)
            LHandler = ListingHandler(
                bot=self.bot,
                button_inter=inter,
                modal_inter=modal_inter,
                auctiondata=listingdat,
                config=srvconf,
                charname=modal_inter.data['components'][0]['components'][0]['values'][0]
            )
            if inter.component.custom_id == buttonids[0]: # Handle bid lowest interactions
                listingfinished = await LHandler.bid_lowest()
            elif inter.component.custom_id == buttonids[1]: # Handle custom bid interactions
                listingfinished = await LHandler.bid_custom()
                if LHandler.error:
                    return
            elif inter.component.custom_id == buttonids[2]: # Handle buy now interactions
                listingfinished = await LHandler.buy_now()
            if not listingfinished:
                AHandler = AuctionHandler(bot=self.bot, auctiondata=LHandler.auctiondata, config=srvconf)
                await AHandler.update_listing_tracker(embed=LHandler.embed)
                await AHandler.log_bid()
                await modal_inter.response.edit_message(embed=LHandler.embed, components=ListingActionRow(listingdat))
                self.bot.sdb['auction_listings'].replace_one({"listingid": str(inter.message.id)}, LHandler.auctiondata)
                return

        AHandler = AuctionHandler(bot=self.bot, auctiondata=LHandler.auctiondata, config=srvconf)
        if listingfinished:
            await AHandler.log_finished(bought=LHandler.bought)
            await modal_inter.response.edit_message("Auction Finished")
            await inter.message.delete()
            await self.bot.sdb['auction_listings'].delete_one({"listingid": str(inter.message.id)})
        else:
            return

    # @commands.Cog.listener("on_button_click")
    # async def cancel_listing(self, inter: disnake.MessageInteraction):
    #     if not inter.component.custom_id == "auction_cancel_listing":
    #         return
    #     listingdat: Dict[str, Any] = await self.bot.sdb['auction_listings'].find_one({"usertrack": [str(inter.author.id), str(inter.message.id)]})
    #     srvconf: Dict[str, Any] = await self.bot.sdb['srvconf'].find_one({"guild": listingdat["guildid"]})
    #     if str(inter.author.id) != listingdat['userid']:
    #         return
    #     component = disnake.ui.TextInput(
    #         style=disnake.TextInputStyle.single_line,
    #         label="Are you sure you want to cancel this listing?",
    #         placeholder='Type "CONFIRM" to confirm cancellation.',
    #         custom_id="confirm_cancel_field",
    #         max_length=7
    #     )
    #     rand=randint(111111,99999999)
    #     await inter.response.send_modal(
    #         title="Confirm Cancel",
    #         custom_id=f"{rand}confirm_cancel_modal",
    #         components=component
    #     )
    #     try:
    #         modal_inter: disnake.ModalInteraction = await self.bot.wait_for(
    #             "modal_submit",
    #             check=lambda i: i.custom_id == f"{rand}confirm_cancel_modal" and i.author.id == inter.author.id,
    #             timeout=60,
    #         )
    #     except asyncio.TimeoutError:
    #         return
    #     confirm = modal_inter.text_values['confirm_cancel_field']
    #     if confirm.casefold() != 'confirm':
    #         modal_inter.send("Confirmation failed, abortting cancel...", ephemeral=True)
    #         return
    #     modal_inter.send("Confirmed, cancelling item listing.")
    #     embed = listingdat['embed']
    #     embed['fields'] = embed['fields'][:3]
    #     embed = (
    #         disnake.Embed.from_dict(embed)
    #         .add_field(name="")
    #     )

        listowner: disnake.User = self.bot.get_user(int(listingdat['usertrack'][0]))
        trackermsg: disnake.Message = await listowner.fetch_message(int(listingdat['usertrack'][1]))
        


    @commands.slash_command()
    async def testconsend(self, inter: disnake.ApplicationCommandInteraction):
        await send_const(inter)

def setup(bot):
    bot.add_cog(AuctionHouse(bot))