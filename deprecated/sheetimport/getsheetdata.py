import re
import requests
import json

async def get_character_data(url: str):
    regex = r"^.*characters\/(\d+)\/?"
    match = re.search(regex, url)

    if not match:
        await ctx.send("Unable to find a valid DDB character link.")
        return

    url = f"https://character-service.dndbeyond.com/character/v3/character/{match.group(1)}"
    resp = requests.get(url)
    json_data = json.loads(resp.content)['data']
    return json_data