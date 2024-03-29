import ast
import asyncio
import os
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    Mapping,
    MutableMapping,
    Sequence,
    Union,
)

import cachetools
from bson.objectid import ObjectId
from bson.raw_bson import RawBSONDocument
from pymongo.results import InsertOneResult, UpdateResult

if TYPE_CHECKING:
    from bot import Labyrinthian


@dataclass
class UpdateResultFacade:
    inserted_id: ObjectId


class MongoCache(cachetools.TTLCache):
    def __init__(
        self,
        bot: "Labyrinthian",
        workdir: str,
        maxsize: float,
        ttl: float,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(maxsize, ttl, *args, **kwargs)
        self.bot = bot

        LITdatDONE = False
        index = 0
        path = os.path.join(workdir, "logs", "LITdat")
        p = Path(path)
        if not p.exists():
            p.mkdir(parents=True, exist_ok=True)
        while not LITdatDONE:
            try:
                path = os.path.join(
                    workdir,
                    "logs",
                    "LITdat",
                    f"LITlog{'' if index == 0 else str(index)}.txt",
                )
                with open(path, "x"):
                    pass
                self.path = path
                LITdatDONE = True
            except FileExistsError as e:
                with open(path, "r") as LITdat:
                    if len(LITdat.read(-1)) < 1:
                        self.path = path
                        LITdatDONE = True
                index += 1

    def popitem(self):
        key, value = super().popitem()
        self.updateLITdat(key, value)
        asyncio.create_task(self.updatedb(key, value))
        # print('Key "%s" evicted with value "%s"' % (key, value))
        return key, value

    async def updatedb(
        self, key: str, value: Union[MutableMapping[str, Any], RawBSONDocument]
    ):
        collectionkey = deepcopy(value["collectionkey"])
        value.pop("collectionkey")  # type: ignore
        result: UpdateResult = await self.bot.sdb[collectionkey].replace_one(
            {"_id": value["_id"]}, value, True
        )

        # this is to check if our write operation to the database succeeded
        # if matched_count is less than 1 or it throws an error, the operation failed
        # if it succeeded, we want to remove the entry from our Lost In Transit log
        try:
            if result.matched_count > 0:
                self.removefromLITdat(key)
        except:
            pass
        # print(yaml.dump(self._Cache__data, sort_keys=False, default_flow_style=False))

    def updateLITdat(
        self,
        key: str,
        value: Dict[str, Union[str, int, List, Dict, ObjectId, datetime, float]],
    ):
        # open our sessions lost in transit data file in read only mode
        # and store the contents in a variable
        # we then close the file
        with open(self.path, "r") as LITdat:
            data = LITdat.read(-1)

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
        data = "\n".join(
            [f"{datakey}: {datavalue}" for datakey, datavalue in data.items()]
        )

        # overwrite the contents of the original file, then close it.
        with open(self.path, "w") as LITdat:
            LITdat.write(data)

    def removefromLITdat(self, key: str):
        # open our sessions lost in transit data file in read only mode
        # and store the contents in a variable
        # we then close the file
        with open(self.path, "r") as LITdat:
            data = LITdat.read(-1)

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
        data = "\n".join(
            [f"{datakey}: {datavalue}" for datakey, datavalue in data.items()]
        )

        # overwrite the contents of the original file, then close it.
        with open(self.path, "w") as LITdat:
            LITdat.write(data)

    def _find_matches_in_self(
        self, collectionkey: str, searchfilter: Mapping[str, Any]
    ):
        """Searches through the cache and returns a list of cache values that match the provided filter
        filter is expected to be a dict where every key value pair must match a key value pair in a cache document"""
        filt = {"collectionkey": collectionkey, **searchfilter}
        return list(
            filter(
                lambda item: all(x in item and item[x] == y for x, y in filt.items()),
                self.values(),
            )
        )

    async def insert_one(
        self,
        collectionkey: str,
        document: Union[MutableMapping[str, Any], RawBSONDocument],
        *args,
        **kwargs,
    ) -> InsertOneResult:
        result: InsertOneResult = await self.bot.sdb[collectionkey].insert_one(
            document, *args, **kwargs
        )
        data = document
        if "_id" not in data:
            data["_id"] = result.inserted_id  # type: ignore
        if "collectionkey" not in data:
            data["collectionkey"] = collectionkey  # type: ignore
        self[str(result.inserted_id)] = data
        # print(yaml.dump(self._Cache__data, sort_keys=False, default_flow_style=False))
        return result

    async def find_one(
        self, collectionkey: str, filter: Mapping[str, Any], *args: Any, **kwargs: Any
    ):
        data = None  # type: ignore
        cachematches = deepcopy(self._find_matches_in_self(collectionkey, filter))
        if cachematches:
            cachematches[0].pop("collectionkey")
            # print(yaml.dump(self._Cache__data, sort_keys=False, default_flow_style=False))
            return cachematches[0]
        else:
            data: MutableMapping[str, Any] = await self.bot.sdb[collectionkey].find_one(
                filter, *args, **kwargs
            )
            if data is not None:
                datacopy = deepcopy(data)
                datacopy["collectionkey"] = collectionkey
                self[str(datacopy["_id"])] = datacopy
            # print(yaml.dump(self._Cache__data, sort_keys=False, default_flow_style=False))
            return data

    async def replace_one(
        self,
        collectionkey: str,
        filter: Mapping[str, Any],
        replacement: Mapping[str, Any],
        upsert: bool = False,
        *args,
        **kwargs,
    ) -> UpdateResult:
        if "collectionkey" not in replacement:
            replacement["collectionkey"] = collectionkey
        if str(replacement["_id"]) in self.keys():
            self[str(replacement["_id"])] = replacement
        else:
            cachematches = self._find_matches_in_self(collectionkey, filter)
            idkey = str(cachematches[0]["_id"])
            self[idkey] = replacement
        replacement.pop("collectionkey")
        result: UpdateResult = await self.bot.sdb[collectionkey].replace_one(
            filter, replacement, upsert, *args, **kwargs
        )
        # print(yaml.dump(self._Cache__data, sort_keys=False, default_flow_style=False))
        return result

    async def update_one(
        self,
        collectionkey: str,
        filter: Mapping[str, Any],
        update: Union[Mapping[str, Any], Sequence[Mapping[str, Any]]],
        upsert: bool = False,
        *args,
        **kwargs,
    ) -> Union[UpdateResult, UpdateResultFacade]:
        document = await self.bot.sdb[collectionkey].find_one_and_update(
            *args,
            filter=filter,
            update=update,
            upsert=upsert,
            return_document=True,
            **kwargs,
        )
        document["collectionkey"] = collectionkey
        self[str(document["_id"])] = document
        # print(yaml.dump(self._Cache__data, sort_keys=False, default_flow_style=False))
        return UpdateResultFacade(inserted_id=document["_id"])

    async def delete_one(
        self, collectionkey: str, filter: Mapping[str, Any], *args, **kwargs
    ):
        result = await self.bot.sdb[collectionkey].find_one_and_delete(
            *args, filter=filter, **kwargs
        )
        if result is None:
            return result
        if str(result["_id"]) in self.keys():
            self.pop(str(result["_id"]))


class CharlistCache(cachetools.TTLCache):
    def __init__(
        self, bot: "Labyrinthian", maxsize: float, ttl: float, *args, **kwargs
    ) -> None:
        super().__init__(maxsize, ttl, *args, **kwargs)
        self.bot = bot

    async def find_distinct_chardat(self, guildkey: str, userkey: str) -> List[str]:
        if f"{guildkey}{userkey}" in self:
            # print(yaml.dump(self._Cache__data, sort_keys=False, default_flow_style=False))
            return self[f"{guildkey}{userkey}"]
        else:
            data: List[str] = await self.bot.sdb[f"charactercollection"].distinct(
                "name", {"user": userkey, "guild": guildkey}
            )
            if data:
                self[f"{guildkey}{userkey}"] = data
            # print(yaml.dump(self._Cache__data, sort_keys=False, default_flow_style=False))
            return data
