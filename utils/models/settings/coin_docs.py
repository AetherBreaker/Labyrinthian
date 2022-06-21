from copy import deepcopy
from typing import Any, Dict, List, Optional, Union


DEFAULT_COINS = {
    "basecoin": {"name": "Gold Piece", "prefix": "gp"},
    "cointypes": [
        {"name": "Copper Piece", "prefix": "cp", "rate": 100.0},
        {"name": "Silver Piece", "prefix": "sp", "rate": 10.0},
        {"name": "Electrum Piece", "prefix": "ep", "rate": 2.0},
        {"name": "Platinum Piece", "prefix": "pp", "rate": 0.1},
    ],
}


# ==== Settings Classes ====
class CoinType:
    def __init__(self, name: str, prefix: str, rate: Union[float, int]) -> None:
        self.name = name
        self.prefix = prefix
        self.rate = rate

    def __iter__(self):
        yield self.name
        yield self.prefix
        yield self.rate

    @classmethod
    def from_dict(cls, input: Dict[str, Union[str, float, int]]):
        return cls(**input)

    def to_dict(self):
        return {"name": self.name, "prefix": self.prefix, "rate": self.rate}

    def __repr__(self) -> str:
        return f"CoinType(name={self.name!r}, prefix={self.prefix!r}, rate={self.rate})"


class BaseCoin:
    def __init__(self, name: str, prefix: str):
        self.name = name
        self.prefix = prefix
        self.rate = 1.0

    def __iter__(self):
        yield self.name
        yield self.prefix
        yield self.rate

    @classmethod
    def from_dict(cls, input: Dict[str, str]):
        return cls(input["name"], input["prefix"])

    def to_dict(self):
        return {"name": self.name, "prefix": self.prefix}

    def __repr__(self) -> str:
        return f"BaseCoin(name={self.name!r}, prefix={self.prefix!r}, rate={self.rate})"


class CoinConfig:
    def __init__(self, base: BaseCoin, types: List[CoinType]) -> None:
        self.base = base
        self.types = types

    def __iter__(self):
        templist = sorted(
            [self.base, *self.types], key=lambda i: (i.rate, i.name, i.prefix)
        )
        for x in templist:
            yield x

    @classmethod
    def from_dict(
        cls,
        input: Dict[
            str, Union[Dict[str, str], List[Dict[str, Union[str, float, int]]]]
        ],
    ):
        types = [CoinType(**x) for x in input["cointypes"]]
        return cls(BaseCoin(**input["basecoin"]), types)

    def to_dict(self):
        return {
            "basecoin": self.base.to_dict(),
            "cointypes": [x.to_dict() for x in self.types],
        }

    @classmethod
    def __get_validators__(cls):
        yield lambda cls, input: isinstance(input, CoinConfig) or cls.from_dict(input)

    def __repr__(self) -> str:
        return f"CoinConfig(base={self.base!r}, types={self.types!r})"


# ==== Coin Instance ====
class Coin(int):
    def __new__(
        cls, count: Union[int, str], base: BaseCoin, type: Optional[CoinType] = None
    ):
        return super().__new__(cls, count)

    def __init__(self, count: int, base: BaseCoin, type: Optional[CoinType] = None):
        self.base = base
        self.type = base if type is None else type
        self.isbase = True if type is None or isinstance(type, BaseCoin) else False

    def __iadd__(self, other):
        res = super(Coin, self).__add__(other)
        return self.__class__(max(res, 0), self.base, self.type)

    def __isub__(self, other):
        res = super(Coin, self).__sub__(other)
        return self.__class__(max(res, 0), self.base, self.type)

    def __imul__(self, other):
        res = super(Coin, self).__mul__(other)
        return self.__class__(max(res, 0), self.base, self.type)

    def __idiv__(self, other):
        res = super(Coin, self).__div__(other)
        return self.__class__(max(res, 0), self.base, self.type)

    def __ifloordiv__(self, other):
        res = super(Coin, self).__floordiv__(other)
        return self.__class__(max(res, 0), self.base, self.type)

    def __str__(self) -> str:
        return "%d" % int(self)

    def __repr__(self):
        return f"Coin(count={self:d}, base={repr(self.base)}, type={repr(self.type)}, isbase={self.isbase})"

    def __deepcopy__(self, _):
        return Coin(self, self.type, self.base)

    @property
    def value(self) -> float:
        return self / self.type.rate

    @property
    def valuestr(self) -> str:
        return f"{self / self.type.rate} {self.base.prefix}"

    def update_types(self, coinconf: CoinConfig) -> bool:
        """Check if these coins types are outdated, if so, update them.
        Converts itself to a BaseCoin type if its original type cannot be found.

        Args:
            coinconf (CoinConfig): An instance of the current servers Coin Configuration.
            coinvar (Any): The variable that points to the current instance of Coin.
            Used to replace the current instance with a new one in the event of

        Returns:
            bool: True if coin count or type name was changed, else False.
        """
        skiptype = False
        basecoin = False

        # Update our BaseCoin instance
        self.base = deepcopy(coinconf.base)

        # Check if our type is an instance of BaseCoin
        if self.isbase:
            # If so, cascade our BaseCoin update down to our CoinType
            self.type = deepcopy(self.base)

        # Check if our original CoinType still exists
        if not basecoin:
            for z in coinconf.types:
                if len([True for x, y in zip(z, self.type) if x == y]) >= 3:
                    skiptype = True

        # If we are a BaseCoin, or our original Type is otherwise unchanged
        # we stop and return False
        if self.isbase or skiptype:
            return False

        bestmatch = None
        # Since we want to prioritize keeping currency value over type
        # but still prefer a matched name, we check for a match to both
        for x in coinconf.types:
            if x.name == self.type.name:
                if x.rate == self.type.rate:
                    bestmatch = x

        # If theres no double match, we match with rate to maintain currency value
        if bestmatch is None:
            for x in coinconf.types:
                if x.rate == self.type.rate:
                    bestmatch = x

        # If still no match, we match with name and run a currency conversion
        if bestmatch is None:
            for x in coinconf.types:
                if x.name == self.type.name:
                    bestmatch = x

        # Begin Conversion
        if bestmatch is not None:
            if self.type.rate == bestmatch.rate:
                self.type = deepcopy(bestmatch)
                return False
            self.rate_conversion(deepcopy(bestmatch))
            return True

        # If our original Type is no longer recognizable or doesnt exist
        # we convert to a BaseCoin and return True
        self.rate_conversion(self.base)
        return True

    def rate_conversion(self, type: CoinType):
        if type.rate == self.type.rate:
            self.type = deepcopy(type)
            return
        self.__class__(
            max(
                [round(self.value * type.rate), round(round(self.value) * type.rate), 0]
            ),
            self.base,
            deepcopy(type),
        )

    @classmethod
    def from_dict(cls, input: Dict[str, Union[int, str, Dict]]):
        type = (
            BaseCoin.from_dict(input["type"])
            if input["isbase"]
            else CoinType.from_dict(input["type"])
        )
        return cls(input["count"], BaseCoin.from_dict(input["base"]), type)

    def to_dict(self):
        return {
            "count": str(self),
            "base": self.base.to_dict(),
            "type": self.type.to_dict(),
            "isbase": self.isbase,
        }


# ==== CoinPurse ====
# class CoinPurse:
