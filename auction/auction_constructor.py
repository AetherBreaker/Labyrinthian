import asyncio
from contextlib import suppress
from dataclasses import dataclass
from datetime import timedelta
from random import randint
import traceback
from typing import TYPE_CHECKING, List, NoReturn, Optional, TypeVar, Dict
import disnake
from pymongo.results import InsertOneResult
from auction.auction_listing import ListingActionRow

from utilities.functions import timedeltaplus

_LabyrinthianT = TypeVar("_LabyrinthianT", bound=disnake.Client)
if TYPE_CHECKING:
    from bot import Labyrinthian

    _LabyrinthianT = Labyrinthian

TOO_MANY_CHARACTERS_SENTINEL = "__special:too_many_characters"
instructionsfrmt = "ansi\n\u001b[1;40;32m"
errorfrmt = "ansi\n\u001b[1;40;31m"

async def send_const(inter: disnake.ApplicationCommandInteraction, *args, **kwargs) -> NoReturn:
    await ConstSender._init(inter, *args, **kwargs)

class ConstSender(disnake.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @classmethod
    async def _init(cls, inter: disnake.ApplicationCommandInteraction) -> NoReturn:
        inst = cls()
        emb = disnake.Embed(
            title="Auction House",
            description="To post an item to the auction house, click the button below and follow the instructions provided."
        )
        await inter.response.send_message(embed=emb, view=inst)
        response = await inter.original_message()
        await inter.bot.dbcache.update_one('srvconf', {"guild": str(inter.guild.id)}, {"$set": {"constid": [str(response.channel.id), str(response.id)]}}, True)


    @disnake.ui.button(emoji="💳", style=disnake.ButtonStyle.primary, custom_id='constsender:primary')
    async def send_constructor(self, button: disnake.ui.Button, inter: disnake.MessageInteraction) -> None:
        await ListingConst._init(inter, inter.bot, inter.author)

@dataclass
class Rarity:
    rarity: str = '\u200B'
    fee: int = 0

@dataclass
class Prices:
    bid: int = 0
    buy: int = None

@dataclass
class Item:
    name: str = "Item Name"
    description: str = "Item Description"
    attunement_required: bool = False
    attunement_info: str = "\u200B"
    rarity: Rarity = Rarity

@dataclass
class Duration:
    time: int = 0
    fee: int = 0

    @property
    def enddate(self) -> str:
        time = '\u200B' if self.time == 0 else disnake.utils.format_dt(disnake.utils.utcnow() + timedelta(seconds=self.time),"R",)
        return time

@dataclass
class Character:
    name: str = "Sir Richard of Astley"
    sheet: str = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

class ListingConst(disnake.ui.View):
    def __init__(self, bot: _LabyrinthianT, owner: disnake.Member) -> None:
        super().__init__(timeout=600)
        self.bot = bot
        self.owner = owner
        self.durations = Dict[str, Duration]
        self.rarities = Dict[str, int]
        self.duration = Duration()
        self.prices = Prices()
        self.character = Character()
        self.item = Item(
            rarity=Rarity()
        )
        self.instructions = f"""```{instructionsfrmt}To create your listing, first you must select a character using the dropdown shown below.```"""
        self.errmsg = '\u200B'
        self.selectmsg = '\u200B'
        self.embeds = List[disnake.Embed]
        self.errembs = []
        self.dur_select_added = False
        self.rarity_select_added = False
        self.modal_button_added = False
        self.send_listing_button_added = False
        self.send_listing_button_added = False

    @property
    def auction_embed(self):
        emb = (
            disnake.Embed(title=self.item.name, description=self.item.description, color=disnake.Colour.random().value)
            .set_author(name=self.character.name)
            .add_field(name="Rarity:", value=self.item.rarity.rarity, inline=True)
            .add_field(name=f"Attunement: {'Yes' if self.item.attunement_required else 'No'}", value=self.item.attunement_info, inline=True)
            .add_field(name="\u200b", value="\u200b", inline=True)
            .add_field(name=f"Top Bidder: None", value=f"Highest Bid: {self.prices.bid} gp", inline=True)
            .add_field(name="Ends:", value=self.duration.enddate, inline=True)
            .set_footer(text=f"{self.owner.name}#{self.owner.discriminator}")
        )
        if self.prices.buy != None:
            emb.insert_field_at(4, name="Buy Now Price:", value=f"{self.prices.buy} gp", inline=True)
        return emb

    @property
    def instructions_embed(self):
        return (
            disnake.Embed(title="Listing Creator", description=self.instructions)
            .add_field(name="Auction Fees:", value=self.total_cost)
        )

    @property
    def total_cost(self) -> str:
        return f"{self.duration.fee + self.item.rarity.fee} gp"

    @property
    def error_embed(self):
        return (
            disnake.Embed(title="Exception:", description=self.errmsg)
        )

    @property
    def select_embed(self):
        return disnake.Embed(
            title="Character Select",
            description=self.selectmsg,
            color=disnake.Colour.random().value
        )

    @property
    def listingdata(self):
        return {
            'topbidder': 'None',
            'topbidchar': 'None',
            'highestbid': self.prices.bid,
            'startingbid': self.prices.bid,
            'buynow': self.prices.buy,
            'enddate': disnake.utils.utcnow() + timedelta(seconds=self.duration.time),
            'character': self.character.name,
            'userid': str(self.owner.id)
        }

    @classmethod
    async def _init(cls, inter: disnake.MessageInteraction, bot: _LabyrinthianT, owner: disnake.Member):
        inst: ListingConst = cls(bot=bot, owner=owner)
        charlist = await inst.bot.sdb[f'BLCharList_{inter.guild.id}'].find({"user": str(inst.owner.id)}).to_list(None)
        srvconf = await inst.bot.dbcache.find_one('srvconf', {"guild": str(inter.guild.id)})
        durlist = srvconf.get('listingdurs', {"86400": 75,"259200": 150,"604800": 275,"1209600": 450,"2630000": 750})
        inst.rarities = srvconf.get('rarities', {"Common": 20, "Uncommon": 40, "Rare": 60, "Very Rare": 80, "Legendary": 200, "Artifact": 400, "Unknown": 0})
        inst.durations = {
            str(timedeltaplus(seconds=int(duration))): Duration(int(duration), cost)
            for duration, cost in durlist.items()
        }
        inst.add_item(CharSelect(inst.bot, charlist))
        inst.embeds = [inst.auction_embed, inst.instructions_embed]
        if len(charlist) <= 0:
            await inter.response.send_message("You don't have any characters to post a listing with!\nPlease create a character with /create before using this.", ephemeral=True)
        else:
            await inter.response.send_message(embeds=inst.embeds, view=inst, ephemeral=True)

    async def refresh_content(self, inter: disnake.Interaction, error: bool=False, select: bool=False, **kwargs):
        self.embeds = [self.auction_embed, self.instructions_embed]
        if select:
            self.embeds.insert(3, self.selectmsg)
        if error:
            for x in self.errembs:
                self.embeds.append(x)
        else:
            self.errembs = []
        if inter.response.is_done():
            await inter.edit_original_message(embeds=self.embeds, view=self, **kwargs)
        else:
            await inter.response.edit_message(embeds=self.embeds, view=self, **kwargs)

class CharSelect(disnake.ui.Select[ListingConst]):
    def __init__(self, bot: _LabyrinthianT, charlist: List[str]) -> None:
        self.bot = bot
        self.charlist = charlist
        self.firstchar = None
        super().__init__(
            placeholder="Select Character",
            min_values=1,
            max_values=1,
            row=0
        )
        self._refresh_character_select()

    def _refresh_character_select(self):
        self.options.clear()
        if len(self.charlist) > 25:
            self.add_option(
                label="Whoa, you have a lot of characters! Click here to select one.", value=TOO_MANY_CHARACTERS_SENTINEL
            )
            return
        for char in reversed(self.charlist):  # display highest-first
            selected = True if char['character'] == self.firstchar else False
            self.add_option(label=char['character'], default=selected)

    async def callback(self, inter: disnake.MessageInteraction):
        self.view: ListingConst
        await inter.response.defer()
        if len(self.values) == 1 and self.values[0] == TOO_MANY_CHARACTERS_SENTINEL:
            charname = await self._text_select_char(inter)
        else:
            charname = self.values[0]
        self.firstchar = charname
        self.view.character.name = charname
        for x in self.charlist:
            if x['character'] == charname:
                self.view.character.sheet = x['sheet']
                break
        self._refresh_character_select()
        if not self.view.dur_select_added:
            self.view.dur_select_added = True
            self.view.add_item(DurSelect(self.view.durations))
            self.view.instructions = (
                f"""```{instructionsfrmt}Now select how long you would like your listing to remain posted in the auction house for."""
                f"""\n\nThe longer the duration, the greater the auction fee.```"""
            )
        await self.view.refresh_content(inter)

    async def _text_select_char(self, inter: disnake.MessageInteraction) -> Optional[str]:
        self.disabled = True
        self.view.selectmsg="Choose one of the following characters by sending a message to this channel.\n"+'\n'.join([x['character'] for x in self.charlist]),
        await self.view.refresh_content(inter, select=True)

        try:
            input_msg: disnake.Message = await self.bot.wait_for(
                "message",
                timeout=60,
                check=lambda msg: msg.author == inter.author and msg.channel.id == inter.channel_id,
            )
            with suppress(disnake.HTTPException):
                await input_msg.delete()
                await self.view.refresh_content(inter)

            charname=[]
            for x in self.charlist:
                if "".join(input_msg.content.split()).casefold() in "".join(x['character'].split()).casefold():
                    charname = x['character']

            if charname:
                return charname
            self.view.selectmsg = "No valid character found. Use the select menu to try again."
            await self.view.refresh_content(inter, select=True)
            await asyncio.sleep(6.0)
            await self.view.refresh_content(inter)
            return None
        except TimeoutError:
            self.view.selectmsg = "No valid character found. Use the select menu to try again."
            await self.view.refresh_content(inter, select=True)
            await asyncio.sleep(6.0)
            await self.view.refresh_content(inter)
            return
        finally:
            self.disabled = False

class DurSelect(disnake.ui.Select[ListingConst]):
    def __init__(self, durlist: List[int]) -> None:
        self.durlist = durlist
        self.firstdur = None
        super().__init__(
            placeholder="Select the Duration of your Listing",
            min_values=1,
            max_values=1,
            row=1
        )
        self._refresh_dur_select()

    def _refresh_dur_select(self):
        self.options.clear()
        durcls: Duration
        for display_dur, durcls in self.durlist.items():
            selected = True if durcls == self.firstdur else False
            self.add_option(label=f"{str(timedeltaplus(seconds=durcls.time))} - {durcls.fee} gp fee", value=display_dur, default=selected)

    async def callback(self, inter: disnake.MessageInteraction):
        self.view: ListingConst
        await inter.response.defer()
        dur = self.durlist[self.values[0]]
        self.firstdur = dur
        self.view.duration = dur
        self._refresh_dur_select()
        if self.view.rarity_select_added == False:
            self.view.rarity_select_added = True
            self.view.instructions = f"""```{instructionsfrmt}Now please proceed to select the rarity of your item and whether or not it requires attunement.```"""
            self.view.add_item(RaritySelect(self.view.rarities))
            self.view.add_item(AttunementButton())
        await self.view.refresh_content(inter)

class RaritySelect(disnake.ui.Select[ListingConst]):
    def __init__(self, rarities: Dict[str, int]) -> None:
        self.firstrare = None
        self.rarities = rarities
        super().__init__(
            placeholder="Select Item Rarity",
            min_values=1,
            max_values=1,
            row=2
            )
        self._refresh_rarity_select()

    def _refresh_rarity_select(self):
        self.options.clear()
        for x in self.rarities:
            selected = True if x == self.firstrare else False
            self.add_option(label=f"{x} - {self.rarities[x]} gp fee", value=x, default=selected)

    async def callback(self, inter: disnake.MessageInteraction):
        self.view: ListingConst
        await inter.response.defer()
        rarity = self.values[0]
        self.firstrare = rarity
        self.view.item.rarity = Rarity(rarity=rarity, fee=self.view.rarities[rarity])
        if self.view.modal_button_added == False:
            self.view.modal_button_added = True
            self.view.add_item(SendModalButton(inter.bot))
            self.view.instructions = (
                f"""```{instructionsfrmt}Next, after confirming whether your item requires attunement, please press the continue button down below."""
                f"""\n\nA window will open where you can fill out the rest of the information about your item."""
                f"""\n\nPlease be warned that the window will time out after 5 minutes, if you exceed this time, you will have to close the window and try again.```"""
            )
        self._refresh_rarity_select()
        await self.view.refresh_content(inter)

class AttunementButton(disnake.ui.Button[ListingConst]):
    def __init__(self):
        self.selected = False
        super().__init__(
            style=disnake.ButtonStyle.secondary,
            label="Attunement: No",
            emoji="🔳",
            row=3
        )

    async def callback(self, inter: disnake.MessageInteraction):
        self.view: ListingConst
        await inter.response.defer()
        if self.selected == False:
            self.selected = True
            self.view.item.attunement_required = True
            self.style=disnake.ButtonStyle.success
            self.label="Attunement: Yes"
            self.emoji="✅"
        elif self.selected == True:
            self.selected = False
            self.view.item.attunement_required = True
            self.style=disnake.ButtonStyle.secondary
            self.label="Attunement: No"
            self.emoji="🔳"
        await self.view.refresh_content(inter)

class SendModalButton(disnake.ui.Button[ListingConst]):
    def __init__(self, bot: _LabyrinthianT):
        self.bot = bot
        super().__init__(
            style=disnake.ButtonStyle.green,
            label="Continue",
            emoji="➡️"
            )
    
    async def callback(self, inter: disnake.MessageInteraction):
        self.view: ListingConst
        random = randint(20934845, 790708956087)
        components=[
            disnake.ui.TextInput(
                label="Item Name",
                placeholder="Winged Boots",
                custom_id="itemName",
                style=disnake.TextInputStyle.single_line,
                max_length=256
            ),
            disnake.ui.TextInput(
                label="Description",
                placeholder=f"""Item Description""",
                custom_id="itemDesc",
                style=disnake.TextInputStyle.multi_line,
                max_length=4000
            ),
            disnake.ui.TextInput(
                label="Starting Bid",
                placeholder="GP only, no decimals",
                custom_id="bidStart",
                style=disnake.TextInputStyle.single_line,
                max_length=9
            ),
            disnake.ui.TextInput(
                label="Buy Now Price *Optional*",
                placeholder="Optional price to purchase item immediately",
                custom_id="buyNow",
                style=disnake.TextInputStyle.single_line,
                max_length=9,
                required=False
            )
        ]
        if self.view.item.attunement_required:
            components.insert(2, disnake.ui.TextInput(
                label="Additional Attunement Info",
                required=False,
                custom_id="attunementInfo",
                style=disnake.TextInputStyle.single_line,
                max_length=1024
            ))
        await inter.response.send_modal(
            title="Listing Text Form",
            custom_id=f"{random}listing_form_modal",
            components=components
        )

        try:
            modal_inter: disnake.ModalInteraction = await self.bot.wait_for(
                "modal_submit",
                check=lambda i: i.custom_id == f"{random}listing_form_modal" and i.author.id == inter.author.id,
                timeout=300,
            )
        except asyncio.TimeoutError:
            self.view.errmsg = f"It seems your form timed out, if you see this message, it is most likely because you took too long to fill out the form.\n\nPlease try again.\nError Traceback:\n```ansi\n\u001b[1;40;32m{traceback.format_exc()}```"
            self.view.errembs.append(self.view.error_embed)
            await self.view.refresh_content(inter, error=False)
            return

        errchk = False
        self.view.item.name = modal_inter.text_values['itemName']

        self.view.item.description = modal_inter.text_values['itemDesc']

        if 'attunementInfo' in modal_inter.text_values and len(modal_inter.text_values['attunementInfo']) > 0:
            self.view.item.attunement_info = modal_inter.text_values['attunementInfo']

        try:
            self.view.prices.bid = int(modal_inter.text_values['bidStart'])
        except (ValueError, TypeError):
            self.view.errmsg = f"It seems your starting bid couldn't be converted to a whole number, heres the error traceback:\n```{errorfrmt}{traceback.format_exc()}```"
            self.view.errembs.append(self.view.error_embed)
            errchk = True


        if 'buyNow' in modal_inter.text_values and len(modal_inter.text_values['buyNow']) > 0:
            try:
                if int(modal_inter.text_values['buyNow']) <= int(modal_inter.text_values['bidStart']):
                    self.view.errmsg = f"Please make sure your buy now price is larger than your starting bid"
                    self.view.errembs.append(self.view.error_embed)
                    errchk = True
                else:
                    self.view.prices.buy = int(modal_inter.text_values['buyNow'])
            except (ValueError, TypeError):
                self.view.errmsg = f"It seems your buy now price couldn't be converted to a whole number, heres the error traceback:\n```{errorfrmt}{traceback.format_exc()}```"
                self.view.errembs.append(self.view.error_embed)
                errchk = True

        if self.view.send_listing_button_added == False:
            self.view.send_listing_button_added = True
            self.view.add_item(SendListingButton(self.view.bot))

        await self.view.refresh_content(modal_inter, error=errchk)

class SendListingButton(disnake.ui.Button[ListingConst]):
    def __init__(self, bot: _LabyrinthianT):
        self.bot = bot
        super().__init__(
            style=disnake.ButtonStyle.green,
            label="Post Listing",
            emoji="🔰"
        )
    
    async def callback(self, inter: disnake.MessageInteraction):
        self.view: ListingConst
        srvconf = await self.bot.dbcache.find_one('srvconf', {"guild": str(inter.guild.id)})
        auction_channel = self.bot.get_channel(int(srvconf['ahfront']))
        listingmsg: disnake.Message = await auction_channel.send(embed=self.view.auction_embed, components=ListingActionRow(self.view.listingdata))
        usertrackmsg: disnake.Message = await inter.author.send("Thank you for using the Corrinthian Auction House.", embed=self.view.auction_embed)
        dbpackage = self.view.listingdata
        dbpackage |= {
            "listingid": str(listingmsg.id),
            "embed": self.view.auction_embed.to_dict(),
            "usertrack": [str(inter.author.id), str(usertrackmsg.id)],
            "originalchan": str(auction_channel.id),
            "guildid": str(inter.guild.id)
        }
        listingID: InsertOneResult = await self.bot.sdb['auction_listings'].insert_one(dbpackage)
        await usertrackmsg.edit(f"Thank you for using the Corrinthian Auction House.\nHeres your listing ID: {listingID.inserted_id}", components=disnake.ui.Button(style=disnake.ButtonStyle.red,label="Cancel Listing",custom_id="auction_cancel_listing",emoji="❌"))
        
        if inter.response.is_done():
            await inter.edit_original_message("Listing Created! Thank you for being a patron of the Corrinthian Auction House", embeds=[], view=None)
        else:
            await inter.response.edit_message("Listing Created! Thank you for being a patron of the Corrinthian Auction House", embeds=[], view=None)