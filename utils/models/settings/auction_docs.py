import re
from typing import TYPE_CHECKING, Dict, List, Optional, Union

import inflect
from utils.functions import timedeltaplus
from utils.models.errors import IntegerConversionError
from utils.models.settings.coin_docs import Coin, CoinConfig

if TYPE_CHECKING:
    from .guild import ServerSettings

    _ServerSettingsT = ServerSettings


class Duration(int):
    def __new__(cls, duration: Union[int, str], fee: Coin):
        return super().__new__(cls, duration)

    def __init__(self, duration: Union[int, str], fee: Coin):
        self.fee = fee
        self.name = str(duration)

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"Duration(duration={int(self)}, fee={self.fee!r})"

    def __deepcopy__(self, _):
        return Duration(self, self.fee)

    @property
    def label(self):
        return f"{self.durstr} - {self.fee} {self.fee.type.name} fee"

    @classmethod
    def from_dict(cls, input: Dict[str, Union[str, Coin]]):
        fee = (
            input["fee"]
            if isinstance(input["fee"], Coin)
            else Coin.from_dict(input["fee"])
        )
        return cls(input["duration"], fee)

    def to_dict(self):
        return {"duration": self.name, "fee": self.fee.to_dict()}

    @property
    def durstr(self):
        return str(timedeltaplus(seconds=self))


class ListingDurationsConfig:
    def __init__(
        self, durlist: List[Duration], supersettings: Optional["ServerSettings"] = None
    ) -> None:
        self.durlist = durlist
        self._supersettings = supersettings

    def __repr__(self):
        joinstr = "\n".join(repr(x) for x in self.durlist)
        return f"ListingdurationsConfig(durlist=[{joinstr}])"

    def __iter__(self):
        for x in self.durlist:
            yield x

    def keys(self):
        for x in self.durlist:
            yield x

    def values(self):
        for x in self.durlist:
            yield x.fee

    def items(self):
        for x in self.durlist:
            yield (x, x.fee)

    @property
    def supersettings(self):
        return self._supersettings

    @supersettings.setter
    def supersettings(self, value):
        self._supersettings = value

    def cascade_guildid(self):
        for x in self.durlist:
            if hasattr(x, "fee"):
                x.fee.supersettings = self._supersettings

    def run_updates(self):
        for x in self.durlist:
            if hasattr(x, "fee"):
                x.fee.update_types()

    def sort_items(self):
        self.durlist = sorted(self.durlist, key=lambda i: (i, i.fee))

    @classmethod
    def from_dict(cls, data: Dict[str, int]):
        """Used to initialize a config from the database."""
        durlist: List[Duration] = sorted(
            [Duration(duration, Coin.from_dict(fee)) for duration, fee in data.items()],
            key=lambda i: (i, i.fee),
        )
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
        return {str(duration): duration.fee.to_dict() for duration in self.durlist}

    def to_str(self):
        p = inflect.engine()
        return "\n".join(
            [
                f"{duration.durstr} # {duration} : {duration.fee.named_count}"
                for duration in self.durlist
            ]
        )

    @classmethod
    def __get_validators__(cls):
        yield cls.from_dict


class Rarity(str):
    def __new__(cls, rarity: Union[int, str], fee: Coin):
        return super().__new__(cls, rarity)

    def __init__(self, rarity: int, fee: Coin):
        self.fee = fee

    def __repr__(self):
        return f"Rarity(rarity={str(self)}, fee={self.fee!r})"

    def __deepcopy__(self, _):
        return Rarity(self, self.fee)


class RaritiesConfig:
    def __init__(
        self, rarlist: List[Rarity], supersettings: Optional["ServerSettings"] = None
    ) -> None:
        self.rarlist = rarlist
        self._supersettings = supersettings

    def __repr__(self):
        joinstr = "\n".join(repr(x) for x in self.rarlist)
        return f"RaritiesConfig(rarlist=[{joinstr}])"

    def __iter__(self):
        for x in self.rarlist:
            yield x

    def keys(self):
        for x in self.rarlist:
            yield x

    def values(self):
        for x in self.rarlist:
            yield x.fee

    def items(self):
        for x in self.rarlist:
            yield (x, x.fee)

    @property
    def supersettings(self):
        return self._supersettings

    @supersettings.setter
    def supersettings(self, value):
        self._supersettings = value

    def cascade_guildid(self):
        for x in self.rarlist:
            if hasattr(x, "fee"):
                x.fee.supersettings = self._supersettings

    def run_updates(self):
        for x in self.rarlist:
            if hasattr(x, "fee"):
                x.fee.update_types()

    @classmethod
    def from_dict(cls, data: Dict[str, int]):
        """Used to initialize a config from the database."""
        rarlist: List[Rarity] = []
        for rarity, fee in data.items():
            rarlist.append(Rarity(rarity, Coin.from_dict(fee)))

        return cls(rarlist)

    @classmethod
    def from_str(cls, string: str, coinconf: CoinConfig):
        """Used to initialize a config from user input."""

        rarlist: List[Rarity] = []

        for line in string.splitlines():
            if not line or line.isspace():
                continue  # skip whitespace lines

            rarity, fee = line.rpartition(":")[::2]

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

            # Normally Rarity handles type casting, however here we want to check
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

            if not rarity or rarity.isspace():
                # rarity not provided: we skip line
                continue

            # done parsing, append to rarlist
            rarlist.append(Rarity(rarity, fee))

        return cls(rarlist)

    def to_dict(self):
        """Serialize the RaritiesConfig to a dict to store it in the db."""
        return {rarity: rarity.fee.to_dict() for rarity in self.rarlist}

    def to_str(self):
        p = inflect.engine()
        return "\n".join(
            [f"{rarity} : {rarity.fee.named_count}" for rarity in self.rarlist]
        )

    @classmethod
    def __get_validators__(cls):
        yield cls.from_dict
