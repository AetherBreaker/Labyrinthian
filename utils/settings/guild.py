from typing import Any, Dict, List, Optional, Tuple, Type, TypeVar, Union

import disnake
import inflect
from pydantic import BaseModel, Field, create_model
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
DEFAULT_BADGE_TEMPLATE = {
    "one": ("1", 0),
    "two": ("2", 1),
    "three": ("3", 3),
    "four": ("4", 6),
    "five": ("5", 10),
    "six": ("6", 14),
    "seven": ("7", 20),
    "eight": ("8", 26),
    "nine": ("9", 34),
    "ten": ("10", 42),
    "eleven": ("11", 50),
    "twelve": ("12", 58),
    "thirteen": ("13", 66),
    "fourteen": ("14", 76),
    "fifteen": ("15", 86),
    "sixteen": ("16", 96),
    "seventeen": ("17", 108),
    "eighteen": ("18", 120),
    "nineteen": ("19", 135),
    "twenty": ("20", 150),
}
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
    listingdurs: Optional[Dict[str, int]] = DEFAULT_LISTING_DURS
    rarities: Optional[Dict[str, int]] = DEFAULT_RARITIES
    outbidthreshold: Optional[int] = 50
    ahfront: Optional[str] = None
    ahback: Optional[str] = None
    ahinternal: Optional[str] = None
    badgelabel: Optional[str] = "badges"

    # ==== lifecycle ====
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


async def for_guild(db, guild: str):
    """Returns the server settings for a given guild."""
    existing = await db.find_one("srvconf", {"guild": guild})
    if "_badgetemplate" in existing:
        badgetemplate = from_local_dict(existing["_badgetemplate"])
    else:
        badgetemplate = from_local_dict(DEFAULT_BADGE_TEMPLATE)
    SettingsModel: Type["ServerSettings"] = create_model(
        "SettingsModel", __base__=ServerSettings, badgetemplate=badgetemplate
    )
    if existing is not None:
        return SettingsModel.parse_obj(existing)
    return SettingsModel(guild=guild, badgetemplate=DEFAULT_BADGE_TEMPLATE)


def from_local_dict(input, from_list: bool = False):
    fieldconstructor = lambda lvl, badge: Field(default=(lvl, badge))
    p = inflect.engine()
    inputdict = {
        p.number_to_words(x + 1): fieldconstructor(y, z)
        for x, (y, z) in enumerate(input if from_list else input.values())
    }
    model: Type["SettingsBaseModel"] = create_model(
        "BadgeTemplateModel", __base__=SettingsBaseModel, **inputdict
    )
    if from_list:
        input = {
            p.number_to_words(x + 1): fieldconstructor(y, z)
            for x, (y, z) in enumerate(input)
        }
    return model.parse_obj(input)


class BadgeField(int):
    def __new__(cls, name: str, value: t.Union[str, int]):
        return super().__new__(BadgeField, value)

    def __init__(self, name: str, value: t.Union[str, int]):
        self.name = name

    @property
    def value(self) -> int:
        return int(self)

    def __repr__(self) -> str:
        return f"BadgeField(name={self.name!r}, value={int(self.value)})"


class BadgeConfig:
    def __init__(self, fields: List[BadgeField]):
        self.fields = fields

    @classmethod
    def from_dict(cls, data: Dict[str, int]):
        """Used to initialize a config from the database."""
        fields: List[BadgeField] = []
        for name, value in data.items():
            fields.append(BadgeField(name, value))

        return cls(fields)

    @classmethod
    def from_str(cls, string: str):
        """Used to initialize a config from user input."""
        auto_name_index = 0
        fields: List[BadgeField] = []

        for line in string.splitlines():
            if not line or line.isspace():
                continue  # skip whitespace lines

            auto_name_index += (
                1  # increment lineno to ensure auto-fields have the correct name
            )

            if len(split := line.split(":")) == 2:
                # name, value provided: strip name and create BadgeField
                name, value = split
                fields.append(BadgeField(name.strip(), value))

            else:
                # only value provided: build name from auto-index
                name = str(auto_name_index)  # maybe customize?
                fields.append(BadgeField(name, line))

        return cls(fields)

    def to_dict(self):
        """Serialize the BadgeConfig to a dict to store it in the db."""
        return {field.name: field.value for field in self.fields}
