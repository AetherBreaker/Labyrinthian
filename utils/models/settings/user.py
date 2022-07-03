from typing import Dict, NewType
from utils.models.settings import SettingsBaseModel

UserID = NewType("UserID", str)
GuildID = NewType("GuildID", str)
CharacterName = NewType("CharacterName", str)


class UserPreferences(SettingsBaseModel):
    user: UserID
    characters: Dict[GuildID, Dict[CharacterName, str]] = {}
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
