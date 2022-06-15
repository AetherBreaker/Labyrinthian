from optparse import Option
from typing import Dict, List, Optional, Union

import disnake
from utils.settings import SettingsBaseModel


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


class ServerSettings(SettingsBaseModel):
    guild: str
    dmroles: Optional[List[str]] = None
    classlist: Optional[List[str]] = DEFAULT_CLASS_LIST
    # lookup_dm_required: bool = True
    # lookup_pm_dm: bool = False
    # lookup_pm_result: bool = False
    badgetemplate: Optional[Dict[str, int]] = DEFAULT_BADGE_TEMPLATE
    listingdurs: Optional[Dict[str, int]] = DEFAULT_LISTING_DURS
    rarities: Optional[Dict[str, int]] = DEFAULT_RARITIES
    outbidthreshold: Optional[int] = 50
    ahfront: Optional[str] = None
    ahback: Optional[str] = None
    ahinternal: Optional[str] = None
    badgelabel: Optional[str] = "badges"

    # ==== lifecycle ====
    @classmethod
    async def for_guild(cls, db, guild_id: str):
        """Returns the server settings for a given guild."""

        existing = await db.find_one("srvconf", {"guild": guild_id})
        if existing is not None:
            return cls.parse_obj(existing)

        return cls(guild_id=guild_id)

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


class BadgeTemplateModal(SettingsBaseModel):
    
