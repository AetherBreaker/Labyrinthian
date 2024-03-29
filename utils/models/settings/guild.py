from typing import TYPE_CHECKING, List, Optional, Union

import disnake
from utils.models import LabyrinthianBaseModel
from utils.models.coinpurse import Coin
from utils.models.settings.auction import ListingDurationsConfig, RaritiesConfig
from utils.models.settings.charlog import XPConfig
from utils.models.settings.coin import CoinConfig

if TYPE_CHECKING:
    from bot import Labyrinthian

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


class ServerSettings(LabyrinthianBaseModel):
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
    startingxp: str = 0
    coinconf: CoinConfig = CoinConfig.from_dict(DEFAULT_COINS)
    loggingcoins: Optional[str] = None
    loggingxp: Optional[str] = None
    loggingauction: Optional[str] = None
    loggingchar: Optional[str] = None

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
        yield self.loggingcoins
        yield self.loggingxp
        yield self.loggingauction
        yield self.loggingchar

    # ==== validators ====

    # ==== lifecycle ====
    @staticmethod
    async def get_data(bot: "Labyrinthian", guild: str):
        data = await bot.dbcache.find_one("srvconf", {"guild": guild})
        wasnone = False
        if data is None:
            wasnone = True
            data = {"guild": guild}
        return (data, wasnone)

    @classmethod
    def for_guild(cls, data):
        """Returns the server settings for a given guild."""
        outp = cls.parse_obj(data)
        outp.setup_selfref()
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
            if hasattr(x, "run_updates") and callable(x.run_updates):
                x.run_updates()
            elif hasattr(x, "update_types") and callable(x.update_types):
                x.update_types()

    def dict(self, *args, **kwargs):
        data = super().dict()
        data["xptemplate"] = self.xptemplate.to_dict()
        data["coinconf"] = self.coinconf.to_dict()
        data["listingdurs"] = self.listingdurs.to_dict()
        data["rarities"] = self.rarities.to_dict()
        data["outbidthreshold"] = self.outbidthreshold.to_dict()
        return data

    async def commit(self, db):
        """Commits the settings to the database."""
        self.run_updates()
        data = self.dict()
        await db.update_one(
            "srvconf", {"guild": self.guild}, {"$set": data}, upsert=True
        )

    @classmethod
    def no_validate(cls, data):
        settings = super().no_validate(data)
        settings.setup_selfref()
        return settings

    # ==== helpers ====
    def is_dm(self, member: disnake.Member):
        """Returns whether the given member is considered a DM given the DM roles specified in the servsettings."""
        if not self.dmroles:
            return any(r.name.lower() in DEFAULT_DM_ROLE_NAMES for r in member.roles)
        dm_role_set = set(self.dmroles)
        return any(str(r.id) in dm_role_set for r in member.roles)
