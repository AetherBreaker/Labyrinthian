from typing import TYPE_CHECKING, Dict, List, NewType, Any
import typing

from bson import ObjectId
from pydantic import BaseModel

from utils.models import LabyrinthianBaseModel


if TYPE_CHECKING:
    ObjID = ObjectId
    from bot import Labyrinthian
else:
    ObjID = Any


UserID = NewType("UserID", str)
GuildID = NewType("GuildID", str)
CharacterName = NewType("CharacterName", str)


class ActiveCharacter(LabyrinthianBaseModel):
    name: CharacterName
    id: ObjID


class UserPreferences(LabyrinthianBaseModel):
    user: UserID
    activechar: Dict[GuildID, ActiveCharacter] = {}
    characters: Dict[GuildID, Dict[CharacterName, ObjID]] = {}
    autoswap: bool = True

    # ==== lifecycle ====
    @staticmethod
    async def get_data(bot: "Labyrinthian", user: UserID):
        data = await bot.dbcache.find_one("userprefs", {"user": user})
        wasnone = False
        if data is None:
            wasnone = True
            data = {"user": user}
        return (data, wasnone)

    async def commit(self, db):
        """Commits the settings to the database."""
        data = self.dict()
        await db.update_one(
            "userprefs", {"user": self.user}, {"$set": data}, upsert=True
        )
