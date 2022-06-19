from typing import Dict, List, Union


class BaseCoin:
    def __init__(self, name: str, prefix: str):
        self.name = name
        self.prefix = prefix
        self.value = 1

    @classmethod
    def from_dict(cls, input: Dict[str, str]):
        return cls(input["name"], input["prefix"])

    def to_dict(self):
        return {"name": self.name, "prefix": self.prefix}

    def __deepcopy__(self, _):
        return BaseCoin(self.name, self.prefix)


class CoinType:
    def __init__(self, name: str, prefix: str, value: Union[float, int]) -> None:
        self.name = name
        self.prefix = prefix
        self.value = value

    @classmethod
    def from_dict(cls, input: Dict[str, Union[str, float, int]]):
        return cls(**input)

    def to_dict(self):
        return {"name": self.name, "prefix": self.prefix, "value": self.value}

    def __deepcopy__(self, _):
        return CoinType(self.name, self.prefix, self.value)


class Coins:
    def __init__(self, base: BaseCoin, types: List[CoinType]) -> None:
        self.base = base
        self.types = types

    # def __iter__(self):
    #     templist = sorted(
    #         [self.base, *self.types], key=lambda i: (i["value"], i["name"], i["prefix"])
    #     )
    #     for x in templist:
    #         yield x

    @property
    def coinlist(self):
        templist = sorted(
            [self.base, *self.types], key=lambda i: (i["value"], i["name"], i["prefix"])
        )
        return templist

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
        yield cls.from_dict
