from copy import deepcopy
from ctypes import Union
from datetime import datetime
from typing import TYPE_CHECKING, Callable, Dict, List, TypeVar
from bson import ObjectId
import cachetools
import disnake
import asyncio

_LabyrinthianT = TypeVar("_LabyrinthianT", bound=disnake.Client)
if TYPE_CHECKING:
    from bot import Labyrinthian

    _LabyrinthianT = Labyrinthian

class MongoCache(cachetools.TTLCache):
    def __init__(self, bot: _LabyrinthianT, maxsize: float, ttl: float, timer: Callable[[], float] = ..., getsizeof: Callable[[cachetools._VT], float] | None = ...) -> None:
        super().__init__(maxsize, ttl, timer, getsizeof)
        self.bot = bot

    def __missing__(self):
        return None

    def popitem(self):
        key, value = super().popitem()
        asyncio.create_task(self.updatedb(key, value))
        print('Key "%s" evicted with value "%s"' % (key, value))
        return key, value

    async def updatedb(self, key: str, value: Dict[str, Union[str, int, List, Dict, ObjectId, datetime, float]]):
        collectionkey = deepcopy(value['collectionkey'])
        value.pop('collectionkey')
        self.bot.sdb[collectionkey].replace_one({'_id': value['_id']}, value, True)