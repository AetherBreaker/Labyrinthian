import ast
import asyncio
import os
from copy import deepcopy
from ctypes import Union
from dataclasses import dataclass
from datetime import datetime
from random import randint
from typing import (TYPE_CHECKING, Any, Callable, Dict, List, Mapping,
                    MutableMapping, Optional, Sequence, TypeVar)

import cachetools
import disnake
import pymongo
from bson import ObjectId
from bson.raw_bson import RawBSONDocument
from pymongo.errors import PyMongoError
from pymongo.results import InsertOneResult, UpdateResult, DeleteResult
from pymongo.typings import _DocumentType

_LabyrinthianT = TypeVar("_LabyrinthianT", bound=disnake.Client)
if TYPE_CHECKING:
    from bot import Labyrinthian

    _LabyrinthianT = Labyrinthian

@dataclass
class UpdateResultFacade:
    inserted_id: ObjectId




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

    def find_matches_in_self(self, searchfilter: Mapping[str, Any]):
        """Searches through the cache and returns a list of cache values that match the provided filter
        filter is expected to be a dict where every key value pair must match a key value pair in a cache document"""
        return list(filter(lambda item: all([x in item and item[x] == y for x,y in searchfilter.items()]), self.values()))

    async def insert_one(self, collectionkey: str, document: Union[MutableMapping[str, Any], RawBSONDocument], *args, **kwargs) -> InsertOneResult:
        result: InsertOneResult = await self.bot.sdb[collectionkey].insert_one(document, *args, **kwargs)
        data = document
        if '_id' not in data:
            data['_id'] = result.inserted_id
        if 'collectionkey' not in data:
            data['collectionkey'] = collectionkey
        self[str(result.inserted_id)] = data
        return result

    async def find_one(self, collectionkey: str, filter: Mapping[str, Any], *args: Any, **kwargs: Any) -> Optional[_DocumentType]:
        data = None
        cachematches = self.find_matches_in_self(filter)
        if cachematches:
            cachematches[0].pop('collectionkey')
            return cachematches[0]
        else:
            data: MutableMapping[str, Any] = await self.bot.sdb[collectionkey].find_one(filter, *args, **kwargs)
            datacopy = deepcopy(data)
            datacopy['collectionkey'] = collectionkey
            self[str(datacopy['_id'])] = datacopy
            return data

    # async def find(self, collectionkey: str, filter: Optional[Any] = None, *args: Any, **kwargs: Any):
    #     pass

    async def replace_one(self, collectionkey: str, filter: Mapping[str, Any], replacement: Mapping[str, Any], upsert: bool = False, *args, **kwargs) -> UpdateResult:
        if 'collectionkey' not in replacement:
            replacement['collectionkey'] = collectionkey
        if str(replacement['_id']) in self.keys():
            self[str(replacement['_id'])] = replacement
        else:
            cachematches = self.find_matches_in_self(filter)
            idkey = str(cachematches[0]['_id'])
            self[idkey] = replacement
        replacement.pop('collectionkey')
        result: UpdateResult = await self.bot.sdb[collectionkey].replace_one(filter, replacement, upsert, *args, **kwargs)
        return result

    async def update_one(self, collectionkey: str, filter: Mapping[str, Any], update: Union[Mapping[str, Any], Sequence[Mapping[str, Any]]], upsert: bool = False, *args, **kwargs) -> Union[UpdateResult, UpdateResultFacade]:
        pass

    async def delete_one(self, collectionkey: str, filter: Mapping[str, Any], *args, **kwargs) -> DeleteResult:
        pass

    """note to self, store items in LIT file
    using keys of their object ID to ensure a unique key for each item"""