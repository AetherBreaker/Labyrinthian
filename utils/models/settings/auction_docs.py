class Duration(int):
    def __new__(cls, durstr: str, duration: int, fee: int, currency: str):
        return super().__new__(Duration, duration)


class ListingDurations:
    pass
