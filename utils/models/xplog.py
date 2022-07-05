import math
import traceback
from typing import TYPE_CHECKING, Any, Generator, List, NewType, Tuple

from bson import ObjectId
from utils.models import LabyrinthianBaseModel


if TYPE_CHECKING:
    ObjID = ObjectId
    from pymongo.results import InsertOneResult
else:
    ObjID = Any


UserID = NewType("UserID", str)
DMUID = NewType("DMUID", str)
GuildID = NewType("GuildID", str)
CharacterName = NewType("CharacterName", str)


class XPLogEntry(LabyrinthianBaseModel):
    charref: ObjID
    user: UserID
    guild: GuildID
    name: CharacterName
    prevxp: float
    xpadded: float
    dm: DMUID
    timestamp: int

    # ==== database ====
    async def commit(self, db):
        """Commits the settings to the database."""
        data = self.dict()
        result: "InsertOneResult" = await db.insert_one("xplog", data)
        return result


class XPLogBook(LabyrinthianBaseModel):
    log: List[XPLogEntry]

    # ==== construction ====
    @classmethod
    async def new(cls, db, char_ref_id: ObjectId) -> "XPLogBook":
        data = db["xplog"].find({"charref": char_ref_id})
        data = data.sort("timestamp", -1)
        data = await data.to_list(None)
        if data:
            return cls.construct(log=[XPLogEntry.construct(**x) for x in data])
        else:
            return None

    def paginate(self, items_per_page: int) -> Generator[Tuple[XPLogEntry], None, None]:
        data = [*self.log]
        for x in range(math.ceil(len(self.log) / items_per_page)):
            result = []
            for y in range(items_per_page):
                if not data:
                    yield result
                    break
                else:
                    result.append(data[0])
                    data = data[1:]
            if not data:
                break
            yield result
