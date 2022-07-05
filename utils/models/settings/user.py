from typing import TYPE_CHECKING, Dict, NewType, Any

from bson import ObjectId
from utils.models.settings import SettingsBaseModel


if TYPE_CHECKING:
    ObjID = ObjectId
else:
    ObjID = Any


UserID = NewType("UserID", str)
GuildID = NewType("GuildID", str)
CharacterName = NewType("CharacterName", str)


class ActiveCharacter(SettingsBaseModel):
    name: CharacterName
    id: ObjID


class UserPreferences(SettingsBaseModel):
    user: UserID
    activechar: Dict[GuildID, ActiveCharacter] = {}
    characters: Dict[GuildID, Dict[CharacterName, ObjID]] = {}
    autoswap: bool = True

    # ==== lifecycle ====
    @classmethod
    async def for_user(cls, mdb, user: str):
        """Returns the user preferences for a given user."""
        existing = await mdb.find_one("userprefs", {"user": user})
        if existing is not None:
            output = cls.parse_obj(existing)
        else:
            output = cls(user=user)
        return output

    async def commit(self, db):
        """Commits the settings to the database."""
        data = self.dict()
        await db.update_one(
            "userprefs", {"user": self.user}, {"$set": data}, upsert=True
        )
