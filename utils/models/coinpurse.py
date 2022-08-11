from copy import deepcopy
from math import ceil
from typing import TYPE_CHECKING, Dict, List, Optional, Union

import disnake
from utils.models.settings.coin import BaseCoin, CoinType

if TYPE_CHECKING:
    from utils.models.settings.coin import CoinConfig
    from utils.models.settings.user import UserPreferences

    from settings.guild import ServerSettings


# ==== Coin Instance ====
class Coin(int):
    def __new__(
        cls,
        count: Union[int, str],
        base: "BaseCoin",
        type: Optional["CoinType"] = None,
        supersettings: Optional["ServerSettings"] = None,
        history: int = 0,
    ):
        return super().__new__(cls, count)

    def __init__(
        self,
        count: int,
        base: "BaseCoin",
        type: Optional["CoinType"] = None,
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

    def __mod__(self, other):
        res = super(Coin, self).__mod__(other)
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
        yield lambda cls, input: input if isinstance(input, Coin) else Coin.from_dict(
            input
        ) if not isinstance(cls, Coin) else cls.from_dict(input)


# ==== CoinPurse ====
class CoinPurse:
    def __init__(
        self,
        coinlist: List[Coin],
        config: "CoinConfig",
        uprefs: "UserPreferences" = None,
    ):
        self.coinlist = coinlist
        self.config = config
        self.prefs = uprefs
        self.events = []

    # ==== magic methods ====
    def __len__(self):
        return self.coinlist.__len__()

    def __repr__(self):
        return f"CoinPurse(coinlist={self.coinlist!r}, config={self.config!r})"

    def __iter__(self):
        for x in self.coinlist:
            yield x

    # ==== methods ====
    def combine_batch(self, coins_to_combine: Union["CoinPurse", Coin, List[Coin]]):
        if isinstance(coins_to_combine, Coin):
            coins_to_combine = [coins_to_combine]
        elif isinstance(coins_to_combine, CoinPurse):
            coins_to_combine = coins_to_combine.coinlist
        self._validate_self()
        self.coinlist = self._start_math(coins_to_combine)
        if self.prefs.coinconvert:
            self._compaction_math()

    def set_coins(self, coins_to_set: Union["CoinPurse", Coin, List[Coin]]):
        if isinstance(coins_to_set, Coin):
            coins_to_set = [coins_to_set]
        elif isinstance(coins_to_set, CoinPurse):
            coins_to_set = coins_to_set.coinlist
        self._validate_self()
        for setcoin in coins_to_set:
            targindex, targcoin = next(
                (index, coin)
                for index, coin in enumerate(self.coinlist)
                if setcoin.type.name == coin.type.name
            )
            setcoin.hist = int(setcoin) - int(targcoin)
            self.coinlist[targindex] = setcoin

    def convert(self):
        self._validate_self()
        self._compaction_math()

    # ==== helpers ====
    def _start_math(self, other: Union["CoinPurse", Coin, List[Coin]]):
        freshcoins = self._sort_coins(x.copy_no_hist() for x in self.coinlist)
        return self._add_coin(freshcoins, other)

    def _validate_self(self):
        """This function is called to check that all Coin type data matches that contained
        in self.config.

        Slight or partial mismatches (i.e. cointype has a matching name, but the rate is mismatched)
        should be soft corrected, value conversion should be unecessary in these situations.

        Complete mismatches (i.e. the cointype is completely unrecognized) are passed off to
        a converter function to convert it into an equal value of valid currency."""
        newcoins: List[Coin] = []
        unrecognized: List[Coin] = []
        uidset = [cointype.uid for cointype in self.config]
        for coin in self.coinlist:
            coin = coin.copy_no_hist()

            # if the uid isnt found in our set of valid uids for this server
            # we append the coin to our list of unrecognized coins to be processed later
            # we then continue the loop
            if coin.uid not in uidset:
                unrecognized.append(coin)
                continue

            # check if the coins basetype matches, and update it if not
            if coin.base != self.config.base:
                coin.base = self.config.base

            # check if the coins type perfectly matches one of the valid types for this server
            # if not, we individually cheak each type attribute, update it, and register the change
            # in an event dict for displaying changes to the user
            elif not any(coin.type == cointype for cointype in self.config):
                targettype = next(
                    cointype for cointype in self.config if coin.uid == cointype.uid
                )
                eventdict = {}
                if coin.type.name != targettype.name:
                    eventdict["namechanged"] = {
                        "old": coin.type.name,
                        "new": targettype.name,
                    }
                    coin.type.name = targettype.name
                if coin.type.prefix != targettype.prefix:
                    eventdict["prefixchanged"] = {
                        "old": coin.type.prefix,
                        "new": targettype.prefix,
                    }
                    coin.type.prefix = targettype.prefix
                if coin.type.rate != targettype.rate:
                    eventdict["ratechanged"] = {
                        "old": coin.type.rate,
                        "new": targettype.rate,
                    }
                    coin.type.rate = targettype.rate
                if coin.type.emoji != targettype.emoji:
                    eventdict["emojichanged"] = {
                        "old": coin.type.emoji,
                        "new": targettype.emoji,
                    }
                    coin.type.emoji = targettype.emoji
                if eventdict:
                    self.events.append(eventdict)
            newcoins.append(coin)

        # next we want to check to make sure the coinpurse has a Coin object for each
        # valid cointype in this server.
        newcoin_names = [coin.type.name for coin in newcoins]
        for cointype in filter(
            lambda cointype: not cointype.name in newcoin_names,
            self.config,
        ):
            newcoins.append(Coin(0, self.config.base, cointype))

        # now we want to process any of the unrecognized coins
        # that have piled up and add them to our coinlist
        if unrecognized:
            self._compensate(newcoins, unrecognized)

        self.coinlist = self._sort_coins(x.copy_no_hist() for x in newcoins)

    def _compensate(
        self, coinlist: Union["CoinPurse", List[Coin]], oddcoinlist: List[Coin]
    ):
        """When an unrecognizable coin is found, this function is called to convert it
        into recognized currency as close to the original value as possible."""
        for oddcoin in oddcoinlist:
            if targetcoin := disnake.utils.get(coinlist, type__name=oddcoin.type.name):
                targetcoin += int(oddcoin)
                continue
            valdict = self.valuedict_from_count(
                int(oddcoin) / oddcoin.type.rate,
                self.config.base,
                self.config,
                capped=False,
            )
            oddcoinlist = self._start_math(self.from_simple_dict(valdict, self.config))

    def _add_coin(self, coinlist: List[Coin], other: Union["CoinPurse", List[Coin]]):
        for otherindex, othercoin in enumerate(other):
            if othercoin == 0:
                continue
            try:
                targetindex = next(
                    coinindex
                    for coinindex, coin in enumerate(coinlist)
                    if coin.type.name == othercoin.type.name
                )
            except StopIteration:
                coinlist.append(
                    Coin(
                        int(othercoin),
                        self.config.base,
                        othercoin.type,
                        history=int(othercoin),
                    )
                )
                coinlist = self._sort_coins(coinlist)
                continue
            if othercoin < 0:
                subbed = self._sub_coin(coinlist, othercoin, targetindex)
                coinlist = self._sort_coins(subbed)
            elif othercoin > 0:
                coinlist[targetindex] += othercoin
        return coinlist

    def _sub_coin(self, coinlist: List[Coin], other: Coin, targetindex: int):
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
        return self._add_coin(
            coinlist,
            self._sort_coins(
                [
                    other,
                    Coin(int(amt * x), self.config.base, other.type),
                    Coin(-int(amt), self.config.base, coinlist[thievery].type),
                ]
            ),
        )

    def _compaction_math(self):
        typelist = list(reversed(self.config))[1:]
        conlist = list(reversed(self.coinlist))
        for index, (coin, ctype) in enumerate(zip(conlist, typelist)):
            stepupcost = int((1 / ctype.rate) * coin.type.rate)
            conlist[index + 1] += Coin(int(coin) // stepupcost, coin.base, ctype)
            conlist[index] -= Coin(
                int(coin) - (int(coin) % stepupcost), coin.base, coin.type
            )
        self.coinlist = self._sort_coins(conlist)

    @staticmethod
    def _sort_coins(coinlist: List[Coin]) -> List[Coin]:
        return sorted(
            coinlist, key=lambda i: (i.type.rate, i.type.name, i.type.prefix, -i)
        )

    @staticmethod
    def valuedict_from_count(
        count: Union[float, int, str],
        type: Union["CoinType", "BaseCoin"],
        config: "CoinConfig",
        capped: bool = True,
    ) -> Dict[str, int]:
        count = float(count)  # JIC typecast
        result = {}
        smallestcoin = next(reversed(config))
        minval = int((count / type.rate) * smallestcoin.rate)
        found_start = False
        for cointype in config:
            if (
                (not capped)
                or found_start
                or (found_start := (cointype.name == type.name))
            ):
                val_in_smallest = (1 / cointype.rate) * smallestcoin.rate
                tempvar, minval = (
                    int(minval / val_in_smallest),
                    minval % val_in_smallest,
                )
                if tempvar != 0:
                    result[cointype.prefix] = tempvar
                minval *= -1 if count < 0 else 1
        return result

    # ==== properties ====
    @property
    def base(self) -> Coin:
        return self.coinlist[
            next(
                x for x, y in enumerate(self.coinlist) if isinstance(y.type, "BaseCoin")
            )
        ]

    @property
    def baseval(self) -> float:
        return float(sum(x.value for x in self.coinlist))

    @property
    def basechangeval(self) -> float:
        return float(sum(x.histbaseval for x in self.coinlist))

    @property
    def display_operation(self) -> str:
        return "\n".join(x.full_operation_str for x in self.coinlist)

    @property
    def display_total(self) -> str:
        return f"{self.config.base.emoji} {round(self.baseval, 2)} {self.config.base.prefix}"

    @property
    def display_operation_total(self) -> str:
        change = round(self.basechangeval, 2)
        return (
            f"{self.config.base.emoji} {round(self.baseval, 2)} {self.config.base.prefix}"
            + (f" ({'+'*(change>0)}{change})" * (change != 0.0))
        )

    # ==== lifecycle ====
    @classmethod
    def from_simple_dict(cls, input: Dict[str, int], config: "CoinConfig"):
        return cls(
            cls._sort_coins(
                Coin(
                    y,
                    config.base,
                    disnake.utils.find(lambda ctype: ctype.prefix == x, config),
                )
                for x, y in input.items()
            ),
            config,
        )

    @classmethod
    def from_dict(cls, input: Dict[str, Union[List[Coin], "CoinConfig"]]):
        if "coinlist" not in input:
            input["coinlist"] = [
                Coin(0, base=input["config"].base, type=x) for x in input["config"]
            ]
        else:
            input["coinlist"] = [Coin.from_dict(x) for x in input["coinlist"]]
        return CoinPurse(**input)

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
