from asyncio import TimeoutError
from contextlib import suppress
from copy import deepcopy
from typing import TYPE_CHECKING, Dict, List, Optional, TypeVar

import disnake
from bson import ObjectId
from disnake.ext import commands
from pymongo import DESCENDING

TOO_MANY_CHARACTERS_SENTINEL = "__special:too_many_characters"

_LabyrinthianT = TypeVar("_LabyrinthianT", bound=disnake.Client)
if TYPE_CHECKING:
    from bot import Labyrinthian

    _LabyrinthianT = Labyrinthian

async def create_CharSelect(inter: disnake.ApplicationCommandInteraction, *args, **kwargs):
    Sel = CharSelect(*args, **kwargs)
    await Sel._init(inter)


class CharSelect(disnake.ui.View):
    def __init__(self, bot: _LabyrinthianT, owner: disnake.User, guild: disnake.Guild, user: disnake.Member=None, ephem: bool=False):
        super().__init__(timeout=180)
        self.bot = bot
        self.owner = owner
        self.guild = guild
        self.user = user
        self.ephem = ephem

    async def _init(self, inter: disnake.ApplicationCommandInteraction):
        self.embed = disnake.Embed.from_dict(
            {
                "title": "Badge browser",
                "description": f"Select a character." if self.user is None else f"Select one of <@{self.user.id}>'s characters below.",
                "color": disnake.Color.random().value,
                "fields": [
                    {
                        "name": "Badge Information:",
                        "value": f"Current Badges: \nExpected Level: ",
                        "inline": True
                    },
                    {
                        "name": "Class Levels:",
                        "value": "\u200B",
                        "inline": True
                    },
                    {
                        "name": f"Total Levels: ",
                        "value": "\u200B", 
                        "inline": True
                    }
                ]
            }
        )
        self.charlist = await self.bot.sdb[f'BLCharList_{self.guild.id}'].find({"user": str(self.owner.id if self.user is None else self.user.id)}).sort("character", DESCENDING).to_list(None)
        self._refresh_character_select()
        if self.charlist:
            await inter.response.send_message(embed=self.embed, view=self, ephemeral=self.ephem)
        else:
            await inter.response.send_message("You don't have any characters yet!")

    async def refresh_content(self, inter: disnake.Interaction):
        if inter.response.is_done():
            await inter.edit_original_message(embed=self.embed, view=self)
        else:
            await inter.response.edit_message(embed=self.embed, view=self)

    def _refresh_character_select(self):
        self.select_char.options.clear()
        if len(self.charlist) > 25:
            self.select_char.add_option(
                label="Whoa, you have a lot of characters! Click here to select one.", value=TOO_MANY_CHARACTERS_SENTINEL
            )
            return
        for char in reversed(self.charlist):  # display highest-first
            self.select_char.add_option(label=char['character'], value=char['character'])

    async def interaction_check(self, inter: disnake.ApplicationCommandInteraction) -> bool:
        if inter.user.id == self.owner.id:
            return True
        await inter.response.send_message("You are not the owner of this menu.", ephemeral=True)
        return False

    @disnake.ui.select(placeholder="Select Character", min_values=1, max_values=1)
    async def select_char(self, select: disnake.ui.Select, inter: disnake.MessageInteraction):
        await inter.response.defer()
        if len(select.values) == 1 and select.values[0] == TOO_MANY_CHARACTERS_SENTINEL:
            charname = await self._text_select_char(inter)
        else:
            charname = select.values[0]
        if charname is None:
            await self.refresh_content(inter)
            return
        Log = LogBrowser(self.bot, self.owner, self.guild, charname, self.charlist, self.user)
        await Log._init(inter)

    async def _text_select_char(self, inter: disnake.MessageInteraction) -> Optional[str]:
        self.select_char.disabled = True
        selectmsg: disnake.Message = await inter.followup.send(
            "Choose one of the following characters by sending a message to this channel.\n"+'\n'.join([x['character'] for x in self.charlist])
        )

        try:
            input_msg: disnake.Message = await self.bot.wait_for(
                "message",
                timeout=60,
                check=lambda msg: msg.author == inter.author and msg.channel.id == inter.channel_id,
            )
            with suppress(disnake.HTTPException):
                await input_msg.delete()
                await selectmsg.delete()

            charname = []
            for x in self.charlist:
                if "".join(input_msg.content.split()).casefold() in "".join(x['character'].split()).casefold():
                    charname = x['character']

            if charname:
                await inter.followup.send(f"{charname} selected.", delete_after=4)
                return charname
            await inter.followup.send("No valid character found. Use the select menu to try again.", delete_after=6)
            return None
        except TimeoutError:
            await inter.followup.send("No valid character found. Use the select menu to try again.", delete_after=6)
            return
        finally:
            self.select_char.disabled = False

class LogBrowser(disnake.ui.View):
    def __init__(self, bot: _LabyrinthianT, owner: disnake.Member, guild: disnake.Guild, charname: str, charlist: List[Dict], user: disnake.Member):
        super().__init__(timeout=180)
        self.bot = bot
        self.owner = owner
        self.guild = guild
        self.firstchar = charname
        self.charlist = charlist
        self.user = owner if user is None else user

        self.first_page.disabled = True
        self.prev_page.disabled = True


    async def _init(self, inter: disnake.MessageInteraction):
        self.embeds = await self.construct_embeds(self.firstchar)
        if len(self.embeds) == 1:
            self.next_page.disabled = True
            self.last_page.disabled = True
        else:
            self.next_page.disabled = False
            self.last_page.disabled = False
        self.embed_count = 0
        self._refresh_character_select()
        await self.refresh_content(inter)

    async def refresh_content(self, inter: disnake.Interaction):
        if inter.response.is_done():
            await inter.edit_original_message(embed=self.embeds[self.embed_count], view=self)
        else:
            await inter.response.edit_message(embed=self.embeds[self.embed_count], view=self)

    async def construct_embeds(self, charname: str) -> List[disnake.Embed]:
        char = await self.bot.dbcache.find_one(f'BLCharList_{self.guild.id}', {"user": str(self.user.id), "character": charname})
        badgelog = await self.bot.sdb[f"BadgeLogMaster_{self.guild.id}"].find({"charRefId": ObjectId(char['_id']), "user": str(self.user.id)}).sort("timestamp", DESCENDING).to_list(None)
        embeds = []
        pageindex = 0
        Embednolog = {
            "title": f"{charname}'s Info'",
            "description": f"Played by: <@{self.user.id}>",
            "color": disnake.Color.random().value,
            "url": f"{char['sheet']}",
            "fields": [
                {
                    "name": "Badge Information:",
                    "value": f"Current Badges: {char['currentbadges']}\nExpected Level: {char['expectedlvl']}",
                    "inline": True
                },
                {
                    "name": "Class Levels:",
                    "value": '\n'.join([f'{x}: {y}' for x,y in char['classes'].items()]),
                    "inline": True
                },
                {
                    "name": f"Total Levels: {char['charlvl']}",
                    "value": "\u200B", 
                    "inline": True
                },
                {
                    "name": "Badge Log",
                    "value": "This character doesn't have any entries yet..."
                }
            ]
        }
        if badgelog:
            overflow = []
            while badgelog:
                pageindex += 1
                Embed = deepcopy(Embednolog)
                logstr = []
                while badgelog:
                    if overflow:
                        logstr.append(overflow[0])
                        overflow.pop(0)
                    Embed['fields'][3]['value'] = ""
                    if badgelog[0]['badges added'] < 0:
                        isneg = True
                    else:
                        isneg = False
                    logstr.append(f"{'' if char['user'] == badgelog[0]['user'] else '<@'+badgelog[0]['user']+'> at'} <t:{badgelog[0]['timestamp']}:f>\n`{badgelog[0]['character']} {'lost badges' if isneg else 'was awarded'} {badgelog[0]['previous badges']}({'' if isneg else '+'}{badgelog[0]['badges added']}) {'to' if isneg else 'by'}` <@{badgelog[0]['awarding DM']}>")
                    badgelog.pop(0)
                    Embed['fields'][3]['value'] = '\n\n'.join(logstr)
                    result = disnake.Embed.from_dict(Embed)
                    if len(result) >= 6000 or len(Embed['fields'][3]['value']) >= 400 or not len(badgelog) > 0:
                        if len(logstr) > 1:
                            overflow.append(logstr[-1])
                            logstr = logstr[:-1]
                        break
                Embed['fields'][3]['value'] = ""
                Embed['fields'][3]['value'] = '\n\n'.join(logstr)
                embeds.append(disnake.Embed.from_dict(Embed))
        else:
            embeds.append(disnake.Embed.from_dict(Embednolog))
        for i, embed in enumerate(embeds):
            embed.set_footer(text=f"Page {i + 1} of {len(embeds)}")
        return embeds

    async def interaction_check(self, inter: disnake.Interaction) -> bool:
        if inter.user.id == self.owner.id:
            return True
        await inter.response.send_message("You are not the owner of this menu.", ephemeral=True)
        return False

    @disnake.ui.select(placeholder="Select Character", row=4, min_values=1, max_values=1)
    async def select_char(self, select: disnake.ui.Select, inter: disnake.MessageInteraction):
        await inter.response.defer()
        if len(select.values) == 1 and select.values[0] == TOO_MANY_CHARACTERS_SENTINEL:
            charname = await self._text_select_char(inter)
        else:
            charname = select.values[0]
        if charname is None:
            self.embed_count = 0
            await self.refresh_content(inter)
            return
        self.embeds = await self.construct_embeds(charname)
        if len(self.embeds) == 1:
            self.next_page.disabled = True
            self.last_page.disabled = True
            self.prev_page.disabled = True
            self.first_page.disabled = True
        else:
            self.next_page.disabled = False
            self.last_page.disabled = False
        self.firstchar = charname
        self._refresh_character_select()
        self.embed_count = 0
        await self.refresh_content(inter)


    def _refresh_character_select(self):
        self.select_char.options.clear()
        if len(self.charlist) > 25:
            self.select_char.add_option(
                label="Whoa, you have a lot of characters! Click here to select one.", value=TOO_MANY_CHARACTERS_SENTINEL
            )
            return
        for char in reversed(self.charlist):  # display highest-first
            selected = self.firstchar is not None and self.firstchar in char['character']
            self.select_char.add_option(label=char['character'], value=char['character'], default=selected)

    async def _text_select_char(self, inter: disnake.MessageInteraction) -> Optional[str]:
        self.select_char.disabled = True
        selectmsg: disnake.Message = await inter.followup.send(
            "Choose one of the following characters by sending a message to this channel.\n"+'\n'.join([x['character'] for x in self.charlist])
        )

        try:
            input_msg: disnake.Message = await self.bot.wait_for(
                "message",
                timeout=60,
                check=lambda msg: msg.author == inter.author and msg.channel.id == inter.channel_id,
            )
            with suppress(disnake.HTTPException):
                await input_msg.delete()
                await selectmsg.delete()

            charname=[]
            for x in self.charlist:
                if "".join(input_msg.content.split()).casefold() in "".join(x['character'].split()).casefold():
                    charname = x['character']

            if charname:
                await inter.followup.send(f"{charname} selected.", delete_after=4)
                return charname
            await inter.followup.send("No valid character found. Use the select menu to try again.", delete_after=6)
            return None
        except TimeoutError:
            await inter.followup.send("No valid character found. Use the select menu to try again.", delete_after=6)
            return
        finally:
            self.select_char.disabled = False

    @disnake.ui.button(emoji="⏪", style=disnake.ButtonStyle.blurple)
    async def first_page(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        self.embed_count = 0
        self.embeds[self.embed_count].set_footer(text=f"Page 1 of {len(self.embeds)}")

        self.first_page.disabled = True
        self.prev_page.disabled = True
        self.next_page.disabled = False
        self.last_page.disabled = False
        await self.refresh_content(inter)

    @disnake.ui.button(emoji="◀", style=disnake.ButtonStyle.secondary)
    async def prev_page(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        self.embed_count -= 1

        self.next_page.disabled = False
        self.last_page.disabled = False
        if self.embed_count == 0:
            self.first_page.disabled = True
            self.prev_page.disabled = True
        await self.refresh_content(inter)

    @disnake.ui.button(emoji="✖️", style=disnake.ButtonStyle.red)
    async def remove(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        if inter.response.is_done():
            await inter.edit_original_message("\u200B", embed=None, view=None)
        else:
            await inter.response.edit_message("\u200B", embed=None, view=None)
        await inter.delete_original_message()

    @disnake.ui.button(emoji="▶", style=disnake.ButtonStyle.secondary)
    async def next_page(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        self.embed_count += 1

        self.first_page.disabled = False
        self.prev_page.disabled = False
        if self.embed_count == len(self.embeds) - 1:
            self.next_page.disabled = True
            self.last_page.disabled = True
        await self.refresh_content(inter)

    @disnake.ui.button(emoji="⏩", style=disnake.ButtonStyle.blurple)
    async def last_page(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        self.embed_count = len(self.embeds) - 1

        self.first_page.disabled = False
        self.prev_page.disabled = False
        self.next_page.disabled = True
        self.last_page.disabled = True
        await self.refresh_content(inter)
