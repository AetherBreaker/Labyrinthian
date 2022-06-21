import re
from typing import Dict, List, Pattern, Union

import inflect
from utils.functions import timedeltaplus
from utils.models.errors import IntegerConversionError
from utils.models.settings.coin_docs import Coin, CoinConfig
from utils.models.settings.guild import DEFAULT_LISTING_DURS


class Duration(int):
    def __new__(cls, duration: Union[int, str], fee: Coin):
        super().__new__(cls, duration)

    def __init__(self, duration: int, fee: Coin):
        self.fee = fee

    def __deepcopy__(self):
        return Duration(self, self.fee)

    @property
    def durstr(self):
        return str(timedeltaplus(seconds=self))

    @classmethod
    def from_dict(cls, input: Dict):
        return cls(input["duration"], Coin.from_dict(input["fee"]))

    def to_dict(self):
        return {"duration": self, "fee": self.fee.to_dict()}


class ListingDurationsConfig:
    def __init__(self, durlist: List[Duration]) -> None:
        self.durlist = durlist

    @classmethod
    def from_dict(cls, data: Dict[str, int]):
        """Used to initialize a config from the database."""
        durlist: List[Duration] = [
            Duration(duration, Coin.from_dict(fee)) for duration, fee in data.items()
        ]
        return cls(durlist)

    @classmethod
    def from_str(cls, string: str, coinconf: CoinConfig):
        """Used to initialize a config from user input."""

        durlist: List[Duration] = []

        for line in string.splitlines():
            if not line or line.isspace():
                continue  # skip whitespace lines

            duration, fee = line.rpartition(":")[::2]

            # If fee is empty, we ignore this line
            if not fee or fee.isspace():
                continue

            # clean any potential whitespace off of fee
            fee = fee.strip()  # type: ignore

            # Check for an integer in fee
            match = re.search(r"[\d,\.]+", fee)
            # Skip line if there is none
            if not match:
                continue

            # Normally Duration handles type casting, however here we want to check
            # if type casting is safe and throw an error to present to the user if it isn't
            try:
                count = int(re.sub(r",", "", match.group(0)))
            except:
                raise IntegerConversionError(
                    f"Error: could not convert {fee} to an integer"
                )

            p = inflect.engine()
            # Check for a currency type match
            for x in coinconf:
                if any(
                    re.search(pat, fee)
                    for pat in [x.name, x.prefix, p.plural(x.name, count)]
                ):
                    fee = Coin(count=count, base=coinconf.base, type=x)

            if not duration or duration.isspace():
                # duration not provided: we skip line
                continue

            match: re.Match = re.match(r"\d+")
            duration = max(match.groups())

            # done parsing, append to durlist
            durlist.append(Duration(duration, fee))

        return cls(durlist)

    def to_dict(self):
        """Serialize the ListingDurationsConfig to a dict to store it in the db."""
        return {duration: duration.fee.to_dict() for duration in self.durlist}

    def to_str(self):
        p = inflect.engine()
        p.plural()
        return "\n".join(
            [
                f"{duration.durstr} # {duration} : {duration.fee} "
                f"{p.plural(duration.fee.type.name, duration.fee)}"
                for duration in self.durlist
            ]
        )

    @classmethod
    def __get_validators__(cls):
        yield cls.from_dict
