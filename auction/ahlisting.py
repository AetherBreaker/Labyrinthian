from typing import TYPE_CHECKING, TypeVar
import disnake
from disnake.ext import commands

_LabyrinthianT = TypeVar("_LabyrinthianT", bound=disnake.Client)
if TYPE_CHECKING:
    from bot import Labyrinthian

    _LabyrinthianT = Labyrinthian

class ListingView(disnake.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)


