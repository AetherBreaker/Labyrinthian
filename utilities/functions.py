"""
Created on Oct 29, 2016
@author: andrew
"""
import asyncio
import logging
import random
import re
from contextlib import suppress
from typing import Callable, TYPE_CHECKING, TypeVar

import disnake
from rapidfuzz import fuzz, process

from utilities.errors import NoSelectionElements, SelectionCancelle

log = logging.getLogger(__name__)
sentinel = object()


def list_get(index, default, l):
    try:
        a = l[index]
    except IndexError:
        a = default
    return a


def get_positivity(string):
    if isinstance(string, bool):  # oi!
        return string
    lowered = string.lower()
    if lowered in ("yes", "y", "true", "t", "1", "enable", "on"):
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


def paginate(choices: list[_HaystackT], per_page: int) -> list[list[_HaystackT]]:
    out = []
    for start_idx in range(0, len(choices), per_page):
        out.append(choices[start_idx : start_idx + per_page])
    return out


async def get_selection(
    ctx,
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

    def chk(msg):
        content = msg.content.lower()
        valid = content in ("c", "n", "p")
        try:
            valid = valid or (1 <= int(content) <= (len(choices) + 1))
        except ValueError:
            pass
        return msg.author == ctx.author and msg.channel == ctx.channel and valid

    for n in range(200):
        _choices = pages[page]
        names = [key(o) for o in _choices]
        embed = disnake.Embed()
        embed.title = "Multiple Matches Found"
        select_str = "Which one were you looking for? (Type the number or `c` to cancel)\n"
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
            select_msg = await ctx.channel.send(embed=embed)
        else:
            embed.add_field(
                name="Instructions",
                value="Type your response in the channel you called the command. This message was PMed to "
                "you to hide the monster name.",
                inline=False,
            )
            select_msg = await ctx.author.send(embed=embed)

        try:
            m = await ctx.bot.wait_for("message", timeout=30, check=chk)
        except asyncio.TimeoutError:
            m = None

        if m is None:
            break
        if m.content.lower() == "n":
            if page + 1 < len(pages):
                page += 1
            else:
                await ctx.channel.send("You are already on the last page.")
        elif m.content.lower() == "p":
            if page - 1 >= 0:
                page -= 1
            else:
                await ctx.channel.send("You are already on the first page.")
        else:
            break

    if delete and not pm:
        with suppress(disnake.HTTPException):
            await select_msg.delete()
            if m is not None:
                await m.delete()
    if m is None or m.content.lower() == "c":
        raise SelectionCancelled()
    return choices[int(m.content) - 1]


async def search_and_select(
    ctx: "AvraeContext",
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
    :param ctx: The context of the search.
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
            result = await selector(ctx, results, key=selectkey or key, pm=pm, message=message, force_select=True)
    if not return_metadata:
        return result
    metadata = {"num_options": 1 if strict else len(results), "chosen_index": 0 if strict else results.index(result)}
    return result, metadata


async def confirm(ctx, message, delete_msgs=False, response_check=get_positivity):
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
    msg = await ctx.channel.send(message)
    try:
        reply = await ctx.bot.wait_for("message", timeout=30, check=auth_and_chan(ctx))
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


# ==== display helpers ====
def a_or_an(string, upper=False):
    if string.startswith("^") or string.endswith("^"):
        return string.strip("^")
    if re.match("[AEIOUaeiou].*", string):
        return "an {0}".format(string) if not upper else f"An {string}"
    return "a {0}".format(string) if not upper else f"A {string}"


# ==== misc helpers ====
def auth_and_chan(ctx):
    """Message check: same author and channel"""

    def chk(msg):
        return msg.author == ctx.author and msg.channel == ctx.channel

    return chk


async def try_delete(message):
    try:
        await message.delete()
    except disnake.HTTPException:
        pass

# ==== user stuff ====
async def user_from_id(ctx, the_id):
    """
    Gets a :class:`disnake.User` given their user id in the context. Returns member if context has data.
    :type ctx: disnake.ext.commands.Context
    :type the_id: int
    :rtype: disnake.User
    """

    async def update_known_user(the_user):
        avatar_hash = the_user.avatar.key if the_user.avatar is not None else None
        await ctx.bot.mdb.users.update_one(
            {"id": str(the_user.id)},
            {
                "$set": {
                    "username": the_user.name,
                    "discriminator": the_user.discriminator,
                    "avatar": avatar_hash,
                    "bot": the_user.bot,
                }
            },
            upsert=True,
        )

    if ctx.guild:  # try and get member
        member = ctx.guild.get_member(the_id)
        if member is not None:
            await update_known_user(member)
            return member

    # try and see if user is in bot cache
    user = ctx.bot.get_user(the_id)
    if user is not None:
        await update_known_user(user)
        return user

    # or maybe the user is in our known user db
    user_doc = await ctx.bot.mdb.users.find_one({"id": str(the_id)})
    if user_doc is not None:
        # noinspection PyProtectedMember
        # technically we're not supposed to create User objects like this
        # but it *should* be fine
        return disnake.User(state=ctx.bot._connection, data=user_doc)

    # fetch the user from the disnake API
    try:
        fetched_user = await ctx.bot.fetch_user(the_id)
    except disnake.NotFound:
        return None

    await update_known_user(fetched_user)
    return fetched_user


async def get_guild_member(guild, member_id):
    """Gets and caches a specific guild member."""
    if guild is None:
        return None
    if (member := guild.get_member(member_id)) is not None:
        return member
    result = await guild.query_members(user_ids=[member_id], limit=1, cache=True)
    if result:
        return result[0]
    return None