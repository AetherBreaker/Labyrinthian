import ast
from copy import deepcopy
from ctypes import Union
from datetime import datetime
from typing import TYPE_CHECKING, Callable, Dict, List, TypeVar
from bson import ObjectId
import cachetools
import disnake
import asyncio
import os
import pymongo
from pymongo.errors import PyMongoError
from pymongo.results import UpdateResult

_LabyrinthianT = TypeVar("_LabyrinthianT", bound=disnake.Client)
if TYPE_CHECKING:
    from bot import Labyrinthian

    _LabyrinthianT = Labyrinthian

class MongoCache(cachetools.TTLCache):
    def __init__(self, bot: _LabyrinthianT, workdir: str, maxsize: float, ttl: float, timer: Callable[[], float] = ..., getsizeof: Callable[[cachetools._VT], float] | None = ...) -> None:
        super().__init__(maxsize, ttl, timer, getsizeof)
        self.bot = bot

        LITdatDONE = False
        index = 0
        while not LITdatDONE:
            try:
                path = os.path.join(workdir, "LITdat", f"LITlog{'' if index == 0 else index}")
                LITdat = open(path, "x")
                LITdat.close()
                self.path = path
                LITdatDONE = True
            except FileExistsError:
                index += 1

    def popitem(self):
        key, value = super().popitem()
        self.updateLITdat(key, value)
        asyncio.create_task(self.updatedb(key, value))
        print('Key "%s" evicted with value "%s"' % (key, value))
        return key, value

    async def updatedb(self, key: str, value: Dict[str, Union[str, int, List, Dict, ObjectId, datetime, float]]):
        collectionkey = deepcopy(value['collectionkey'])
        value.pop('collectionkey')
        result: UpdateResult = await self.bot.sdb[collectionkey].replace_one({'_id': value['_id']}, value, True)

        # this is to check if our write operation to the database succeeded
        # if matched_count is less than 1 or it throws an error, the operation failed
        # if it succeeded, we want to remove the entry from our Lost In Transit log
        try:
            if result.matched_count > 0:
                self.removefromLITdat(key)
        except:
            pass

    def updateLITdat(self, key: str, value: Dict[str, Union[str, int, List, Dict, ObjectId, datetime, float]]):
        # open our sessions lost in transit data file in read only mode
        # and store the contents in a variable
        # we then close the file
        LITdat = open(self.path, "r")
        data = LITdat.read(size=-1)
        LITdat.close()

        # next we run split on the file contents to create a list separated by newlines
        # we then convert this back into a string to then strip the list "brackets" off
        data = data.splitlines()
        data = str(data)
        data.strip("[]")

        # now we encase the string in braces, then evaluate the string as code with literal_eval
        data = f"{{{data}}}"
        data = ast.literal_eval(data)

        # make our changes to the data...
        # by processing the data into a dict, we can overwrite data with matching keys
        # this allows us to "remember" if the same item has previously failed to
        # send to the database, so we only ever store the "newest" version of the item
        # (this doesnt account for if an even newer iteration of the item successfully wrote to database)
        data[key] = value

        # time to join the data back together with newlines for text editor readability
        # data is stored as "key: value" per line
        data = '\n'.join([f"{datakey}: {datavalue}" for datakey, datavalue in data.items()])

        # overwrite the contents of the original file, then close it.
        LITdat = open(self.path, "w")
        LITdat.write(data)
        LITdat.close()


    def removefromLITdat(self, key: str):
        # open our sessions lost in transit data file in read only mode
        # and store the contents in a variable
        # we then close the file
        LITdat = open(self.path, "r")
        data = LITdat.read(size=-1)
        LITdat.close()

        # next we run split on the file contents to create a list separated by newlines
        # we then convert this back into a string to then strip the list "brackets" off
        data = data.splitlines()
        data = str(data)
        data.strip("[]")

        # now we encase the string in braces, then evaluate the string as code with literal_eval
        data = f"{{{data}}}"
        data = ast.literal_eval(data)

        # make our changes to the data...
        # by processing the data into a dict, we can overwrite data with matching keys
        # this allows us to "remember" if the same item has previously failed to
        # send to the database, so we only ever store the "newest" version of the item
        # (this doesnt account for if an even newer iteration of the item successfully wrote to database)
        data.pop(key)

        # time to join the data back together with newlines for text editor readability
        # data is stored as "key: value" per line
        data = '\n'.join([f"{datakey}: {datavalue}" for datakey, datavalue in data.items()])

        # overwrite the contents of the original file, then close it.
        LITdat = open(self.path, "w")
        LITdat.write(data)
        LITdat.close()


    async def get(self, collectionkey: str, filter: Dict[str, Union[str, int, List, Dict, ObjectId, datetime, float]]):
        pass



    """note to self, store items in LIT file
    using keys of their object ID to ensure a unique key for each item"""