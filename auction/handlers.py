from dataclasses import dataclass
from datetime import timezone, tzinfo
import traceback
from typing import TYPE_CHECKING, Any, List, NoReturn, Optional, TypeVar, Dict
import disnake
from disnake.ext import commands

from utilities.functions import timedeltaplus

_LabyrinthianT = TypeVar("_LabyrinthianT", bound=disnake.Client)
if TYPE_CHECKING:
    from bot import Labyrinthian

    _LabyrinthianT = Labyrinthian

errorfrmt = "ansi\n\u001b[1;40;31m"

@dataclass
class AuctionHandler:
    bot: _LabyrinthianT
    auctiondata: Dict[str, Any]
    config: Dict[str, Any]

    async def log_bid(self) -> None:
        topbidder = self.bot.get_user(int(self.auctiondata['topbidder']))
        logemb = disnake.Embed(
            title="New Bid!",
            description=f"{self.auctiondata['topbidchar']}({topbidder.name}{topbidder.discriminator}) is now the top bidder on {self.auctiondata['character']}'s {self.auctiondata['embed']['title']}",
        )
        if 'ahinternal' in self.config:
            auctionlogchan: disnake.abc.GuildChannel = self.bot.get_channel(int(self.config['ahinternal']))
            await auctionlogchan.send(embed=logemb)


    async def log_finished(self, bought: bool) -> None:
        self.auctiondata["embed"]['fields'] = self.auctiondata["embed"]['fields'][:3]
        winner = None
        if self.auctiondata["topbidder"] != 'None':
            winner: disnake.User = self.bot.get_user(int(self.auctiondata['topbidder']))
            if bought:
                self.auctiondata['highestbid'] = self.auctiondata['buynow']
                winnerfield = f"Bought by: {self.auctiondata['topbidchar']}({winner.name}{winner.discriminator})"
            else:
                winnerfield = f"Winner: {self.auctiondata['topbidchar']}({winner.name}{winner.discriminator})"
            soldfor = f"Sold for: {self.auctiondata['highestbid']} gp"
        else:
            winnerfield = "Auction ended with no bids"
            soldfor = f"Starting bid of {self.auctiondata['startingbid']} gp refunded"
        if bought:
            ended = disnake.utils.utcnow()
        else:
            ended = self.auctiondata['enddate'].replace(tzinfo=timezone.utc)
        embed = (
            disnake.Embed.from_dict(self.auctiondata['embed'])
            .add_field(
                name=winnerfield,
                value=soldfor
            )
            .add_field(name="Ended", value=disnake.utils.format_dt(ended, "R"))
        )
        self.auctiondata['embed'] = disnake.Embed.to_dict(embed)
        auctionendstr = f"Winning user: <@{winner.id}>" if self.auctiondata["topbidder"] != 'None' else ""
        await self.update_listing_tracker(embed, auctionendstr)
        if 'ahinternal' in self.config:
            auctionlogchan: disnake.abc.GuildChannel = self.bot.get_channel(int(self.config['ahinternal']))
            await auctionlogchan.send(auctionendstr, embed=embed)

    async def update_listing_tracker(self, embed: disnake.Embed, contentstr: str='None'):
        listowner: disnake.User = self.bot.get_user(int(self.auctiondata['usertrack'][0]))
        trackermsg: disnake.Message = await listowner.fetch_message(int(self.auctiondata['usertrack'][1]))
        if contentstr == 'None':
            await trackermsg.edit(embed=embed)
        else:
            await trackermsg.edit(contentstr, embed=embed)

class ListingHandler:
    def __init__(
        self,
        bot: _LabyrinthianT,
        button_inter: disnake.MessageInteraction,
        modal_inter: disnake.ModalInteraction,
        auctiondata: Dict[str, Any],
        config: Dict[str, Any],
        charname: str,
    ):
        """Handle button interactions from auction listings."""
        self.bot = bot
        self.button_inter = button_inter
        self.modal_inter = modal_inter
        self.auctiondata = auctiondata
        self.config = config
        self.charname = charname
        self.embed = disnake.Embed.from_dict(auctiondata['embed'])
        self.bought = False
        self.error = False
    

    async def bid_lowest(self) -> bool:
        self.auctiondata["highestbid"] += 50
        self.embed.set_field_at(
            3,
            name=f"Top Bidder: {self.charname} (@{self.button_inter.author.name}{self.button_inter.author.discriminator})",
            value=f"Highest Bid: {self.auctiondata['highestbid']} gp"
        )
        self.auctiondata["embed"] = self.embed.to_dict()
        if self.auctiondata['buynow'] != None:
            if self.auctiondata["highestbid"] >= self.auctiondata["buynow"]:
                self.bought = True
                return True
            else:
                return False

    async def bid_custom(self) -> bool:
        # Check if custom bid amount can be cast as an integer
        # return if not with error msg.
        try:
            bidamount = int(self.modal_inter.data['components'][1]['components'][0]['value'])
        except (ValueError, TypeError):
            self.error = True
            await self.button_inter.send(f"<@{self.button_inter.author.id}> It seems your starting bid couldn't be converted to a whole number, heres the error traceback:\n```{errorfrmt}{traceback.format_exc()}```", ephemeral=True)
            return False

        # Check if bid amount is atleast x higher than previous highest bid.
        # x is set from server config.
        if bidamount < self.auctiondata['highestbid']:
            self.error = True
            await self.button_inter.send(f"<@{self.button_inter.author.id}> That bid is too low, you must outbid the previous bid by atleast {self.config['outbidthreshold']} gold pieces of more.", ephemeral=True)
            return False

        # Update listing data and modify listing embed
        self.auctiondata['highestbid'] = bidamount
        self.embed.set_field_at(
            3,
            name=f"Top Bidder: {self.charname} (@{self.button_inter.author.name}{self.button_inter.author.discriminator})",
            value=f"Highest Bid: {self.auctiondata['highestbid']} gp"
        )
        self.auctiondata['embed'] = self.embed.to_dict()

        # Check if new bid exceeds the buy now price
        if self.auctiondata['buynow'] != None:
            if self.auctiondata["highestbid"] >= self.auctiondata["buynow"]:
                self.bought = True
                return True
            else:
                return False

    async def buy_now(self):
        pass