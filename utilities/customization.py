import asyncio
import io
import re
from utilities import checks
import disnake
from disnake.ext import commands
from disnake.ext.commands import BucketType, NoPrivateMessage
from utilities.functions import confirm, confirmInter

class Customization(commands.Cog):
	"""Commands to help streamline using the bot."""

	def __init__(self, bot):
		self.bot = bot

	@commands.command()
	@commands.guild_only()
	async def prefix(self, ctx, prefix: str = None):
		"""
		Sets the bot's prefix for this server.
		You must have Manage Server permissions or a role called "Bot Admin" to use this command. Due to a possible Discord conflict, a prefix beginning with `/` will require confirmation.
		Forgot the prefix? Reset it with "@Labyrinthian#1476 prefix '".
		"""
		guild_id = str(ctx.guild.id)
		if prefix is None:
			current_prefix = await self.bot.get_guild_prefix(ctx.guild)
			return await ctx.send(f"My current prefix is: `{current_prefix}`.")

		if not checks._role_or_permissions(ctx, lambda r: r.name.lower() == "bot admin", manage_guild=True):
			return await ctx.send("You do not have permissions to change the guild prefix.")

		# Check for Discord Slash-command conflict
		if prefix.startswith("/"):
			if not await confirm(
				ctx,
				"Setting a prefix that begins with / may cause issues. "
				"Are you sure you want to continue? (Reply with yes/no)",
			):
				return await ctx.send("Ok, cancelling.")
		else:
			if not await confirm(
				ctx,
				f"Are you sure you want to set my prefix to `{prefix}`? This will affect "
				f"everyone on this server! (Reply with yes/no)",
			):
				return await ctx.send("Ok, cancelling.")

		# insert into cache
		self.bot.prefixes[guild_id] = prefix

		# update db
		await self.bot.sdb.prefixes.update_one({"guild_id": guild_id}, {"$set": {"prefix": prefix}}, upsert=True)

		await ctx.send(f"Prefix set to `{prefix}` for this server.")

	@commands.slash_command(description="Sets the bot's prefix for this server.", checks=[commands.guild_only()])
	async def prefix(self, inter, prefix: str = None):
		"""
		Sets the bot's prefix for this server.
		You must have Manage Server permissions or a role called "Bot Admin" to use this command. Due to a possible Discord conflict, a prefix beginning with `/` will require confirmation.
		Forgot the prefix? Reset it with "@Labyrinthian#1476 prefix '".
		"""
		guild_id = str(inter.guild.id)
		if prefix is None:
			current_prefix = await self.bot.get_guild_prefix(inter.guild)
			return await inter.send(f"My current prefix is: `{current_prefix}`.")

		if not checks._role_or_permissions(inter, lambda r: r.name.lower() == "bot admin", manage_guild=True):
			return await inter.send("You do not have permissions to change the guild prefix.")

		# Check for Discord Slash-command conflict
		if prefix.startswith("/"):
			if not await confirmInter(
				inter,
				"Setting a prefix that begins with / may cause issues. "
				"Are you sure you want to continue? (Reply with yes/no)",
				delete_msgs=True
			):
				return await inter.send("Ok, cancelling.")
		else:
			if not await confirmInter(
				inter,
				f"Are you sure you want to set my prefix to `{prefix}`? This will affect "
				f"everyone on this server! (Reply with yes/no)",
				delete_msgs=True
			):
				return await inter.send("Ok, cancelling.")

		# insert into cache
		self.bot.prefixes[guild_id] = prefix

		# update db
		await self.bot.sdb.prefixes.update_one({"guild_id": guild_id}, {"$set": {"prefix": prefix}}, upsert=True)

		await inter.response.defer()

		await inter.edit_original_message(f"Prefix set to `{prefix}` for this server.")

def setup(bot):
    bot.add_cog(Customization(bot))