import disnake
from disnake.ext import commands

class ListingView(disnake.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

