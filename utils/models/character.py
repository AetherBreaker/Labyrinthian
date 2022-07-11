from copy import deepcopy
import re
from typing import TYPE_CHECKING, Any, Dict, NewType, Optional
import typing
from bson import ObjectId

from pydantic import AnyUrl, BaseModel, validator
from utils.models import LabyrinthianBaseModel

from utils.models.settings.guild import ServerSettings


if TYPE_CHECKING:
    ObjID = ObjectId
    from bot import Labyrinthian
    from utils.MongoCache import UpdateResultFacade
    from utils.models.settings.user import UserPreferences
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


class LastLog(LabyrinthianBaseModel):
    id: ObjID = None
    time: int = None


class Character(LabyrinthianBaseModel):
    id: ObjID = None
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
    @staticmethod
    async def get_data(
        bot: "Labyrinthian", filter: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        char = await bot.dbcache.find_one(
            "charactercollection",
            filter,
        )
        if char is None:
            return None
        else:
            settings = await bot.get_server_settings(char["guild"], validate=False)
            if "id" not in char or char["id"] is None:
                char["id"] = deepcopy(char["_id"])
            char.pop("_id")
            char = {"settings": settings, **char}
            return char

    @classmethod
    def no_validate(cls, data):
        typings = typing.get_type_hints(cls)
        for field, value in data.items():
            fieldtype = typings.get(field, None)
            if isinstance(fieldtype, BaseModel):
                data[field] = fieldtype(value)
            elif hasattr(fieldtype, "from_dict"):
                data[field] = fieldtype.from_dict(value)
        return cls.construct(**data)

    async def commit(self, db):
        """Commits the settings to the database."""
        data = self.dict(exclude={"settings"})
        result: "UpdateResultFacade" = await db.update_one(
            "charactercollection",
            {"user": self.user, "guild": self.guild, "name": self.name},
            {"$set": data},
            upsert=True,
        )
        return result

    async def archive(self, bot: "Labyrinthian", uprefs: "UserPreferences"):
        """Archives the character data, rendering it inaccessible to end users
        but retaining the data on the database."""
        data = self.dict(exclude={"settings"})
        await bot.dbcache.insert_one("graveyard", data)
        result = await bot.dbcache.delete_one("charactercollection", {"_id": self.id})
        if result is None:
            await bot.dbcache.delete_one("charactercollection", {"id": self.id})
        if self.guild in uprefs.activechar:
            uprefs.activechar.pop(self.guild)
        if self.name in uprefs.characters[self.guild]:
            uprefs.characters[self.guild].pop(self.name)
        await uprefs.commit(bot.dbcache)

    # @classmethod
    # async def retrieve(
    #     cls,
    #     bot: "Labyrinthian",
    #     settings: ServerSettings,
    #     guild_id: str,
    #     user_id: str,
    #     character_name: str,
    # ):
    #     """Returns a character log."""
    #     char = await bot.dbcache.find_one(
    #         "graveyard",
    #         {"user": user_id, "guild": guild_id, "name": character_name},
    #     )
    #     if char is None:
    #         return None
    #     else:
    #         data = {"settings": settings, **char}
    #         data.pop("_id")
    #         if "id" not in data or data["id"] is None:
    #             data["id"] = char["_id"]
    #         recovered = cls.parse_obj(data)

    #         return recovered
