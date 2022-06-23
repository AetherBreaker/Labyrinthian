from typing import Any, ClassVar, Dict, List, Optional, TypeVar, Union

import disnake
from pydantic import BaseModel
from utils.models.settings import SettingsBaseModel
from utils.models.settings.auction_docs import ListingDurationsConfig, RaritiesConfig
from utils.models.settings.charlog_docs import XPConfig
from utils.models.settings.coin_docs import CoinConfig

Model = TypeVar("Model", bound="BaseModel")

DEFAULT_DM_ROLE_NAMES = {"dm", "gm", "dungeon master", "game master"}
DEFAULT_XP_TEMPLATE = {
    "1": 0,
    "2": 1,
    "3": 3,
    "4": 6,
    "5": 10,
    "6": 14,
    "7": 20,
    "8": 26,
    "9": 34,
    "10": 42,
    "11": 50,
    "12": 58,
    "13": 66,
    "14": 76,
    "15": 86,
    "16": 96,
    "17": 108,
    "18": 120,
    "19": 135,
    "20": 150,
}
DEFAULT_LISTING_DURS = {
    "86400": {
        "count": "75",
        "base": {"name": "Gold Piece", "prefix": "gp"},
        "type": {"name": "Gold Piece", "prefix": "gp"},
        "isbase": True,
    },
    "259200": {
        "count": "150",
        "base": {"name": "Gold Piece", "prefix": "gp"},
        "type": {"name": "Gold Piece", "prefix": "gp"},
        "isbase": True,
    },
    "604800": {
        "count": "275",
        "base": {"name": "Gold Piece", "prefix": "gp"},
        "type": {"name": "Gold Piece", "prefix": "gp"},
        "isbase": True,
    },
    "1209600": {
        "count": "450",
        "base": {"name": "Gold Piece", "prefix": "gp"},
        "type": {"name": "Gold Piece", "prefix": "gp"},
        "isbase": True,
    },
    "2630000": {
        "count": "750",
        "base": {"name": "Gold Piece", "prefix": "gp"},
        "type": {"name": "Gold Piece", "prefix": "gp"},
        "isbase": True,
    },
}
DEFAULT_RARITIES = {
    "Common": {
        "count": "20",
        "base": {"name": "Gold Piece", "prefix": "gp"},
        "type": {"name": "Gold Piece", "prefix": "gp"},
        "isbase": True,
    },
    "Uncommon": {
        "count": "40",
        "base": {"name": "Gold Piece", "prefix": "gp"},
        "type": {"name": "Gold Piece", "prefix": "gp"},
        "isbase": True,
    },
    "Rare": {
        "count": "60",
        "base": {"name": "Gold Piece", "prefix": "gp"},
        "type": {"name": "Gold Piece", "prefix": "gp"},
        "isbase": True,
    },
    "Very Rare": {
        "count": "80",
        "base": {"name": "Gold Piece", "prefix": "gp"},
        "type": {"name": "Gold Piece", "prefix": "gp"},
        "isbase": True,
    },
    "Legendary": {
        "count": "200",
        "base": {"name": "Gold Piece", "prefix": "gp"},
        "type": {"name": "Gold Piece", "prefix": "gp"},
        "isbase": True,
    },
    "Artifact": {
        "count": "400",
        "base": {"name": "Gold Piece", "prefix": "gp"},
        "type": {"name": "Gold Piece", "prefix": "gp"},
        "isbase": True,
    },
    "Unknown": {
        "count": "0",
        "base": {"name": "Gold Piece", "prefix": "gp"},
        "type": {"name": "Gold Piece", "prefix": "gp"},
        "isbase": True,
    },
}
DEFAULT_CLASS_LIST = [
    "Artificer",
    "Barbarian",
    "Bard",
    "Blood Hunter",
    "Cleric",
    "Druid",
    "Fighter",
    "Monk",
    "Paladin",
    "Ranger",
    "Rogue",
    "Sorcerer",
    "Warlock",
    "Wizard",
]
DEFAULT_COINS = {
    "basecoin": {"name": "Gold Piece", "prefix": "gp"},
    "cointypes": [
        {"name": "Copper Piece", "prefix": "cp", "rate": 100.0},
        {"name": "Silver Piece", "prefix": "sp", "rate": 10.0},
        {"name": "Electrum Piece", "prefix": "ep", "rate": 2.0},
        {"name": "Platinum Piece", "prefix": "pp", "rate": 0.1},
    ],
}


class ServerSettings(SettingsBaseModel):
    # _instances: ClassVar[Dict[str, Optional["ServerSettings"]]] = None
    guild: str
    dmroles: Optional[List[Union[str, int]]] = []
    classlist: List[str] = DEFAULT_CLASS_LIST
    # lookup_dm_required: bool = True
    # lookup_pm_dm: bool = False
    # lookup_pm_result: bool = False
    xptemplate: XPConfig = XPConfig.from_dict(DEFAULT_XP_TEMPLATE)
    listingdurs: ListingDurationsConfig = ListingDurationsConfig.from_dict(
        DEFAULT_LISTING_DURS
    )
    rarities: RaritiesConfig = RaritiesConfig.from_dict(DEFAULT_RARITIES)
    outbidthreshold: int = 50
    ahfront: Optional[str] = None
    ahback: Optional[str] = None
    ahinternal: Optional[str] = None
    xplabel: str = "Badge"
    coinconf: CoinConfig = CoinConfig.from_dict(DEFAULT_COINS)

    # ==== magic methods ====
    # def __new__(cls, guild, *args, **kwargs):
    #     if str(guild) not in cls._instances:
    #         cls._instances[str(guild)] = super().__new__(cls, *args, **kwargs)
    #     return cls._instances

    def __iter__(self):
        yield self.guild
        yield self.dmroles
        yield self.classlist
        yield self.xptemplate
        yield self.listingdurs
        yield self.rarities
        yield self.outbidthreshold
        yield self.ahfront
        yield self.ahback
        yield self.ahinternal
        yield self.xplabel
        yield self.coinconf

    # ==== validators ====

    # ==== lifecycle ====
    @classmethod
    async def for_guild(cls, mdb, guild: str):
        """Returns the server settings for a given guild."""
        existing = await mdb.find_one("srvconf", {"guild": guild})
        if existing is not None:
            outp = cls.parse_obj(existing)
        else:
            outp = cls(guild=guild)
        outp.setup_selfref()
        print(outp)
        outp.run_updates()
        return outp

    def setup_selfref(self):
        for x in self:
            if hasattr(x, "supersettings"):
                x.supersettings = self
            else:
                continue
            if hasattr(x, "cascade_guildid"):
                x.cascade_guildid()

    def run_updates(self):
        for x in self:
            if hasattr(x, "run_updates"):
                x.run_updates()

    async def commit(self, db):
        """Commits the settings to the database."""
        data = self.dict()
        data["xptemplate"] = self.xptemplate.to_dict()
        data["coinconf"] = self.coinconf.to_dict()
        await db.update_one(
            "srvconf", {"guild": self.guild}, {"$set": data}, upsert=True
        )

    # ==== helpers ====
    def is_dm(self, member: disnake.Member):
        """Returns whether the given member is considered a DM given the DM roles specified in the servsettings."""
        if not self.dmroles:
            return any(r.name.lower() in DEFAULT_DM_ROLE_NAMES for r in member.roles)
        dm_role_set = set(self.dmroles)
        return any(r.id in dm_role_set for r in member.roles)
