import re
from typing import TYPE_CHECKING, Any, Dict, NewType
from bson import ObjectId

from pydantic import AnyUrl, validator

from utils.models.settings import SettingsBaseModel
from utils.models.settings.guild import ServerSettings


if TYPE_CHECKING:
    ObjID = ObjectId
else:
    ObjID = Any


DDB_URL_RE = re.compile(
    r"(?:https?://)?(?:www\.dndbeyond\.com|ddb\.ac)(?:/profile/.+)?/characters/(\d+)/?"
)
DICECLOUD_URL_RE = re.compile(r"(?:https?://)?dicecloud\.com/character/([\d\w]+)/?")
URL_KEY_V1_RE = re.compile(r"key=([^&#]+)")
URL_KEY_V2_RE = re.compile(r"/spreadsheets/d/([a-zA-Z0-9-_]+)")


UserID = NewType("UserID", str)
GuildID = NewType("GuildID", str)
CharacterName = NewType("CharacterName", str)


class LastLog(SettingsBaseModel):
    id: ObjID = None
    time: int = None


class Character(SettingsBaseModel):
    settings: ServerSettings
    user: UserID
    guild: GuildID
    name: CharacterName
    sheet: AnyUrl
    multiclasses: Dict[str, int] = {}
    xp: int = 0
    lastlog: LastLog = LastLog()

    # ==== properties ====
    @property
    def level(self):
        return 0 if len(self.multiclasses) == 0 else sum(self.multiclasses.values())

    @property
    def expected_level(self):
        var = "1"
        for x, y in self.settings.xptemplate.items():
            if self.xp >= x:
                var = y
        return var

    # ==== validators ====
    @validator("sheet")
    def check_url(cls, v):
        if DDB_URL_RE.match(v):
            return v
        elif DICECLOUD_URL_RE.match(v):
            return v
        else:
            m2 = URL_KEY_V2_RE.search(v)
            if m2:
                return v
            m1 = URL_KEY_V1_RE.search(v)
            if m1:
                return v
            else:
                raise ValueError(
                    "Sheet type does not match accepted formats, or is not a valid URL."
                )

    @validator("multiclasses")
    def valid_classes(cls, v, values):
        settings: ServerSettings = values.get("settings")
        for x in v:
            assert x in settings.classlist, f"{x} is not a valid class in this server."
        return v

    # ==== lifecycle ====
    @classmethod
    async def for_user(
        cls,
        mdb,
        settings: ServerSettings,
        guild_id: str,
        user_id: str,
        character_name: str,
    ):
        """Returns a character log."""
        char = mdb.find_one(
            "charactercollection",
            {"user": user_id, "guild": guild_id, "name": character_name},
        )
        if char is None:
            return None
        else:
            data = {"settings": settings, **char}
            return await cls.parse_obj(data)

    async def commit(self, db):
        """Commits the settings to the database."""
        data = self.dict(exclude={"settings"})
        await db.update_one(
            "charactercollection",
            {"user": self.user, "guild": self.guild, "name": self.name},
            {"$set": data},
            upsert=True,
        )
