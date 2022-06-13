import re
import disnake.utils

from utilities import config
from utilities.errors import ExternalImportError
from utilities.functions import extract_gsheet_id_from_url

DDB_URL_RE = re.compile(r"(?:https?://)?(?:www\.dndbeyond\.com|ddb\.ac)(?:/profile/.+)?/characters/(\d+)/?")
DICECLOUD_URL_RE = re.compile(r"(?:https?://)?dicecloud\.com/character/([\d\w]+)/?")

def author_is_owner(ctx):
    return ctx.author.id == config.OWNER_ID

def _check_permissions(ctx, perms):
    if author_is_owner(ctx):
        return True

    ch = ctx.channel
    author = ctx.author
    try:
        resolved = ch.permissions_for(author)
    except AttributeError:
        resolved = None
    return all(getattr(resolved, name, None) == value for name, value in perms.items())

def _role_or_permissions(ctx, role_filter, **perms):
    if _check_permissions(ctx, perms):
        return True

    ch = ctx.message.channel
    author = ctx.message.author
    if isinstance(ch, disnake.abc.PrivateChannel):
        return False  # can't have roles in PMs

    try:
        role = disnake.utils.find(role_filter, author.roles)
    except:
        return False
    return role is not None

def urlCheck(url: str) -> bool:
    # Sheets in order: DDB, Dicecloud, Gsheet
    if DDB_URL_RE.match(url):
        return True
    elif DICECLOUD_URL_RE.match(url):
        return True
    else:
        try:
            url = extract_gsheet_id_from_url(url)
        except ExternalImportError:
            return False
        return True