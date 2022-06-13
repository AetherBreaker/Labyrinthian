from typing import Dict, List, Optional, Union

import disnake
from utils.settings import SettingsBaseModel


DEFAULT_DM_ROLE_NAMES = {"dm", "gm", "dungeon master", "game master"}

class ServerSettings(SettingsBaseModel):
    guild: int
    dmroles: Optional[List[int]] = None
    # lookup_dm_required: bool = True
    # lookup_pm_dm: bool = False
    # lookup_pm_result: bool = False
    badgetemplate: Optional[Dict[Union[int, str], int]]
    

    # ==== lifecycle ====
    @classmethod
    async def for_guild(cls, db, guild_id: str):
        """Returns the server settings for a given guild."""

        existing = await db.find_one('srvconf', {"guild": guild_id})
        if existing is not None:
            return cls.parse_obj(existing)

        return cls(guild_id=guild_id)

    async def commit(self, db):
        """Commits the settings to the database."""
        await db.update_one('srvconf', {"guild": self.guild_id}, {"$set": self.dict()}, upsert=True)

    # ==== helpers ====
    def is_dm(self, member: disnake.Member):
        """Returns whether the given member is considered a DM given the DM roles specified in the servsettings."""
        if not self.dm_roles:
            return any(r.name.lower() in DEFAULT_DM_ROLE_NAMES for r in member.roles)
        dm_role_set = set(self.dm_roles)
        return any(r.id in dm_role_set for r in member.roles)