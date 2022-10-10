from typing import TYPE_CHECKING, Any, Dict, NewType, Optional

from bson import ObjectId

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
    activechar: Dict[GuildID, Optional[ActiveCharacter]] = {}
    characters: Dict[GuildID, Dict[CharacterName, ObjID]] = {}
    autoswap: bool = True
    coinconvert: bool = False

    # ==== checks ====
    def has_valid_activechar(self, guild_id: GuildID) -> bool:
        if guild_id in self.activechar:
            if isinstance(self.activechar[guild_id], ActiveCharacter):
                if isinstance(self.activechar[guild_id].id, ObjectId):
                    return True
        return False

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

    async def refresh_chardat(self, bot: "Labyrinthian"):
        chardat = (
            await bot.sdb["charactercollection"].find({"user": self.user}).sort("guild")
        ).to_list(None)
        for guild in list(self.characters.keys()):
            match = bot.get_guild(int(guild))
            self.characters.pop(guild)
            if not match:
                if guild in self.activechar:
                    self.activechar.pop(guild)
                continue
            self.characters[guild] = {}
            filterfunc = lambda document: document["guild"] == guild
            guildchars = {}
            for character in filter(filterfunc, chardat):
                self.characters[guild][character["name"]] = character["_id"]
                guildchars[character["name"]] = {
                    "name": character["name"],
                    "id": character["_id"],
                }
            if self.activechar[guild].name in guildchars:
                self.activechar[guild] = ActiveCharacter(
                    **guildchars[self.activechar[guild].name]
                )
        await self.commit(bot.dbcache)
