from typing import Any, List, Optional, Union

import disnake
from utils.models.coinpurse import Coin
from utils.models.settings import SettingsBaseModel
from utils.models.settings.auction_docs import ListingDurationsConfig, RaritiesConfig
from utils.models.settings.charlog_docs import XPConfig
from utils.models.settings.coin_docs import CoinConfig

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
        "base": {
            "name": "Gold Piece",
            "prefix": "gp",
            "emoji": "<:DDBGold:983191635376623667>",
        },
        "type": {
            "name": "Gold Piece",
            "prefix": "gp",
            "emoji": "<:DDBGold:983191635376623667>",
        },
        "isbase": True,
    },
    "259200": {
        "count": "150",
        "base": {
            "name": "Gold Piece",
            "prefix": "gp",
            "emoji": "<:DDBGold:983191635376623667>",
        },
        "type": {
            "name": "Gold Piece",
            "prefix": "gp",
            "emoji": "<:DDBGold:983191635376623667>",
        },
        "isbase": True,
    },
    "604800": {
        "count": "275",
        "base": {
            "name": "Gold Piece",
            "prefix": "gp",
            "emoji": "<:DDBGold:983191635376623667>",
        },
        "type": {
            "name": "Gold Piece",
            "prefix": "gp",
            "emoji": "<:DDBGold:983191635376623667>",
        },
        "isbase": True,
    },
    "1209600": {
        "count": "450",
        "base": {
            "name": "Gold Piece",
            "prefix": "gp",
            "emoji": "<:DDBGold:983191635376623667>",
        },
        "type": {
            "name": "Gold Piece",
            "prefix": "gp",
            "emoji": "<:DDBGold:983191635376623667>",
        },
        "isbase": True,
    },
    "2630000": {
        "count": "750",
        "base": {
            "name": "Gold Piece",
            "prefix": "gp",
            "emoji": "<:DDBGold:983191635376623667>",
        },
        "type": {
            "name": "Gold Piece",
            "prefix": "gp",
            "emoji": "<:DDBGold:983191635376623667>",
        },
        "isbase": True,
    },
}
DEFAULT_RARITIES = {
    "Common": {
        "count": "20",
        "base": {
            "name": "Gold Piece",
            "prefix": "gp",
            "emoji": "<:DDBGold:983191635376623667>",
        },
        "type": {
            "name": "Gold Piece",
            "prefix": "gp",
            "emoji": "<:DDBGold:983191635376623667>",
        },
        "isbase": True,
    },
    "Uncommon": {
        "count": "40",
        "base": {
            "name": "Gold Piece",
            "prefix": "gp",
            "emoji": "<:DDBGold:983191635376623667>",
        },
        "type": {
            "name": "Gold Piece",
            "prefix": "gp",
            "emoji": "<:DDBGold:983191635376623667>",
        },
        "isbase": True,
    },
    "Rare": {
        "count": "60",
        "base": {
            "name": "Gold Piece",
            "prefix": "gp",
            "emoji": "<:DDBGold:983191635376623667>",
        },
        "type": {
            "name": "Gold Piece",
            "prefix": "gp",
            "emoji": "<:DDBGold:983191635376623667>",
        },
        "isbase": True,
    },
    "Very Rare": {
        "count": "80",
        "base": {
            "name": "Gold Piece",
            "prefix": "gp",
            "emoji": "<:DDBGold:983191635376623667>",
        },
        "type": {
            "name": "Gold Piece",
            "prefix": "gp",
            "emoji": "<:DDBGold:983191635376623667>",
        },
        "isbase": True,
    },
    "Legendary": {
        "count": "200",
        "base": {
            "name": "Gold Piece",
            "prefix": "gp",
            "emoji": "<:DDBGold:983191635376623667>",
        },
        "type": {
            "name": "Gold Piece",
            "prefix": "gp",
            "emoji": "<:DDBGold:983191635376623667>",
        },
        "isbase": True,
    },
    "Artifact": {
        "count": "400",
        "base": {
            "name": "Gold Piece",
            "prefix": "gp",
            "emoji": "<:DDBGold:983191635376623667>",
        },
        "type": {
            "name": "Gold Piece",
            "prefix": "gp",
            "emoji": "<:DDBGold:983191635376623667>",
        },
        "isbase": True,
    },
    "Unknown": {
        "count": "0",
        "base": {
            "name": "Gold Piece",
            "prefix": "gp",
            "emoji": "<:DDBGold:983191635376623667>",
        },
        "type": {
            "name": "Gold Piece",
            "prefix": "gp",
            "emoji": "<:DDBGold:983191635376623667>",
        },
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
    "basecoin": {
        "name": "Gold Piece",
        "prefix": "gp",
        "emoji": "<:DDBGold:983191635376623667>",
    },
    "cointypes": [
        {
            "name": "Copper Piece",
            "prefix": "cp",
            "rate": 100.0,
            "emoji": "<:DDBCopper:983191632230895668>",
        },
        {
            "name": "Silver Piece",
            "prefix": "sp",
            "rate": 10.0,
            "emoji": "<:DDBSilver:990421042013032488>",
        },
        {
            "name": "Electrum Piece",
            "prefix": "ep",
            "rate": 2.0,
            "emoji": "<:DDBElectrum:983191637813506068>",
        },
        {
            "name": "Platinum Piece",
            "prefix": "pp",
            "rate": 0.1,
            "emoji": "<:DDBPlatinum:983191639042457712>",
        },
    ],
}
DEFAULT_THRESHOLD = {
    "count": "50",
    "base": {
        "name": "Gold Piece",
        "prefix": "gp",
        "emoji": "<:DDBGold:983191635376623667>",
    },
    "type": {
        "name": "Gold Piece",
        "prefix": "gp",
        "emoji": "<:DDBGold:983191635376623667>",
    },
    "isbase": True,
}


class ServerSettings(SettingsBaseModel):
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
    outbidthreshold: Coin = Coin.from_dict(DEFAULT_THRESHOLD)
    ahfront: Optional[str] = None
    ahback: Optional[str] = None
    ahinternal: Optional[str] = None
    xplabel: str = "Badge"
    coinconf: CoinConfig = CoinConfig.from_dict(DEFAULT_COINS)

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
            elif hasattr(x, "update_types"):
                x.update_types()

    async def commit(self, db):
        """Commits the settings to the database."""
        data = self.dict()
        data["xptemplate"] = self.xptemplate.to_dict()
        data["coinconf"] = self.coinconf.to_dict()
        data["listingdurs"] = self.listingdurs.to_dict()
        data["rarities"] = self.rarities.to_dict()
        data["outbidthreshold"] = self.outbidthreshold.to_dict()
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
