"""
Created on Oct 29, 2016
@author: andrew
"""
import asyncio
import re
from typing import Callable, TypeVar
from disnake.ext import commands
import disnake

from rapidfuzz import fuzz, process

from utils.models.errors import ExternalImportError

class timedeltaplus():
    def __init__(self,seconds:int=0,minutes:int=0,hours:int=0,days:int=0,weeks:int=0,months:int=0,years:int=0) -> None:
        secs=seconds
        secs+=minutes*60
        secs+=hours*3600
        secs+=days*86400
        secs+=weeks*604800
        secs+=months*2630000
        secs+=years*31556952
        self.years, remainder = divmod(secs, 31556952)
        self.months, remainder = divmod(remainder, 2630000)
        self.weeks, remainder = divmod(remainder, 604800)
        self.days, remainder = divmod(remainder, 86400)
        self.hours, remainder = divmod(remainder, 3600)
        self.minutes, self.seconds = divmod(remainder, 60)
        self.iter = (self.years,self.months,self.weeks,self.days,self.hours,self.minutes,self.seconds)
        self.timetab = ('Year', 'Month', 'Week', 'Day', 'Hour', 'Minute', 'Second')

    @property
    def fdict(self) -> dict:
        return {f"{x}{'s' if y > 1 or y < -1 else ''}": y for x,y in zip(self.timetab, self.iter) if y != 0}

    @property
    def dict(self) -> dict:
        return {x: y for x,y in zip(self.timetab, self.iter)}

    @property
    def ftup(self) -> tuple:
        return tuple(x for x in self.iter)

    def __str__(self) -> str:
        return ', '.join([f"{y} {x}{'s' if y > 1 or y < -1 else ''}" for x,y in zip(self.timetab, self.iter) if y != 0])


def get_positivity(string):
    if isinstance(string, bool):  # oi!
        return string
    lowered = string.lower()
    if lowered in ("yes", "y", "True", "t", "1", "enable", "on"):
        return True
    elif lowered in ("no", "n", "false", "f", "0", "disable", "off"):
        return False
    else:
        return None

# ==== search / select menus ====
_HaystackT = TypeVar("_HaystackT")

def search(
    list_to_search: list[_HaystackT], value: str, key: Callable[[_HaystackT], str], cutoff=5, strict=False
) -> tuple[_HaystackT | list[_HaystackT], bool]:
    """Fuzzy searches a list for an object
    result can be either an object or list of objects
    :param list_to_search: The list to search.
    :param value: The value to search for.
    :param key: A function defining what to search for.
    :param cutoff: The scorer cutoff value for fuzzy searching.
    :param strict: If True, will only search for exact matches.
    :returns: A two-tuple (result, strict)"""
    # there is nothing to search
    if len(list_to_search) == 0:
        return [], False

    # full match, return result
    exact_matches = [a for a in list_to_search if value.lower() == key(a).lower()]
    if not (exact_matches or strict):
        partial_matches = [a for a in list_to_search if value.lower() in key(a).lower()]
        if len(partial_matches) > 1 or not partial_matches:
            names = [key(d).lower() for d in list_to_search]
            fuzzy_map = {key(d).lower(): d for d in list_to_search}
            fuzzy_results = [r for r in process.extract(value.lower(), names, scorer=fuzz.ratio) if r[1] >= cutoff]
            fuzzy_sum = sum(r[1] for r in fuzzy_results)
            fuzzy_matches_and_confidences = [(fuzzy_map[r[0]], r[1] / fuzzy_sum) for r in fuzzy_results]

            # display the results in order of confidence
            weighted_results = []
            weighted_results.extend((match, confidence) for match, confidence in fuzzy_matches_and_confidences)
            weighted_results.extend((match, len(value) / len(key(match))) for match in partial_matches)
            sorted_weighted = sorted(weighted_results, key=lambda e: e[1], reverse=True)

            # build results list, unique
            results = []
            for r in sorted_weighted:
                if r[0] not in results:
                    results.append(r[0])
        else:
            results = partial_matches
    else:
        results = exact_matches

    if len(results) > 1:
        return results, False
    elif not results:
        return [], False
    else:
        return results[0], True

async def confirm(ctx: commands.Context, message: disnake.Message, delete_msgs=False, response_check=get_positivity):
    """
    Confirms whether a user wants to take an action.
    :rtype: bool|None
    :param ctx: The current Context.
    :param message: The message for the user to confirm.
    :param delete_msgs: Whether to delete the messages.
    :param response_check: A function (str) -> bool that returns whether a given reply is a valid response.
    :type response_check: (str) -> bool
    :return: Whether the user confirmed or not. None if no reply was recieved
    """
    msg: disnake.Message = await ctx.channel.send(message)
    try:
        reply: disnake.Message = await ctx.bot.wait_for("message", timeout=30, check=auth_and_chan(ctx))
    except asyncio.TimeoutError:
        return None
    reply_bool = response_check(reply.content) if reply is not None else None
    if delete_msgs:
        try:
            await msg.delete()
            await reply.delete()
        except:
            pass
    return reply_bool

def natural_join(things, between: str):
    if len(things) < 3:
        return f" {between} ".join(things)
    first_part = ", ".join(things[:-1])
    return f"{first_part}, {between} {things[-1]}"

async def confirmInter(inter: disnake.Interaction, message, delete_msgs=False, response_check=get_positivity):
    """
    Confirms whether a user wants to take an action.
    :rtype: bool|None
    :param ctx: The current Context.
    :param message: The message for the user to confirm.
    :param delete_msgs: Whether to delete the messages.
    :param response_check: A function (str) -> bool that returns whether a given reply is a valid response.
    :type response_check: (str) -> bool
    :return: Whether the user confirmed or not. None if no reply was recieved
    """
    msg = await inter.channel.send(message)
    try:
        reply = await inter.bot.wait_for("message", timeout=30, check=auth_and_chan(inter))
    except asyncio.TimeoutError:
        return None
    reply_bool = response_check(reply.content) if reply is not None else None
    if delete_msgs:
        try:
            await msg.delete()
            await reply.delete()
        except:
            pass
    return reply_bool

# ==== misc helpers ====
def auth_and_chan(ctx: commands.Context):
    """Message check: same author and channel"""

    def chk(msg: disnake.Message):
        return msg.author == ctx.author and msg.channel == ctx.channel

    return chk

URL_KEY_V1_RE = re.compile(r"key=([^&#]+)")
URL_KEY_V2_RE = re.compile(r"/spreadsheets/d/([a-zA-Z0-9-_]+)")

def extract_gsheet_id_from_url(url: str):
    m2 = URL_KEY_V2_RE.search(url)
    if m2:
        return url
    m1 = URL_KEY_V1_RE.search(url)
    if m1:
        return url
    raise ExternalImportError("This is not a valid Google Sheets link.")