import disnake
from disnake.ext import commands
from yarl import URL

class ConstSender(disnake.ui.View):
    def __init__(self, bot: commands.bot):
        super().__init__(timeout=None)
        self.bot = bot


class ListingConst(disnake.ui.View):
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=600)
        self.bot = bot



class ListingModal(disnake.ui.Modal):
    def __init__(self, bot: commands.Bot, title: str, components: Components, custom_id: str = ..., timeout: float = 600) -> None:
        self.bot = bot
        super().__init__(title=title, components, custom_id, timeout)




listingmsg = {
    "content": '@aetherbreaker',
    "embeds":{
        "type": "rich",
        "title": 'Winged Boots',
        "description": "While you wear these boots, you have a flying speed equal to your walking speed. You can use the boots to fly for up to 4 hours, all at once or in several shorter flights, each one using a minimum of 1 minute from the duration. If you are flying when the duration expires, you descend at a rate of 30 feet per round until you land.\n\nThe boots regain 2 hours of flying capability for every 12 hours they aren't in use.",
        "color": "0x00FFFF",
        "fields": [
        {
            "name": 'Rarity: Uncommon',
            "value": "\u200B",
            "inline": True
        },
        {
            "name": 'Attunement: Yes',
            "value": '*Additional attunement info*',
            "inline": True
        },
        {
            "name": '\u220B',
            "value": "\u200B",
            "inline": True
        },
        {
            "name": 'Highest Bid',
            "value": '1000 gp',
            "inline": True
        },
        {
            "name": 'Buy Now Price',
            "value": '2000 gp',
            "inline": True
        }
        ],
        "thumbnail": {
        "url": URL(URL="https://www.dndbeyond.com/avatars/thumbnails/7/490/1000/1000/636284785276517401.jpeg"),
        "height": 0,
        "width": 0
        },
        "author": {
        "name": 'Character Name'
        }
    }
}