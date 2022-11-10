from typing import TYPE_CHECKING, NewType

from bson import ObjectId

from utils.models import LabyrinthianBaseModel

if TYPE_CHECKING:
    ObjID = ObjectId
    from bot import Labyrinthian
else:
    ObjID = Any

UserID = NewType("UserID", str)
GuildID = NewType("GuildID", str)
CharacterName = NewType("CharacterName", str)


class AuctionListing(LabyrinthianBaseModel):
    id: ObjID
    guild: GuildID
    user: UserID
    name: CharacterName

    # ==== dunders ====
    def __iter__(self):
        pass

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
