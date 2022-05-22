import disnake.utils
from disnake.ext import commands

from utilities import config


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


# ===== checks =====
def is_owner():
    def predicate(ctx):
        if author_is_owner(ctx):
            return True
        raise commands.CheckFailure("Only the bot owner may run this command.")

    return commands.check(predicate)


def role_or_permissions(role_name, **perms):
    def predicate(ctx):
        if _role_or_permissions(ctx, lambda r: r.name.lower() == role_name.lower(), **perms):
            return True
        raise commands.CheckFailure(
            f"You require a role named {role_name} or these permissions to run this command: {', '.join(perms)}"
        )

    return commands.check(predicate)


def admin_or_permissions(**perms):
    def predicate(ctx):
        admin_role = "Bot Admin"
        if _role_or_permissions(ctx, lambda r: r.name.lower() == admin_role.lower(), **perms):
            return True
        raise commands.CheckFailure(
            f"You require a role named Bot Admin or these permissions to run this command: {', '.join(perms)}"
        )

    return commands.check(predicate)


BREWER_ROLES = ("server brewer", "dragonspeaker")


#def feature_flag(flag_name, use_ddb_user=False, default=False):
#    async def predicate(ctx):
#        if use_ddb_user:
#            ddb_user = await ctx.bot.ddb.get_ddb_user(ctx, ctx.author.id)
#            if ddb_user is None:
#                user = {"key": str(ctx.author.id), "anonymous": True}
#            else:
#                user = ddb_user.to_ld_dict()
#        else:
#            user = disnake_user_to_dict(ctx.author)

#        flag_on = await ctx.bot.ldclient.variation(flag_name, user, default)
#        if flag_on:
#            return True

#        raise commands.CheckFailure("This command is currently disabled. Check back later!")

#    return commands.check(predicate)


#def user_permissions(*permissions: str):
#    """The user must have all of the specified permissions granted by `!admin set_user_permissions`"""

#    async def predicate(ctx):
#        user_p = await ctx.bot.mdb.user_permissions.find_one({"id": str(ctx.author.id)})
#        if all(user_p.get(p) for p in permissions):
#            return True
#        raise commands.CheckFailure(f"This command requires the {natural_join(permissions, 'and')} permissions.")

#    return commands.check(predicate)