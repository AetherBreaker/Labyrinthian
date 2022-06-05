import asyncio
from contextlib import suppress
from copy import deepcopy
from dataclasses import dataclass
from datetime import timedelta
from time import time
import traceback
from typing import List, Optional
import disnake
from disnake.ext import commands

from utilities.checks import urlCheck

TOO_MANY_CHARACTERS_SENTINEL = "__special:too_many_characters"
instructionsfrmt = "ansi\n\u001b[1;40;32m"
errorfrmt = "ansi\n\u001b[1;40;31m"

async def send_const(inter: disnake.ApplicationCommandInteraction, *args, **kwargs):
    Send = ConstSender(*args, **kwargs)
    await Send._init(inter)

class ConstSender(disnake.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def _init(self, inter: disnake.ApplicationCommandInteraction):
        emb = disnake.Embed(
            title="Auction House",
            description="To post an item to the auction house, click the button below and follow the instructions provided."
        )
        await inter.response.send_message(embed=emb, view=self)
        response = await inter.original_message()
        await inter.bot.sdb['srvconf'].update_one({"guild": str(inter.guild.id)}, {"$set": {"constid": [str(response.channel.id), str(response.id)]}}, True)


    @disnake.ui.button(emoji="💳", style=disnake.ButtonStyle.primary, custom_id='constsender:primary')
    async def send_constructor(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        Constr = ListingConst(inter.bot, inter.author)
        await Constr._init(inter)

@dataclass
class Rarity:
    display_name: str
    cost: int

@dataclass
class Item:
    name: str
    description: str
    attunement_required: bool
    attunement_info: str
    rarity: str

    @property
    def attunement_repr(self) -> str:
        return self.attunement_info if self.attunement_required else "\u200B"

@dataclass
class Duration:
    display: str
    time: int
    cost: int

    def __str__(self) -> str:
        return disnake.utils.format_dt(
            disnake.utils.utcnow() + timedelta(days=self.time),
            "R",
        )

@dataclass
class Character:
    name: str
    sheet: str

class ListingConst(disnake.ui.View):
    def __init__(self, bot: commands.Bot, owner: disnake.Member):
        super().__init__(timeout=600)
        self.bot = bot
        self.owner = owner
        self.character = Character(
            'Character Name',
            'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
        )
        self.dur_select_added = False
        self.rarity_select_added = False
        self.modal_button_added = False
        self.send_listing_button_added = False
        self.embeddicts = {
            "Listing": {
                "type": "rich",
                "title": 'item name',
                "description": "item description",
                "color": disnake.Colour.random().value,
                "fields": {
                    "rarity": {
                        "name": 'Rarity:',
                        "value": "\u200B",
                        "inline": True
                    },
                    "attunement": {
                        "name": 'Attunement: No',
                        "value": '\u200B',
                        "inline": True
                    },
                    "divider": {
                        "name": '\u200B',
                        "value": "\u200B",
                        "inline": True
                    },
                    "bids": {
                        "name": 'Starting Bid:',
                        "value": '\u200B',
                        "inline": True
                    },
                    "buynow": {
                        "name": '',
                        "value": '',
                        "inline": True
                    },
                    "duration": {
                        "name": 'Ends:',
                        "value": '\u200B',
                        "inline": True
                    }
                },
                "footer": {
                    "text": f"{self.owner.name}#{self.owner.discriminator}"
                },
                "author": {
                    "name": 'Character Name',
                    "url": 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
                }
            },
            "Instructions": {
                "type": "rich",
                "title": 'Listing Creator',
                "description": f"""```{instructionsfrmt}To create your listing, first you must select a character using the dropdown shown below.```""",
                "color": disnake.Colour.random().value,
                "fields": {
                    "fees": {
                        "name": 'Auction Fees:',
                        "value": f"0 gp",
                        "inline": False
                    }
                }
            }
        }
        self.charname = self.embeddicts['Listing']['author']['name']
        self.sheet = self.embeddicts['Listing']['author']['url']
        self.displaydur = self.embeddicts['Listing']['fields']['duration']
        self.durcost = 0
        self.rarity = self.embeddicts['Listing']['fields']['rarity']
        self.rarcost = 0
        self.attunement = self.embeddicts['Listing']['fields']['attunement']
        self.itemname = self.embeddicts['Listing']['title']
        self.itemdesc = self.embeddicts['Listing']['description']
        self.bids = self.embeddicts['Listing']['fields']['bids']
        self.buynow = self.embeddicts['Listing']['fields']['buynow']
        self.instructions = self.embeddicts['Instructions']
        self.fees = self.embeddicts['Instructions']['fields']['fees']
        self.datadict = {
            "duration": 0,
            "topbid": 0,
            "topbiduser": None,
            "buyprice": None
        }
        self.dur = self.datadict['duration']
        self.biddata = self.datadict['topbid']
        self.buydata = self.datadict['buyprice']

    @property
    def total_cost(self) -> str:
        return f"{self.duration.cost + self.item.rarity.cost} gp"

    @property
    def auction_embed(self):
        return (
            disnake.Embed(title=self.item.name, description=self.item.description)
            .set_author(name=self.character.name)
            .add_field(name="Rarity:", value=self.item.rarity.display_name)
            .add_field(name="Attunement:", value=self.item.attunement_repr)
            .add_field(name="\u200b", value="\u200b")
            .add_field(name="Highest Bid:", value="-")
            .add_field(name="Buy Now Price:", value="-")
            .add_field(name="Ends:", value=str(self.duration))
        )

    @classmethod
    async def _init(self, inter: disnake.MessageInteraction):
        charlist = await self.bot.sdb[f'BLCharList_{inter.guild.id}'].find({"user": str(self.owner.id)}).to_list(None)
        srvconf= await self.bot.sdb['srvconf'].find_one({"guild": str(inter.guild.id)})
        durlist = srvconf.get('listingdurs', {"1 Day": ("86400", 75),"3 Days": ("259200", 150),"1 Week": ("604800", 275),"2 Weeks": ("1209600", 450),"1 Month": ("2630000", 750)})
        rarlist = srvconf.get('rarities', {"Common": 20, "Uncommon": 40, "Rare": 60, "Very Rare": 80, "Legendary": 200, "Artifact": 400, "Unknown": 0})
        self.durations = {
            display_dur: Duration(int(duration), cost)
            for display_dur, (duration, cost) in durlist.items()
        }
        self.rarities = {
            rarity: Rarity(rarity, fee)
            for rarity, fee, in rarlist.items()
        }
        embcon = deepcopy(self.embeddicts)
        for x in embcon.values():
            if 'fields' in x:
                listconv = []
                for y in x['fields'].values():
                    if y['name'] != '':
                        listconv.append(y)
                x.update({'fields': listconv})
        self.embeds = [disnake.Embed.from_dict(x) for x in embcon.values()]
        self.add_item(CharSelect(self.bot, self.charlist))
        if len(self.charlist) <= 0:
            await inter.response.send_message("You don't have any characters to post a listing with!\nPlease create a character with /create before using this.", ephemeral=True)
        else:
            await inter.response.send_message(embeds=self.embeds, view=self, ephemeral=True)

    async def refresh_content(self, inter: disnake.Interaction, removeerror: bool=True, **kwargs):
        print(self.embeddicts)
        if removeerror:
            for x in self.embeddicts:
                if 'Error' in x:
                    self.embeddicts.pop(x)
        embcon = deepcopy(self.embeddicts)
        for x in embcon.values():
            if 'fields' in x:
                listconv = []
                for y in x['fields'].values():
                    if y['name'] != '':
                        listconv.append(y)
                x.update({'fields': listconv})
        self.embeds = [disnake.Embed.from_dict(x) for x in embcon.values()]
        if inter.response.is_done():
            await inter.edit_original_message(embeds=self.embeds, view=self, **kwargs)
        else:
            await inter.response.edit_message(embeds=self.embeds, view=self, **kwargs)

class CharSelect(disnake.ui.Select[ListingConst]):
    def __init__(self, bot: commands.Bot, charlist: List[str]) -> None:
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
            self.add_option(label=char['character'], value=char['character'], default=selected)

    async def callback(self, inter: disnake.MessageInteraction):
        await inter.response.defer()
        if len(self.values) == 1 and self.values[0] == TOO_MANY_CHARACTERS_SENTINEL:
            charname = await self._text_select_char(inter)
        else:
            charname = self.values[0]
        self.firstchar = charname
        self.view.charname = charname
        for x in self.charlist:
            if x['character'] == charname:
                self.view.sheet = x['sheet']
                break
        self._refresh_character_select()
        if not self.view.dur_select_added:
            self.view.dur_select_added = True
            self.view.add_item(DurSelect(self.view.durlist))
            self.view.instructions['description'] = (
                f"""```{instructionsfrmt}Now select how long you would like your listing to remain posted in the auction house for."""
                f"""\n\nThe longer the duration, the greater the auction fee.```"""
            )
        await self.view.refresh_content(inter)

    async def _text_select_char(self, inter: disnake.MessageInteraction) -> Optional[str]:
        self.disabled = True
        emb = {
            "type": "rich",
            "title": "Character Select",
            "description": "Choose one of the following characters by sending a message to this channel.\n"+'\n'.join([x['character'] for x in self.charlist]),
            "color": disnake.Colour.random().value
        }
        self.view.embeddicts['SelectChar'] = (emb)
        await self.view.refresh_content(inter)

        try:
            input_msg: disnake.Message = await self.bot.wait_for(
                "message",
                timeout=60,
                check=lambda msg: msg.author == inter.author and msg.channel.id == inter.channel_id,
            )
            with suppress(disnake.HTTPException):
                await input_msg.delete()
                self.view.embeddicts.pop('SelectChar')
                await self.view.refresh_content(inter)

            charname=[]
            for x in self.charlist:
                if "".join(input_msg.content.split()).casefold() in "".join(x['character'].split()).casefold():
                    charname = x['character']

            if charname:
                return charname
            emb['description'] = "No valid character found. Use the select menu to try again."
            self.view.embeddicts['SelectChar'] = (emb)
            await self.view.refresh_content(inter)
            await asyncio.sleep(6.0)
            self.view.embeddicts.pop('SelectChar')
            await self.view.refresh_content(inter)
            return None
        except TimeoutError:
            emb['description'] = "No valid character found. Use the select menu to try again."
            self.view.embeddicts['SelectChar'] = (emb)
            await self.view.refresh_content(inter)
            await asyncio.sleep(6.0)
            self.view.embeddicts.pop('SelectChar')
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
        durlist = {str(y): x for x,y in self.durlist.items()}
        for cost,dur in reversed(durlist.items()):  # display highest-first
            months, remainder = divmod(int(dur), 2630000)
            weeks, remainder = divmod(remainder, 604800)
            days, remainder = divmod(remainder, 86400)
            hours, remainder = divmod(remainder, 3600)
            minutes, seconds = divmod(remainder, 60)
            timetup = {'month': months, 'week': weeks, 'day': days, 'hour': hours, 'minute': minutes, 'second': seconds}
            optstr = []
            for x,y in timetup.items():
                if y > 0:
                    optstr.append(f'{y} {x}{"s" if y > 1 else ""}')
            optstr = ', '.join(optstr)
            selected = True if dur == self.firstdur else False
            self.add_option(label=f"{optstr} - {cost} gp fee", value=dur, default=selected)

    async def callback(self, inter: disnake.MessageInteraction):
        await inter.response.defer()
        dur = self.values[0]
        self.firstdur = dur
        self.view.fees['value'] = f"{self.view.rarcost+self.durlist[dur]} gp"
        self.view.durcost = self.durlist[dur]
        self.view.displaydur['value'] = f"<t:{int(time())+int(dur)}:R>"
        self.view.dur = dur
        self._refresh_dur_select()
        if self.view.rarity_select_added == False:
            self.view.rarity_select_added = True
            self.view.instructions['description'] = f"""```{instructionsfrmt}Now please proceed to select the rarity of your item and whether or not it requires attunement.```"""
            self.view.add_item(RaritySelect())
            self.view.add_item(AttunementButton())
        await self.view.refresh_content(inter)

class RaritySelect(disnake.ui.Select[ListingConst]):
    def __init__(self) -> None:
        self.raritylist = {
            "Common": 20,
            "Uncommon": 40,
            "Rare": 60,
            "Very Rare": 80,
            "Legendary": 200,
            "Artifact": 400,
            "Unknown": 0
        }
        self.firstrare = None
        super().__init__(
            placeholder="Select Item Rarity",
            min_values=1,
            max_values=1,
            row=2
            )
        self._refresh_rarity_select()

    def _refresh_rarity_select(self):
        self.options.clear()
        for x in self.raritylist:
            selected = True if x == self.firstrare else False
            self.add_option(label=f"{x} - {self.raritylist[x]} gp fee", value=x, default=selected)

    async def callback(self, inter: disnake.MessageInteraction):
        await inter.response.defer()
        self.firstrare = self.values[0]
        self.view.rarity['value'] = self.values[0]
        self.view.rarcost = self.raritylist[self.values[0]]
        self.view.fees['value'] = f"{self.raritylist[self.values[0]]+self.view.durcost} gp"
        if self.view.modal_button_added == False:
            self.view.modal_button_added = True
            self.view.add_item(SendModalButton(inter.bot))
            self.view.instructions['description'] = (
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
        await inter.response.defer()
        if self.selected == False:
            self.selected = True
            self.view.attunement['name'] = "Attunement: Yes"
            self.style=disnake.ButtonStyle.success
            self.label="Attunement: Yes"
            self.emoji="✅"
        elif self.selected == True:
            self.selected = False
            self.view.attunement['name'] = "Attunement: No"
            self.style=disnake.ButtonStyle.secondary
            self.label="Attunement: No"
            self.emoji="🔳"
        await self.view.refresh_content(inter)

class SendModalButton(disnake.ui.Button[ListingConst]):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        super().__init__(
            style=disnake.ButtonStyle.green,
            label="Continue",
            emoji="➡️"
            )
    
    async def callback(self, inter: disnake.MessageInteraction):
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
                max_length=10
            ),
            disnake.ui.TextInput(
                label="Buy Now Price *Optional*",
                placeholder="Optional price to purchase item immediately",
                custom_id="buyNow",
                style=disnake.TextInputStyle.single_line,
                max_length=10,
                required=False
            )
        ]
        if self.view.attunement:
            components.insert(2, disnake.ui.TextInput(
                label="Additional Attunement Info",
                placeholder="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                value="\u200B",
                required=False,
                custom_id="attunementInfo",
                style=disnake.TextInputStyle.single_line,
                max_length=1024
            ))
        await inter.response.send_modal(
            title="Listing Text Form",
            custom_id="this_is_an_interesting_custom_id_hmmm_yes",
            components=components
        )

        try:
            modal_inter: disnake.ModalInteraction = await self.bot.wait_for(
                "modal_submit",
                check=lambda i: i.custom_id == "this_is_an_interesting_custom_id_hmmm_yes" and i.author.id == inter.author.id,
                timeout=300,
            )
        except asyncio.TimeoutError:
            self.view.embeddicts['Error'] = {
                "title": "Exception",
                "description": f"It seems your form timed out, if you see this message, it is most likely because you took too long to fill out the form.\n\nPlease try again.\nError Traceback:\n```ansi\n\u001b[1;40;32m{traceback.format_exc()}```"
            }
            await self.view.refresh_content(inter, False)
            return
        
        self.view.itemname = modal_inter.text_values['itemName']

        self.view.itemdesc = modal_inter.text_values['itemDesc']

        if 'attunementInfo' in modal_inter.text_values and len(modal_inter.text_values['attunementInfo']) > 0:
            self.view.attunement['value'] = modal_inter.text_values['attunementInfo']
        
        try:
            self.view.biddata = int(modal_inter.text_values['bidStart'])
            self.view.bids['value'] = f"{modal_inter.text_values['bidStart']} gp"
        except (ValueError, TypeError):
            errindex = 0
            for x in self.view.embeddicts:
                if 'Error' in x:
                    errindex += 1
            self.view.embeddicts[f'Error{errindex}'] = {
                "title": "Exception:",
                "description": f"It seems your starting bid couldn't be converted to a whole number, heres the error traceback:\n```{errorfrmt}{traceback.format_exc()}```",
                "color": disnake.Colour.red().value
            }
        if 'buyNow' in modal_inter.text_values and len(modal_inter.text_values['buyNow']) > 0:
            try:
                self.view.buydata = int(modal_inter.text_values['buyNow'])
                self.view.buynow['name'] = "Buy Now Price:"
                self.view.buynow['value'] = f"{modal_inter.text_values['buyNow']} gp"
            except (ValueError, TypeError):
                errindex = 0
                for x in self.view.embeddicts:
                    if 'Error' in x:
                        errindex += 1
                self.view.embeddicts[f'Error{errindex}'] = {
                    "title": "Exception:",
                    "description": f"It seems your buy now price couldn't be converted to a whole number, heres the error traceback:\n```{errorfrmt}{traceback.format_exc()}```",
                    "color": disnake.Colour.red().value
                }
        
        await self.view.refresh_content(modal_inter)