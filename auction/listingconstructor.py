from contextlib import suppress
from typing import Optional
import disnake
from disnake.ext import commands
from yarl import URL

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
        await inter.bot.sdb['srvconf'].update_one({"guild": str(inter.guild.id)}, {"$set": {"constid": {str(response.channel.id): str(response.id)}}}, True)


    @disnake.ui.button(emoji="💳", style=disnake.ButtonStyle.primary, custom_id='constsender:primary')
    async def send_constructor(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        pass
        # Constr = ListingConst(inter.bot, inter.author)
        # await Constr._init(inter)

# class ListingConst(disnake.ui.View):
#     def __init__(self, bot: commands.Bot, owner: disnake.Member):
#         super().__init__(timeout=600)
#         self.bot = bot
#         self.firstchar = None

#     async def _init(self, inter: disnake.MessageInteraction):
#         self.charlist = await self.bot.sdb[f'BLCharList_{inter.guild.id}'].distinct("character", {"user": str(self.owner.id)})
#         self._refresh_character_select()
#         emb = disnake.Embed()
#         await inter.response.send_message(embed=emb, view=self, ephemeral=True)

#     async def refresh_view(self, inter: disnake.Interaction, **kwargs):
#         if inter.response.is_done():
#             await inter.edit_original_message(view=self, **kwargs)
#         else:
#             await inter.response.edit_message(view=self, **kwargs)

#     @disnake.ui.select(placeholder="Select Character", min_values=1, max_values=1)
#     async def select_char(self, select: disnake.ui.Select, inter: disnake.MessageInteraction):
#         await inter.response.defer()
#         if len(select.values) == 1 and select.values[0] == TOO_MANY_CHARACTERS_SENTINEL:
#             charname = await self._text_select_char(inter)
#         else:
#             charname = select.values[0]

#     def _refresh_character_select(self):
#         self.select_char.options.clear()
#         if len(self.charlist) > 25:
#             self.select_char.add_option(
#                 label="Whoa, you have a lot of characters! Click here to select one.", value=TOO_MANY_CHARACTERS_SENTINEL
#             )
#             return
#         for char in reversed(self.charlist):  # display highest-first
#             selected = True if char == self.firstchar else False
#             self.select_char.add_option(label=char, value=char)

#     async def _text_select_char(self, inter: disnake.MessageInteraction) -> Optional[str]:
#         self.select_char.disabled = True
#         selectmsg: disnake.Message = await inter.followup.send(
#             "Choose one of the following characters by sending a message to this channel.\n"+'\n'.join([x['character'] for x in self.charlist])
#         )

#         try:
#             input_msg: disnake.Message = await self.bot.wait_for(
#                 "message",
#                 timeout=60,
#                 check=lambda msg: msg.author == inter.author and msg.channel.id == inter.channel_id,
#             )
#             with suppress(disnake.HTTPException):
#                 await input_msg.delete()
#                 await selectmsg.delete()

#             charname=[]
#             for x in self.charlist:
#                 if "".join(input_msg.content.split()).casefold() in "".join(x['character'].split()).casefold():
#                     charname = x['character']

#             if charname:
#                 await self.inter.followup.send(f"{charname} selected.", delete_after=4)
#                 return charname
#             await self.inter.followup.send("No valid character found. Use the select menu to try again.", delete_after=6)
#             return None
#         except TimeoutError:
#             await self.inter.followup.send("No valid character found. Use the select menu to try again.", delete_after=6)
#             return
#         finally:
#             self.select_char.disabled = False




# class ListingModal(disnake.ui.Modal):
#     def __init__(self, bot: commands.Bot, title: str, components: Components, custom_id: str = ..., timeout: float = 600) -> None:
#         self.bot = bot
#         super().__init__(title=title, components, custom_id, timeout)




# listingmsg = {
#     "content": '@aetherbreaker',
#     "embeds":{
#         "type": "rich",
#         "title": 'Winged Boots',
#         "description": "While you wear these boots, you have a flying speed equal to your walking speed. You can use the boots to fly for up to 4 hours, all at once or in several shorter flights, each one using a minimum of 1 minute from the duration. If you are flying when the duration expires, you descend at a rate of 30 feet per round until you land.\n\nThe boots regain 2 hours of flying capability for every 12 hours they aren't in use.",
#         "color": "0x00FFFF",
#         "fields": [
#         {
#             "name": 'Rarity: Uncommon',
#             "value": "\u200B",
#             "inline": True
#         },
#         {
#             "name": 'Attunement: Yes',
#             "value": '*Additional attunement info*',
#             "inline": True
#         },
#         {
#             "name": '\u220B',
#             "value": "\u200B",
#             "inline": True
#         },
#         {
#             "name": 'Highest Bid',
#             "value": '1000 gp',
#             "inline": True
#         },
#         {
#             "name": 'Buy Now Price',
#             "value": '2000 gp',
#             "inline": True
#         }
#         ],
#         "thumbnail": {
#         "url": URL(URL="https://www.dndbeyond.com/avatars/thumbnails/7/490/1000/1000/636284785276517401.jpeg"),
#         "height": 0,
#         "width": 0
#         },
#         "author": {
#         "name": 'Character Name'
#         }
#     }
# }