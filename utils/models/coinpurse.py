from copy import deepcopy
from typing import TYPE_CHECKING, Dict, List, Optional, Union

import inflect

from utils.models.settings.coin import BaseCoin, CoinConfig, CoinType


if TYPE_CHECKING:
    from settings.guild import ServerSettings
    from bot import Labyrinthian


# ==== Coin Instance ====
class Coin(int):
    def __new__(
        cls,
        count: Union[int, str],
        base: BaseCoin,
        type: Optional[CoinType] = None,
        supersettings: Optional["ServerSettings"] = None,
    ):
        return super().__new__(cls, count)

    def __init__(
        self,
        count: int,
        base: BaseCoin,
        type: Optional[CoinType] = None,
        supersettings: Optional["ServerSettings"] = None,
    ):
        self.base = base
        self.type = base if type is None else type
        self.isbase = True if type is None or isinstance(type, BaseCoin) else False
        self._supersettings: "ServerSettings" = supersettings

    @property
    def supersettings(self):
        return self._supersettings

    @supersettings.setter
    def supersettings(self, value):
        self._supersettings = value

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
        return f"Coin(count={int(self)}, base={self.base!r}, type={self.type!r}, isbase={self.isbase!r})"

    def __deepcopy__(self, _):
        return Coin(self, self.type, self.base)

    @property
    def prefixed_count(self):
        p = inflect.engine()
        return f"{self} {self.type.prefix}"

    @property
    def named_count(self):
        p = inflect.engine()
        return f"{self} {p.plural(self.type.name, self)}"

    @property
    def value(self) -> float:
        return self / self.type.rate

    @property
    def valuestr(self) -> str:
        return f"{self / self.type.rate} {self.base.prefix}"

    def update_types(self, coinconf: CoinConfig = None) -> bool:
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
        bot: "Labyrinthian",
        config: CoinConfig,
        usersettings,
    ):
        self.coinlist = coinlist
        self.config = config
        self.settings = usersettings
        self.bot = bot

    # ==== coin selection ====
    def _match_selection(self, input):
        pass

    # ==== coin ops ====
    def add_coins(self, input):
        pass

    def remove_coins(self, input):
        pass

    # ==== conversion helpers ====
    pass

    # ==== display ====
    def display_contents(self):
        pass

    # ==== construction ====
    @classmethod
    async def for_char(cls, mdb, guild: str):
        pass

    # ==== data conversion ====
    def _init_from_dict(self, input: Dict):
        pass

    def to_dict(self):
        pass

    # ==== magic methods ====
    def __str__(self):
        pass

    def __iter__(self):
        pass
