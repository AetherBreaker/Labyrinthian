from copy import deepcopy
from math import ceil
from typing import TYPE_CHECKING, Dict, List, Optional, Union

from utils.models.settings.coin import BaseCoin, CoinType

if TYPE_CHECKING:
    from utils.models.settings.coin import CoinConfig

    from settings.guild import ServerSettings


# ==== Coin Instance ====
class Coin(int):
    def __new__(
        cls,
        count: Union[int, str],
        base: "BaseCoin",
        type: Optional[CoinType] = None,
        supersettings: Optional["ServerSettings"] = None,
        history: int = 0,
    ):
        return super().__new__(cls, count)

    def __init__(
        self,
        count: int,
        base: "BaseCoin",
        type: Optional[CoinType] = None,
        supersettings: Optional["ServerSettings"] = None,
        history: int = 0,
    ):
        self.base = base
        self.type = base if type is None else type
        self.isbase = True if type is None or isinstance(type, BaseCoin) else False
        self._supersettings: "ServerSettings" = supersettings
        self.hist = history

    @property
    def supersettings(self):
        return self._supersettings

    @supersettings.setter
    def supersettings(self, value):
        self._supersettings = value

    def __add__(self, other):
        res = super(Coin, self).__add__(other)
        return Coin(res, self.base, self.type, history=self.hist + other)

    def __iadd__(self, other):
        res = super(Coin, self).__add__(other)
        return Coin(res, self.base, self.type, history=self.hist + other)

    def __sub__(self, other):
        res = super(Coin, self).__sub__(other)
        return Coin(res, self.base, self.type, history=self.hist - other)

    def __isub__(self, other):
        res = super(Coin, self).__sub__(other)
        return Coin(res, self.base, self.type, history=self.hist - other)

    def __floordiv__(self, other):
        res = super(Coin, self).__floordiv__(other)
        return Coin(res, self.base, self.type, history=self.hist)

    def __div__(self, other):
        res = super(Coin, self).__div__(other)
        return Coin(res, self.base, self.type, history=self.hist)

    def __str__(self) -> str:
        return "%d" % int(self)

    def __repr__(self):
        return f"Coin(count={int(self)}, hist={self.hist}, base={self.base!r}, type={self.type!r}, isbase={self.isbase!r})"

    def __deepcopy__(self, _):
        return Coin(self, self.base, self.type, self.hist)

    def copy_no_hist(self):
        return Coin(self, self.base, self.type)

    @property
    def prefixed_count(self):
        return f"{int(self)} {self.type.prefix}"

    @property
    def value(self) -> float:
        return self / self.type.rate

    @property
    def histbaseval(self) -> float:
        return self.hist / self.type.rate

    @property
    def full_display_str(self) -> str:
        return f"{self.type.emoji} {int(self)} {self.type.prefix}"

    @property
    def full_operation_str(self) -> str:
        return f"{self.type.emoji} {int(self)} {self.type.prefix}" + (
            f" ({'+'*(self.hist>0)}{self.hist})" * (self.hist != 0)
        )

    @property
    def uid(self):
        return self.type.uid

    def update_types(self, coinconf: "CoinConfig" = None) -> bool:
        """Check if these coins types are outdated, if so, update them.
        Converts itself to a BaseCoin type if its original type cannot be found.

        Args:
            coinconf (CoinConfig): An instance of the current servers Coin Configuration.
            coinvar (Any): The variable that points to the current instance of Coin.
            Used to replace the current instance with a new one in the event of

        Returns:
            bool: True if coin count or type name was changed, else False.
        """
        if coinconf is None:
            coinconf = self._supersettings.coinconf
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

    def rate_conversion(self, type: "CoinType"):
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

    @classmethod
    def __get_validators__(cls):
        yield lambda cls, input: input if isinstance(input, Coin) else (
            Coin.from_dict(input) if not isinstance(cls, Coin) else cls.from_dict(input)
        )


# ==== CoinPurse ====
class CoinPurse:
    def __init__(
        self,
        coinlist: List[Coin],
        config: "CoinConfig",
    ):
        self.coinlist = coinlist
        self.config = config

    # ==== magic methods ====
    def __len__(self):
        return self.coinlist.__len__()

    def __str__(self):
        pass

    def __iter__(self):
        for x in self.coinlist:
            yield x

    def __add__(self, other: Union["CoinPurse", Coin, List[Coin]]):
        newlist = deepcopy(self.coinlist)
        if isinstance(other, Coin):
            other = [other]
        newlist = self.add_coin(newlist, other.coinlist)
        return CoinPurse(newlist, self.config)

    # ==== helpers ====
    def add_coin(
        self, coinlist: List[Coin], other: Union["CoinPurse", Coin, List[Coin]]
    ):
        # print("start of add")
        # print("coinlist = " + "\n\t".join(x.prefixed_count for x in coinlist) + "\n")
        # print(
        #     "other = "
        #     + "\n\t".join(
        #         x.prefixed_count
        #         for x in (other if isinstance(other, List) else [other])
        #     )
        #     + "\n\n"
        # )
        for y, x in enumerate(other):
            if x == 0:
                continue
            try:
                targetindex = next(
                    y for y, z in enumerate(coinlist) if z.type.name == x.type.name
                )
            except StopIteration:
                coinlist.append(x)
                coinlist = sorted(
                    coinlist, key=lambda i: (i.type.rate, i.type.name, i.type.prefix, i)
                )
                continue
            if x < 0:
                subbed = self.sub_coin(coinlist, x, targetindex)
                coinlist = sorted(
                    subbed,
                    key=lambda i: (i.type.rate, i.type.name, i.type.prefix, i),
                )
            elif x > 0:
                coinlist[targetindex] += x
                other[y] -= x
        for x in other:
            if x == 0:
                other.remove(x)
        # print("end of add")
        # print("coinlist = " + "\n\t".join(x.prefixed_count for x in coinlist) + "\n")
        # print(
        #     "other = "
        #     + "\n\t".join(
        #         x.prefixed_count
        #         for x in (other if isinstance(other, List) else [other])
        #     )
        #     + "\n\n"
        # )
        return coinlist

    def sub_coin(self, coinlist: List[Coin], other: Coin, targetindex: int):
        # print("start of subtract")
        # print("coinlist = " + "\n\t".join(x.prefixed_count for x in coinlist) + "\n")
        # print(
        #     "other = "
        #     + "\n\t".join(
        #         x.prefixed_count
        #         for x in (other if isinstance(other, List) else [other])
        #     )
        #     + "\n\n"
        # )
        while coinlist[targetindex] > 0 and other < 0:
            if coinlist[targetindex] >= abs(other):
                coinlist[targetindex] += other
                other += abs(other)
            elif coinlist[targetindex] < abs(other):
                other += coinlist[targetindex]
                coinlist[targetindex] -= coinlist[targetindex]
            else:
                coinlist[targetindex] -= 1
                other += 1
        if other > -1:
            return coinlist
        thievery = next(
            x for x, y in reversed(list(enumerate(coinlist[:targetindex]))) if y > 0
        )
        x = (1 / coinlist[thievery].type.rate) * other.type.rate
        amt = ceil(abs(other) / x)
        otherlist = [
            other,
            Coin(int(amt * x), self.config.base, other.type),
            Coin(-int(amt), self.config.base, coinlist[thievery].type),
        ]
        otherlist = sorted(
            otherlist,
            key=lambda i: (i, i.type.rate, i.type.name, i.type.prefix),
            reverse=True,
        )
        # print("end of subtract")
        # print("coinlist = " + "\n\t".join(x.prefixed_count for x in coinlist) + "\n")
        # print("other = " + "\n\t".join(x.prefixed_count for x in otherlist) + "\n\n")
        return self.add_coin(coinlist, otherlist)

        # Checks that the coinpurse only contains cointypes listed in the coinconfig
        # any invalid cointypes are converted to valid currency types, readded to
        # the coinpurse, then removed.

    def verify_all(self):
        pass

    # ==== properties ====
    @property
    def base(self) -> Coin:
        index = next(
            x for x, y in enumerate(self.coinlist) if isinstance(y.type, "BaseCoin")
        )
        return self.coinlist[index]

    @property
    def baseval(self) -> float:
        return float(sum(x.value for x in self.coinlist))


    @property
    def display_operation(self) -> str:
        return "\n".join(x.full_operation_str for x in self.coinlist)


    # ==== lifecycle ====
    @classmethod
    def from_dict(cls, input: Dict[str, Union[List[Coin], "CoinConfig"]]):
        if "coinlist" not in input:
            input["coinlist"] = [
                Coin(0, base=input["config"].base, type=x) for x in input["config"]
            ]
        else:
            input["coinlist"] = [Coin.from_dict(x) for x in input["coinlist"]]
        return CoinPurse(input["coinlist"], input["config"])

    def to_dict(self):
        return {"coinlist": [x.to_dict() for x in self.coinlist]}

    # ==== pydantic jank ====
    @classmethod
    def __get_validators__(cls):
        yield lambda cls, input: input if isinstance(input, CoinPurse) else (
            CoinPurse.from_dict(input)
            if not isinstance(cls, CoinPurse)
            else cls.from_dict(input)
        )
