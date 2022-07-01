"""
Created on Oct 29, 2016
@author: andrew
"""
import asyncio
from contextlib import suppress
import math
import random
import re
from typing import Any, Callable, List, TypeVar, Optional, Union
from disnake.ext import commands
import disnake
import emoji
import inflect

from rapidfuzz import fuzz, process

from utils.models.errors import (
    ExternalImportError,
    NoSelectionElements,
    SelectionCancelled,
)


class timedeltaplus:
    def __init__(
        self,
        seconds: int = 0,
        minutes: int = 0,
        hours: int = 0,
        days: int = 0,
        weeks: int = 0,
        months: int = 0,
        years: int = 0,
    ) -> None:
        secs = seconds
        secs += minutes * 60
        secs += hours * 3600
        secs += days * 86400
        secs += weeks * 604800
        secs += months * 2630000
        secs += years * 31556952
        self.years, remainder = divmod(secs, 31556952)
        self.months, remainder = divmod(remainder, 2630000)
        self.weeks, remainder = divmod(remainder, 604800)
        self.days, remainder = divmod(remainder, 86400)
        self.hours, remainder = divmod(remainder, 3600)
        self.minutes, self.seconds = divmod(remainder, 60)
        self.iter = (
            self.years,
            self.months,
            self.weeks,
            self.days,
            self.hours,
            self.minutes,
            self.seconds,
        )
        self.timetab = ("Year", "Month", "Week", "Day", "Hour", "Minute", "Second")

    @property
    def fdict(self) -> dict:
        return {
            f"{x}{'s' if y > 1 or y < -1 else ''}": y
            for x, y in zip(self.timetab, self.iter)
            if y != 0
        }

    @property
    def dict(self) -> dict:
        return {x: y for x, y in zip(self.timetab, self.iter)}

    @property
    def ftup(self) -> tuple:
        return tuple(x for x in self.iter)

    def __str__(self) -> str:
        return ", ".join(
            [
                f"{y} {x}{'s' if y > 1 or y < -1 else ''}"
                for x, y in zip(self.timetab, self.iter)
                if y != 0
            ]
        )

    @property
    def intstr(self):
        return ", ".join(
            [
                f"{y} {x}{'s' if y > 1 or y < -1 else ''}"
                for x, y in zip(self.timetab, self.iter)
                if y != 0
            ]
        )


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
    list_to_search: list[_HaystackT],
    value: str,
    key: Callable[[_HaystackT], str],
    cutoff=5,
    strict=False,
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
            fuzzy_results = [
                r
                for r in process.extract(value.lower(), names, scorer=fuzz.ratio)
                if r[1] >= cutoff
            ]
            fuzzy_sum = sum(r[1] for r in fuzzy_results)
            fuzzy_matches_and_confidences = [
                (fuzzy_map[r[0]], r[1] / fuzzy_sum) for r in fuzzy_results
            ]

            # display the results in order of confidence
            weighted_results = []
            weighted_results.extend(
                (match, confidence)
                for match, confidence in fuzzy_matches_and_confidences
            )
            weighted_results.extend(
                (match, len(value) / len(key(match))) for match in partial_matches
            )
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


async def confirm(
    ctx: commands.Context,
    message: disnake.Message,
    delete_msgs=False,
    response_check=get_positivity,
):
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
    msg: disnake.Message = await ctx.channel.send(message)  # type: ignore
    try:
        reply: disnake.Message = await ctx.bot.wait_for(
            "message", timeout=30, check=auth_and_chan(ctx)
        )
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


async def confirmInter(
    inter: disnake.Interaction,
    message,
    delete_msgs=False,
    response_check=get_positivity,
):
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
        reply = await inter.bot.wait_for(
            "message", timeout=30, check=auth_and_chan(inter)
        )
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
def auth_and_chan(ctx: Union[commands.Context, disnake.Interaction]):
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


T = TypeVar("T")


def truncate_list(input: List[T], cutoff: int, repl: Optional[T] = None) -> List[T]:
    return input[:cutoff] if repl is None else input[:cutoff] + [repl]


def simple_tabulate_str(input: List[str], columnamt: int = 2) -> str:
    length = int(math.ceil(len(input) / columnamt))
    input = list(input)
    columns = [
        input[x * length : (x + 1) * length] for x, y in enumerate(range(columnamt))
    ]
    while len(columns[0]) > len(columns[-1]):
        columns[-1].append("")
    colmaxes = [max(len(y) for y in x) for x in columns]
    joinlist = []
    for lineindex, line in enumerate(range(length)):
        linejoin = []
        for columnindex, column in enumerate(columns):
            if columnindex == 0:
                linejoin.append(f"{column[0]:{colmaxes[columnindex]}}")
            elif (columnindex + 1) == len(columns):
                linejoin.append(f"{column[0]:>{colmaxes[columnindex]}}")
            else:
                linejoin.append(f"{column[0]:^{colmaxes[columnindex]}}")
            columns[columnindex] = column[1:]
        joinlist.append(" | ".join(linejoin))
    return "\n".join(joinlist)


def has_unicode_emote(text: str) -> bool:
    for character in text:
        if character in emoji.UNICODE_EMOJI_ENGLISH:
            return True
    return False


def paginate(choices: list[_HaystackT], per_page: int) -> list[list[_HaystackT]]:
    out = []
    for start_idx in range(0, len(choices), per_page):
        out.append(choices[start_idx : start_idx + per_page])
    return out


async def try_delete(message):
    try:
        await message.delete()
    except disnake.HTTPException:
        pass


async def get_selection(
    inter: disnake.Interaction,
    choices: list[_HaystackT],
    key: Callable[[_HaystackT], str],
    delete=True,
    pm=False,
    message=None,
    force_select=False,
):
    """Returns the selected choice, or raises an error.
    If delete is True, will delete the selection message and the response.
    If length of choices is 1, will return the only choice unless force_select is True.
    :raises NoSelectionElements: if len(choices) is 0.
    :raises SelectionCancelled: if selection is cancelled."""
    if len(choices) == 0:
        raise NoSelectionElements()
    elif len(choices) == 1 and not force_select:
        return choices[0]

    page = 0
    pages = paginate(choices, 10)
    m = None
    select_msg = None

    def chk(msg: disnake.Message):
        content = msg.content.lower()
        valid = content in ("c", "n", "p")
        try:
            valid = valid or (1 <= int(content) <= len(choices))
        except ValueError:
            pass
        return msg.author == inter.author and msg.channel == inter.channel and valid

    for n in range(200):
        _choices = pages[page]
        names = [key(o) for o in _choices]
        embed = disnake.Embed()
        embed.title = "Multiple Matches Found"
        select_str = (
            "Which one were you looking for? (Type the number or `c` to cancel)\n"
        )
        if len(pages) > 1:
            select_str += "`n` to go to the next page, or `p` for previous\n"
            embed.set_footer(text=f"Page {page + 1}/{len(pages)}")
        for i, r in enumerate(names):
            select_str += f"**[{i + 1 + page * 10}]** - {r}\n"
        embed.description = select_str
        embed.colour = random.randint(0, 0xFFFFFF)
        if message:
            embed.add_field(name="Note", value=message, inline=False)
        if select_msg:
            await try_delete(select_msg)
        if not pm:
            select_msg = await inter.channel.send(embed=embed)
        else:
            embed.add_field(
                name="Instructions",
                value=(
                    "Type your response in the channel you called the command. This message was PMed to "
                    "you to hide the monster name."
                ),
                inline=False,
            )
            select_msg = await inter.author.send(embed=embed)

        try:
            m: disnake.Message = await inter.bot.wait_for(
                "message", timeout=30, check=chk
            )
        except asyncio.TimeoutError:
            m = None

        if m is None:
            break
        if m.content.lower() == "n":
            if page + 1 < len(pages):
                page += 1
            else:
                await inter.channel.send("You are already on the last page.")
        elif m.content.lower() == "p":
            if page - 1 >= 0:
                page -= 1
            else:
                await inter.channel.send("You are already on the first page.")
        else:
            break

    if delete and not pm:
        with suppress(disnake.HTTPException):
            await select_msg.delete()
            if m is not None:
                await m.delete()
    if m is None or m.content.lower() == "c":
        raise SelectionCancelled()
    idx = int(m.content) - 1
    return choices[idx]


async def search_and_select(
    inter: disnake.Interaction,
    list_to_search: list[_HaystackT],
    query: str,
    key: Callable[[_HaystackT], str],
    cutoff=5,
    pm=False,
    message=None,
    list_filter=None,
    selectkey=None,
    return_metadata=False,
    strip_query_quotes=True,
    selector=get_selection,
) -> _HaystackT:
    """
    Searches a list for an object matching the key, and prompts user to select on multiple matches.
    Guaranteed to return a result - raises if there is no result.
    :param inter: The context of the search.
    :param list_to_search: The list of objects to search.
    :param query: The value to search for.
    :param key: How to search - compares key(obj) to value
    :param cutoff: The cutoff percentage of fuzzy searches.
    :param pm: Whether to PM the user the select prompt.
    :param message: A message to add to the select prompt.
    :param list_filter: A filter to filter the list to search by.
    :param selectkey: If supplied, each option will display as selectkey(opt) in the select prompt.
    :param return_metadata: Whether to return a metadata object {num_options, chosen_index}.
    :param strip_query_quotes: Whether to strip quotes from the query.
    :param selector: The coroutine to use to select a result if multiple results are possible.
    """
    if list_filter:
        list_to_search = list(filter(list_filter, list_to_search))

    if strip_query_quotes:
        query = query.strip("\"'")

    result = search(list_to_search, query, key, cutoff)

    if result is None:
        raise NoSelectionElements("No matches found.")
    results, strict = result

    if strict:
        result = results
    else:
        if len(results) == 0:
            raise NoSelectionElements()

        first_result = results[0]
        confidence = fuzz.partial_ratio(key(first_result).lower(), query.lower())
        if len(results) == 1 and confidence > 75:
            result = first_result
        else:
            result = await selector(
                inter,
                results,
                key=selectkey or key,
                pm=pm,
                message=message,
                force_select=True,
            )
    if not return_metadata:
        return result
    metadata = {
        "num_options": 1 if strict else len(results),
        "chosen_index": 0 if strict else results.index(result),
    }
    return result, metadata
