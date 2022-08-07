from typing import Dict, List, Union


class CoinType:
    def __init__(
        self, name: str, prefix: str, rate: Union[float, int], emoji: str = None
    ) -> None:
        self.name = name
        self.prefix = prefix
        self.rate = rate
        self.emoji = emoji

    def __iter__(self):
        yield self.name
        yield self.prefix
        yield self.rate
        if self.emoji is not None:
            yield self.emoji

    def __setattr__(self, name, value):
        self.__dict__[name] = value

    @property
    def label(self):
        return f"Type: {self.name}"

    @classmethod
    def from_dict(cls, input: Dict[str, Union[str, float, int]]):
        return cls(**input)

    def to_dict(self):
        return {
            "name": self.name,
            "prefix": self.prefix,
            "rate": self.rate,
            "emoji": self.emoji,
        }

    def __repr__(self) -> str:
        return f"CoinType(name={self.name!r}, prefix={self.prefix!r}, rate={self.rate})"


class BaseCoin:
    def __init__(self, name: str, prefix: str, emoji: str = None):
        self.name = name
        self.prefix = prefix
        self.rate = 1.0
        self.emoji = emoji

    def __iter__(self):
        yield self.name
        yield self.prefix
        yield self.rate
        if self.emoji is not None:
            yield self.emoji

    def __setattr__(self, name, value):
        self.__dict__[name] = value

    @property
    def label(self):
        return f"Base: {self.name}"

    @classmethod
    def from_dict(cls, input: Dict[str, str]):
        return cls(**input)

    def to_dict(self):
        return {"name": self.name, "prefix": self.prefix, "emoji": self.emoji}

    def __repr__(self) -> str:
        return f"BaseCoin(name={self.name!r}, prefix={self.prefix!r}, rate={self.rate})"


class CoinConfig:
    def __init__(self, base: BaseCoin, types: List[CoinType]) -> None:
        self.base = base
        self.types = sorted(types, key=lambda i: (i.rate, i.name, i.prefix))

    def __iter__(self):
        templist = sorted(
            [self.base, *self.types], key=lambda i: (i.rate, i.name, i.prefix)
        )
        for x in templist:
            yield x

    def sort_items(self):
        self.types = sorted(self.types, key=lambda i: (i.rate, i.name, i.prefix))

    def create_empty_coinlist(self):
        coinlist = []
        for x in self:
            coinlist.append(
                {
                    "count": str(0),
                    "base": self.base.to_dict(),
                    "type": x.to_dict(),
                    "isbase": True if isinstance(x, BaseCoin) else False,
                }
            )
        return coinlist

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
        yield lambda cls, input: input if isinstance(input, CoinConfig) else (
            CoinConfig.from_dict(input)
            if not isinstance(cls, CoinConfig)
            else cls.from_dict(input)
        )

    def __deepcopy__(self, _):
        return CoinConfig(self.base, self.types)

    def __repr__(self) -> str:
        return f"CoinConfig(base={self.base!r}, types={self.types!r})"
