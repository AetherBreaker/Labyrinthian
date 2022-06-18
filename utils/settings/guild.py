from enum import auto
from typing import Any, Dict, List, Optional, Set, Tuple, Type, TypeVar, Union

import disnake
import inflect
from pydantic import BaseModel, Field, create_model
from utils.models.errors import IntegerConversionError
from utils.settings import SettingsBaseModel

Model = TypeVar("Model", bound="BaseModel")


# {
#     "1": 0,
#     "2": 1,
#     "3": 3,
#     "4": 6,
#     "5": 10,
#     "6": 14,
#     "7": 20,
#     "8": 26,
#     "9": 34,
#     "10": 42,
#     "11": 50,
#     "12": 58,
#     "13": 66,
#     "14": 76,
#     "15": 86,
#     "16": 96,
#     "17": 108,
#     "18": 120,
#     "19": 135,
#     "20": 150,
# }
# [
#     BadgeField(name="1", value=0),
#     BadgeField(name="2", value=1),
#     BadgeField(name="3", value=3),
#     BadgeField(name="4", value=6),
#     BadgeField(name="5", value=10),
#     BadgeField(name="6", value=14),
#     BadgeField(name="7", value=20),
#     BadgeField(name="8", value=26),
#     BadgeField(name="9", value=34),
#     BadgeField(name="10", value=42),
#     BadgeField(name="11", value=50),
#     BadgeField(name="12", value=58),
#     BadgeField(name="13", value=66),
#     BadgeField(name="14", value=76),
#     BadgeField(name="15", value=86),
#     BadgeField(name="16", value=96),
#     BadgeField(name="17", value=108),
#     BadgeField(name="18", value=120),
#     BadgeField(name="19", value=135),
#     BadgeField(name="20", value=150),
# ]


DEFAULT_DM_ROLE_NAMES = {"dm", "gm", "dungeon master", "game master"}
DEFAULT_BADGE_TEMPLATE = {
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


class BadgeField(int):
    def __new__(cls, name: Union[str, int], value: Union[str, int]):
        return super().__new__(BadgeField, value)

    def __init__(self, name: str, value: Union[str, int]):
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

            name, value = line.rpartition(":")[::2]

            auto_name_index += (
                1  # increment lineno to ensure auto-fields have the correct name
            )

            if value.isspace() or value == "":
                # if value is whitespace or empty, we default it
                # if a default doesnt exist for this loop index, we skip the line entirely
                if auto_name_index in DEFAULT_BADGE_TEMPLATE:
                    value = DEFAULT_BADGE_TEMPLATE[f"{auto_name_index}"]
                else:
                    continue

            # clean any potential whitespace off of value
            value = value.strip()

            # Normally BadgeField handles type casting, however here we want to check
            # if type casting is safe and throw an error to present to the user if it isn't
            try:
                value = int(value)
            except:
                raise IntegerConversionError(
                    f"Error: could not convert {value} to an integer"
                )

            if name.isspace() or name == "":
                # name not provided: assign default name from provided default func
                name = str(auto_name_index)

            # done setting defaults, append to fields
            fields.append(BadgeField(name, value))

        return cls(fields)

    def to_dict(self):
        """Serialize the BadgeConfig to a dict to store it in the db."""
        return {field.name: field.value for field in self.fields}

    def to_str(self):
        return "\n".join([f"{field.name} : {field.value}" for field in self.fields])

    @classmethod
    def __get_validators__(cls):
        yield cls.from_dict


class ServerSettings(SettingsBaseModel):
    guild: str
    dmroles: Optional[List[str]] = None
    classlist: Optional[List[str]] = DEFAULT_CLASS_LIST
    # lookup_dm_required: bool = True
    # lookup_pm_dm: bool = False
    # lookup_pm_result: bool = False
    _badgetemplate: BadgeConfig = BadgeConfig.from_dict(DEFAULT_BADGE_TEMPLATE)
    listingdurs: Optional[Dict[str, int]] = DEFAULT_LISTING_DURS
    rarities: Optional[Dict[str, int]] = DEFAULT_RARITIES
    outbidthreshold: Optional[int] = 50
    ahfront: Optional[str] = None
    ahback: Optional[str] = None
    ahinternal: Optional[str] = None
    badgelabel: Optional[str] = "badges"

    # ==== lifecycle ====
    @classmethod
    async def for_guild(cls, mdb, guild: int):
        """Returns the server settings for a given guild."""
        existing = await mdb.find_one("srvconf", {"guild": guild})
        if existing is not None:
            return cls.parse_obj(existing)
        return cls(guild=guild)

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


# async def for_guild(db, guild: str):
#     """Returns the server settings for a given guild."""
#     existing = await db.find_one("srvconf", {"guild": guild})
#     if "_badgetemplate" in existing:
#         badgetemplate = from_local_dict(existing["_badgetemplate"])
#     else:
#         badgetemplate = from_local_dict(DEFAULT_BADGE_TEMPLATE)
#     SettingsModel: Type["ServerSettings"] = create_model(
#         "SettingsModel", __base__=ServerSettings, badgetemplate=badgetemplate
#     )
#     if existing is not None:
#         return SettingsModel.parse_obj(existing)
#     return SettingsModel(guild=guild, badgetemplate=DEFAULT_BADGE_TEMPLATE)


# def from_local_dict(input, from_list: bool = False):
#     fieldconstructor = lambda lvl, badge: Field(default=(lvl, badge))
#     p = inflect.engine()
#     inputdict = {
#         p.number_to_words(x + 1): fieldconstructor(y, z)
#         for x, (y, z) in enumerate(input if from_list else input.values())
#     }
#     model: Type["SettingsBaseModel"] = create_model(
#         "BadgeTemplateModel", __base__=SettingsBaseModel, **inputdict
#     )
#     if from_list:
#         input = {
#             p.number_to_words(x + 1): fieldconstructor(y, z)
#             for x, (y, z) in enumerate(input)
#         }
#     return model.parse_obj(input)
