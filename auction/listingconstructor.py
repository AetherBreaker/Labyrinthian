import asyncio
from contextlib import suppress
from copy import deepcopy
import numbers
from os import remove
from pickletools import long1
from time import time
import traceback
from turtle import st
from typing import List, Optional
from urllib.parse import MAX_CACHE_SIZE
import disnake
from disnake.ext import commands
from yarl import URL

from utilities.checks import urlCheck

TOO_MANY_CHARACTERS_SENTINEL = "__special:too_many_characters"

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

class ListingConst(disnake.ui.View):
    def __init__(self, bot: commands.Bot, owner: disnake.Member):
        super().__init__(timeout=600)
        self.bot = bot
        self.owner = owner
        self.charname = '\u200B'
        self.sheet = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
        self.dur_select_added = False
        self.dur = 0
        self.durcost = 0
        self.rarity_select_added = False
        self.rarity = ""
        self.rarcost = 0
        self.attunement = None
        self.modal_button_added = False
        self.itemname = None
        self.itemdesc = None
        self.attunementinfo = None
        self.bidstart = None
        self.buynow = None
        self.embeddicts = {
            "Listing": {
                "type": "rich",
                "title": 'item name',
                "description": "item description",
                "color": disnake.Colour.random().value,
                "fields": [
                    {
                        "name": 'Rarity:',
                        "value": "\u200B",
                        "inline": True
                    },
                    {
                        "name": 'Attunement: ',
                        "value": '*Additional attunement info*',
                        "inline": True
                    },
                    {
                        "name": '\u200B',
                        "value": "\u200B",
                        "inline": True
                    },
                    {
                        "name": 'Starting Bid:',
                        "value": '\u200B',
                        "inline": True
                    },
                    {
                        "name": 'Buy Now Price:',
                        "value": '\u200B',
                        "inline": True
                    },
                    {
                        "name": 'Ends:',
                        "value": '\u200B',
                        "inline": True
                    }
                ],
                "author": {
                    "name": 'Character Name',
                    "url": 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
                }
            },
            "Instructions": {
                "type": "rich",
                "title": 'Listing Creator',
                "description": "To create your listing, first you must select a character using the dropdown shown below.",
                "color": disnake.Colour.random().value,
                "fields": [
                    {
                        "name": 'Auction Fees:',
                        "value": f"{self.durcost+self.rarcost} gp",
                        "inline": False
                    }
                ]
            }
        }

    async def _init(self, inter: disnake.MessageInteraction):
        self.charlist = await self.bot.sdb[f'BLCharList_{inter.guild.id}'].find({"user": str(self.owner.id)}).to_list(None)
        durlist = await self.bot.sdb['srvconf'].find_one({"guild": str(inter.guild.id)})
        self.durlist = durlist['listingdurs'] if 'listingdurs' in durlist else {"86400": 75,"259200": 150,"604800": 275,"1209600": 450,"2630000": 750}
        self.embeds = [disnake.Embed.from_dict(x) for x in self.embeddicts.values()]
        self.add_item(CharSelect(self.bot, self.charlist))
        await inter.response.send_message(embeds=self.embeds, view=self, ephemeral=True)

    async def refresh_content(self, inter: disnake.Interaction, removeerror: bool=True, **kwargs):
        if removeerror and 'Error' in self.embeddicts:
            self.embeddicts.pop('Error')
        self.embeddicts['Listing']['author']['name'] = self.charname
        self.embeddicts['Listing']['author']['url'] = self.sheet
        if self.dur != 0:
            self.embeddicts['Listing']['fields'][5]['value'] = f"<t:{int(time())+int(self.dur)}:R>"
        self.embeddicts['Instructions']['fields'][0]['value'] = f"{self.durcost+self.rarcost} gp"
        self.embeddicts['Listing']['fields'][0]['value'] = f'\u200B{self.rarity}'
        if self.attunement != None:
            self.embeddicts['Listing']['fields'][1]['name'] = f"Attunement: {'Yes' if self.attunement else False}"
        self.embeds = [disnake.Embed.from_dict(x) for x in self.embeddicts.values()]
        if inter.response.is_done():
            await inter.edit_original_message(embeds=self.embeds, view=self, **kwargs)
        else:
            await inter.response.edit_message(embeds=self.embeds, view=self, **kwargs)

    async def content_error_check(self, inter: disnake.Interaction):
        # bid not a number
        try:
            self.bidstart = int(self.bidstart)
        except ValueError:
            self.embeddicts['Error'] = {
                "title": "Exception:",
                "description": f"It seems your starting bid couldn't be converted to a whole number, heres the error traceback:\n```ansi\n\u001b[1;40;32m{traceback.format_exc()}```",
                "color": disnake.Colour.red().value
            }
            await self.refresh_content(inter, False)
            return True

        # buynow not a number
        try:
            self.buynow = int(self.buynow)
        except ValueError:
            self.embeddicts['Error'] = {
                "title": "Exception:",
                "description": f"It seems your buy now price couldn't be converted to a whole number, heres the error traceback:\n```ansi\n\u001b[1;40;32m{traceback.format_exc()}```",
                "color": disnake.Colour.red().value
            }
            await self.refresh_content(inter, False)
            return True


        tembed = deepcopy(self.embeddicts['Listing'])
        tembed['title'] = self.itemname
        tembed['description'] = self.itemdesc
        tembed['fields'][1]['value'] = self.attunementinfo
        tembed['fields'][3]['value'] = self.bidstart
        tembed['fields'][4]['value'] = self.buynow
        print(tembed)
        tembed = disnake.Embed.from_dict(tembed)
        print(tembed)
        if len(tembed) > 6000:
            self.embeddicts['Error'] = {
                "title": "Error",
                "description": f"```ansi\n1;40;32mIt seems the total length of the embed exceeded 6000 characters, please try to reduce the length of your listing to below 6000 characters and try again.```",
                "color": disnake.Colour.red().value
            }
            await self.refresh_content(inter, False)
            return True
        return False



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
            self.view.embeddicts['Instructions']['description'] = f"""Now select how long you would like your listing to remain posted in the auction house for.
            The longer the duration, the greater the auction fee."""
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
            self.add_option(label=f"{optstr} - costs: {cost} gp", value=dur, default=selected)

    async def callback(self, inter: disnake.MessageInteraction):
        await inter.response.defer()
        dur = self.values[0]
        self.firstdur = dur
        self.view.durcost = self.durlist[dur]
        self.view.dur = dur
        self._refresh_dur_select()
        if self.view.rarity_select_added == False:
            self.view.rarity_select_added = True
            self.view.embeddicts['Instructions']['description'] = f"""Now please proceed to select the rarity of your item and whether or not it requires attunement."""
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
            self.add_option(label=x, default=selected)

    async def callback(self, inter: disnake.MessageInteraction):
        await inter.response.defer()
        self.firstrare = self.values[0]
        self.view.rarity = self.values[0]
        self.view.rarcost = self.raritylist[self.values[0]]
        if self.view.modal_button_added == False:
            self.view.modal_button_added = True
            self.view.add_item(SendModalButton(inter.bot))
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
            self.view.attunement = True
            self.style=disnake.ButtonStyle.success
            self.label="Attunement: Yes"
            self.emoji="✅"
        elif self.selected == True:
            self.selected = False
            self.view.attunement = False
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
                max_length=256,
                min_length=2
            ),
            disnake.ui.TextInput(
                label="Description",
                placeholder=f"""Item Description""",
                custom_id="itemDesc",
                style=disnake.TextInputStyle.multi_line,
                min_length=2,
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
                max_length=10
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
            self.view.attunementinfo = modal_inter.text_values['attunementInfo']
        self.view.bidstart = modal_inter.text_values['bidStart']
        if 'buyNow' in modal_inter.text_values and len(modal_inter.text_values['buyNow']) > 0:
            self.view.buynow = modal_inter.text_values['buyNow']
        
        if await self.view.content_error_check(modal_inter):
            return