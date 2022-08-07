from typing import TYPE_CHECKING

import disnake
from disnake.ext import commands

if TYPE_CHECKING:
    from bot import Labyrinthian


class UserPreferencesCog(commands.Cog):
    def __init__(self, bot: "Labyrinthian"):
        self.bot = bot


def setup(bot: "Labyrinthian"):
    bot.add_cog(UserPreferencesCog(bot))
