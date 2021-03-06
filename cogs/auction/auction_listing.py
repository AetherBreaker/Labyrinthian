from typing import Any, Dict
import disnake


class ListingActionRow(disnake.ui.ActionRow):
    def __init__(self, listingdat: Dict[str, Any]):
        components = [
            disnake.ui.Button(
                custom_id="auction_bid_lowest",
                emoji="<:DDBPlatinum:983191639042457712>",
                style=disnake.ButtonStyle.green,
                label=f"Bid: {listingdat['highestbid']+50} gp",
            ),
            disnake.ui.Button(
                custom_id="auction_bid_custom",
                emoji="<:DDBGold:983191635376623667>",
                style=disnake.ButtonStyle.gray,
                label="Bid: Custom Amount",
            ),
        ]
        if listingdat["buynow"] != None:
            components.append(
                disnake.ui.Button(
                    custom_id="auction_buy_now",
                    emoji="🪙",
                    style=disnake.ButtonStyle.danger,
                    label=f"Buy Now: {listingdat['buynow']} gp",
                )
            )
        super().__init__(*components)
