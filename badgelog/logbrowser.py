import disnake
from disnake.ext import commands
from asyncio import TimeoutError
from contextlib import suppress
from copy import deepcopy
from typing import Dict, List, Optional
from bson import ObjectId
from pymongo import DESCENDING
import asyncio

TOO_MANY_CHARACTERS_SENTINEL = "__special:too_many_characters"


async def create_LogBrowser(inter: disnake.ApplicationCommandInteraction, bot: commands.Bot, owner: disnake.User, guild: disnake.Guild, charname: str, charlist: List):
    Log = LogBrowser(inter, bot, owner, guild, charname, charlist)
    await Log._init()
    return Log

class LogBrowser(disnake.ui.View):
    def __init__(self, inter: disnake.ApplicationCommandInteraction, bot: commands.Bot, owner: disnake.User, guild: disnake.Guild, charname: str, charlist: List):
        super().__init__(timeout=180)

        self.owner = owner
        self.guild = guild
        self.bot = bot
        self.firstchar = charname
        self.charlist = charlist
        self.inter = inter

        self.first_page.disabled = True
        self.prev_page.disabled = True


    async def _init(self):
        self.embeds = await self.construct_embeds(self.firstchar)
        if len(self.embeds) == 1:
            self.next_page.disabled = True
            self.last_page.disabled = True
        else:
            self.next_page.disabled = False
            self.last_page.disabled = False
        self.embed_count = 0
        self._refresh_character_select()
        await self.refresh_msg(self.inter)

    async def refresh_msg(self, inter: disnake.ApplicationCommandInteraction):
        await inter.edit_original_message("", embed=self.embeds[0], view=self)

    async def construct_embeds(self, charname: str) -> List[disnake.Embed]:
        char = await self.bot.sdb[f'BLCharList_{self.guild.id}'].find_one({"user": str(self.owner.id), "character": charname})
        badgelog = await self.bot.sdb[f"BadgeLogMaster_{self.guild.id}"].find({"charRefId": ObjectId(char['_id']), "user": str(self.owner.id)}).sort("timestamp", DESCENDING).to_list(None)
        embeds = []
        pageindex = 0
        Embednolog = {
            "title": f"{charname}'s Info'",
            "description": f"Played by: <@{self.owner.id}>",
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
            while badgelog:
                pageindex += 1
                Embed = deepcopy(Embednolog)
                logstr = []
                while badgelog:
                    Embed['fields'][3]['value'] = ""
                    if badgelog[0]['badges added'] < 0:
                        isneg = True
                    else:
                        isneg = False
                    logstr.append(f"{'' if char['user'] == badgelog[0]['user'] else '<@'+badgelog[0]['user']+'> at'} <t:{badgelog[0]['timestamp']}:f>\n`{badgelog[0]['character']} {'lost badges' if isneg else 'was awarded'} {badgelog[0]['previous badges']}({'' if isneg else '+'}{badgelog[0]['badges added']}) {'to' if isneg else 'by'}` <@{badgelog[0]['awarding DM']}>")
                    badgelog.pop(0)
                    Embed['fields'][3]['value'] = '\n\n'.join(logstr)
                    result = disnake.Embed.from_dict(Embed)
                    if len(result) >= 6000 or len(Embed['fields'][3]['value']) >= 512 or not len(badgelog) > 0:
                        if len(logstr) > 1:
                            logstr = logstr[:-1]
                        break
                Embed['fields'][3]['value'] = ""
                Embed['fields'][3]['value'] = '\n\n'.join(logstr)
                print(Embed)
                embeds.append(disnake.Embed.from_dict(Embed))
        else:
            embeds.append(disnake.Embed.from_dict(Embednolog))
        for i, embed in enumerate(embeds):
            embed.set_footer(text=f"Page {i + 1} of {len(embeds)}")
        return embeds

    async def interaction_check(self, interaction: disnake.Interaction) -> bool:
        if interaction.user.id == self.owner.id:
            return True
        await interaction.response.send_message("You are not the owner of this menu.", ephemeral=True)
        return False

    @disnake.ui.select(placeholder="Character", row=4, min_values=1, max_values=1)
    async def select_character(self, select: disnake.ui.Select, interaction: disnake.Interaction):
        if len(select.values) == 1 and select.values[0] == TOO_MANY_CHARACTERS_SENTINEL:
            charname = await self._text_select_character(interaction)
        else:
            charname = select.values[0]
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
        await interaction.edit_original_message(embed=self.embeds[0], view=self)

    def _refresh_character_select(self):
        self.select_character.options.clear()
        if len(self.charlist) > 25:
            self.select_character.add_option(
                label="Whoa, you have a lot of characters! Click here to select one.", value=TOO_MANY_CHARACTERS_SENTINEL
            )
            return
        for char in reversed(self.charlist):  # display highest-first
            selected = self.firstchar is not None and self.firstchar in char['character']
            self.select_character.add_option(label=char['character'], value=char['character'], default=selected)

    async def _text_select_character(self, interaction: disnake.Interaction) -> Optional[str]:
        self.select_character.disabled = True
        await interaction.send(
            "Choose a character by sending a message to this channel.",
            ephemeral=True,
        )

        try:
            input_msg: disnake.Message = await self.bot.wait_for(
                "message",
                timeout=60,
                check=lambda msg: msg.author == interaction.author and msg.channel.id == interaction.channel_id,
            )
            with suppress(disnake.HTTPException):
                await input_msg.delete()

            for x in self.charlist:
                if "".join(input_msg.split()).casefold() == "".join(x['character'].split()).casefold():
                    charname = x

            if charname:
                await interaction.send("Character selected.", ephemeral=True)
                return charname
            await interaction.send("No valid character found. Use the select menu to try again.", ephemeral=True)
            return 
        except TimeoutError:
            await interaction.send("No valid character found. Use the select menu to try again.", ephemeral=True)
            return
        finally:
            self.select_character.disabled = False

    @disnake.ui.button(emoji="⏪", style=disnake.ButtonStyle.blurple)
    async def first_page(self, button: disnake.ui.Button, interaction: disnake.MessageInteraction):
        self.embed_count = 0
        embed = self.embeds[self.embed_count]
        embed.set_footer(text=f"Page 1 of {len(self.embeds)}")

        self.first_page.disabled = True
        self.prev_page.disabled = True
        self.next_page.disabled = False
        self.last_page.disabled = False
        await interaction.edit_original_message(embed=embed, view=self)

    @disnake.ui.button(emoji="◀", style=disnake.ButtonStyle.secondary)
    async def prev_page(self, button: disnake.ui.Button, interaction: disnake.MessageInteraction):
        self.embed_count -= 1
        embed = self.embeds[self.embed_count]

        self.next_page.disabled = False
        self.last_page.disabled = False
        if self.embed_count == 0:
            self.first_page.disabled = True
            self.prev_page.disabled = True
        await interaction.edit_original_message(embed=embed, view=self)

    @disnake.ui.button(emoji="✖️", style=disnake.ButtonStyle.red)
    async def remove(self, button: disnake.ui.Button, interaction: disnake.MessageInteraction):
        await interaction.edit_original_message(view=None)

    @disnake.ui.button(emoji="▶", style=disnake.ButtonStyle.secondary)
    async def next_page(self, button: disnake.ui.Button, interaction: disnake.MessageInteraction):
        self.embed_count += 1
        embed = self.embeds[self.embed_count]

        self.first_page.disabled = False
        self.prev_page.disabled = False
        if self.embed_count == len(self.embeds) - 1:
            self.next_page.disabled = True
            self.last_page.disabled = True
        await interaction.edit_original_message(embed=embed, view=self)

    @disnake.ui.button(emoji="⏩", style=disnake.ButtonStyle.blurple)
    async def last_page(self, button: disnake.ui.Button, interaction: disnake.MessageInteraction):
        self.embed_count = len(self.embeds) - 1
        embed = self.embeds[self.embed_count]

        self.first_page.disabled = False
        self.prev_page.disabled = False
        self.next_page.disabled = True
        self.last_page.disabled = True
        await interaction.edit_original_message(embed=embed, view=self)




