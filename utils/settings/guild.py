from optparse import Option
from typing import Any, Dict, List, Optional, Type, TypeVar, Union
from xmlrpc.client import Server

import disnake
import inflect
from pydantic import BaseModel, Field, create_model
from pydantic.error_wrappers import ErrorWrapper, ValidationError
from pydantic.fields import FieldInfo
from pydantic.utils import ROOT_KEY
from utils.settings import SettingsBaseModel

Model = TypeVar("Model", bound="BaseModel")

DEFAULT_DM_ROLE_NAMES = {"dm", "gm", "dungeon master", "game master"}
tempthing = {
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
DEFAULT_BADGE_TEMPLATE = [
    ("1", 0),
    ("2", 1),
    ("3", 3),
    ("4", 6),
    ("5", 10),
    ("6", 14),
    ("7", 20),
    ("8", 26),
    ("9", 34),
    ("10", 42),
    ("11", 50),
    ("12", 58),
    ("13", 66),
    ("14", 76),
    ("15", 86),
    ("16", 96),
    ("17", 108),
    ("18", 120),
    ("19", 135),
    ("20", 150),
]
DEFAULT_LISTING_DURS = {
    "86400": 75,
    "259200": 150,
    "604800": 275,
    "1209600": 450,
    "2630000": 750,
}
DEFAULT_RARITIES = {
    "Common": 20,
    "Uncommon": 40,
    "Rare": 60,
    "Very Rare": 80,
    "Legendary": 200,
    "Artifact": 400,
    "Unknown": 0,
}
DEFAULT_CLASS_LIST = (
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
)


class ServerSettings(SettingsBaseModel):
    guild: str
    dmroles: Optional[List[str]] = None
    classlist: Optional[List[str]] = DEFAULT_CLASS_LIST
    # lookup_dm_required: bool = True
    # lookup_pm_dm: bool = False
    # lookup_pm_result: bool = False
    _badgetemplate: Type["SettingsBaseModel"]
    listingdurs: Optional[Dict[str, int]] = DEFAULT_LISTING_DURS
    rarities: Optional[Dict[str, int]] = DEFAULT_RARITIES
    outbidthreshold: Optional[int] = 50
    ahfront: Optional[str] = None
    ahback: Optional[str] = None
    ahinternal: Optional[str] = None
    badgelabel: Optional[str] = "badges"

    # ==== lifecycle ====
    @classmethod
    async def for_guild(cls, db, guild: str):
        """Returns the server settings for a given guild."""

        existing = await db.find_one("srvconf", {"guild": guild})
        if existing is not None:
            if "_badgetemplate" in existing:
                _badgetemplate = from_local_dict(existing["_badgetemplate"])
            else:
                _badgetemplate = from_local_dict(DEFAULT_BADGE_TEMPLATE)
            result = cls.parse_obj(existing)
            result._badgetemplate = _badgetemplate
            return result
        _badgetemplate = from_local_dict(DEFAULT_BADGE_TEMPLATE)
        return cls(guild=guild, _badgetemplate=_badgetemplate)

    async def commit(self, db):
        """Commits the settings to the database."""
        await db.update_one(
            "srvconf", {"guild": self.guild}, {"$set": self.dict()}, upsert=True
        )

    # ==== helpers ====
    def is_dm(self, member: disnake.Member):
        """Returns whether the given member is considered a DM given the DM roles specified in the servsettings."""
        if not self.dmroles:
            return any(r.name.lower() in DEFAULT_DM_ROLE_NAMES for r in member.roles)
        dm_role_set = set(self.dmroles)
        return any(r.id in dm_role_set for r in member.roles)


def from_local_dict(input):
    fieldconstructor = lambda lvl, badge: Field(default=[lvl, badge])
    p = inflect.engine()
    inputdict = {
        p.number_to_words(x + 1): fieldconstructor(y, z)
        for x, (y, z) in enumerate(input)
    }
    model: Type["SettingsBaseModel"] = create_model(
        "BadgeTemplateModel", __base__=SettingsBaseModel, **inputdict
    )
    input = {p.number_to_words(x + 1): [y, z] for x, (y, z) in enumerate(input)}
    return model.parse_obj(input)
