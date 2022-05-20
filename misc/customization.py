import asyncio
import io
import re

import discord
from discord.ext import commands
from discord.ext.commands import BucketType, NoPrivateMessage

class Customization(commands.Cog):
	"""Commands to help streamline using the bot."""

	def __init__(self, bot):
		self.bot = bot

	#@commands.Cog.listener()
	#async def on_ready(self):
	#	if self.bot.is_cluster_0:
	#		cmds = list(self.bot.all_commands.keys())
	#		await self.bot.rdb.jset("default_commands", cmds)

	@commands.command()
	@commands.guild_only()
	async def prefix(self, ctx, prefix: str = None):
		"""
		Sets the bot's prefix for this server.
		You must have Manage Server permissions or a role called "Bot Admin" to use this command. Due to a possible Discord conflict, a prefix beginning with `/` will require confirmation.
		Forgot the prefix? Reset it with "@Avrae#6944 prefix !".
		"""
		guild_id = str(ctx.guild.id)
		if prefix is None:
			current_prefix = await self.bot.get_guild_prefix(ctx.guild)
			return await ctx.send(
				f"My current prefix is: `{current_prefix}`. You can run commands like "
				f"`{current_prefix}roll 1d20` or by mentioning me!"
			)

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
		await self.bot.mdb.prefixes.update_one({"guild_id": guild_id}, {"$set": {"prefix": prefix}}, upsert=True)

		await ctx.send(f"Prefix set to `{prefix}` for this server. Use commands like `{prefix}roll` now!")

	@commands.slash_command(description="Sets the bot's prefix for this server.", checks=[guild_only()])
	async def prefix(self, inter, prefix: str = None):
		"""
		Sets the bot's prefix for this server.
		You must have Manage Server permissions or a role called "Bot Admin" to use this command. Due to a possible Discord conflict, a prefix beginning with `/` will require confirmation.
		Forgot the prefix? Reset it with "@Avrae#6944 prefix !".
		"""
		guild_id = str(inter.guild.id)
		if prefix is None:
			current_prefix = await self.bot.get_guild_prefix(inter.guild)
			return await inter.send(
				f"My current prefix is: `{current_prefix}`. You can run commands like "
				f"`{current_prefix}roll 1d20` or by mentioning me!"
			)

		if not checks._role_or_permissions(inter, lambda r: r.name.lower() == "bot admin", manage_guild=True):
			return await inter.send("You do not have permissions to change the guild prefix.")

		# Check for Discord Slash-command conflict
		if prefix.startswith("/"):
			if not await confirm(
				inter,
				"Setting a prefix that begins with / may cause issues. "
				"Are you sure you want to continue? (Reply with yes/no)",
			):
				return await inter.send("Ok, cancelling.")
		else:
			if not await confirm(
				inter,
				f"Are you sure you want to set my prefix to `{prefix}`? This will affect "
				f"everyone on this server! (Reply with yes/no)",
			):
				return await inter.send("Ok, cancelling.")

		# insert into cache
		self.bot.prefixes[guild_id] = prefix

		# update db
		await self.bot.mdb.prefixes.update_one({"guild_id": guild_id}, {"$set": {"prefix": prefix}}, upsert=True)

		await inter.send(f"Prefix set to `{prefix}` for this server. Use commands like `{prefix}roll` now!")

def setup(bot):
    bot.add_cog(Customization(bot))