from typing import Dict, List, Union

from utils.models.errors import IntegerConversionError


DEFAULT_XP_TEMPLATE = {
    "1": 0,
    "2": 1,
    "3": 3,
    "4": 6,
    "5": 10,
    "6": 14,
    "7": 20,
    "8": 26,
    "9": 34,
    "10": 42,
    "11": 50,
    "12": 58,
    "13": 66,
    "14": 76,
    "15": 86,
    "16": 96,
    "17": 108,
    "18": 120,
    "19": 135,
    "20": 150,
}


class XPField(int):
    def __new__(cls, name: Union[str, int], value: Union[str, int]):
        return super().__new__(XPField, value)

    def __init__(self, name: str, value: Union[str, int]):
        self.name = name

    @property
    def value(self) -> int:
        return int(self)

    def __str__(self) -> str:
        return "%d" % int(self)

    def __repr__(self) -> str:
        return f"XPField(name={self.name!r}, value={self.value})"

    def __deepcopy__(self, _):
        return XPField(self.name, self.value)


class XPConfig:
    def __init__(self, fields: List[XPField]):
        self.fields = fields

    def __iter__(self):
        for x in self.fields:
            yield x

    def keys(self):
        for x in self.fields:
            yield x

    def values(self):
        for x in self.fields:
            yield x.name

    def items(self):
        for x in self.fields:
            yield (x, x.name)

    @classmethod
    def from_dict(cls, data: Dict[str, int]):
        """Used to initialize a config from the database."""
        fields: List[XPField] = [XPField(name, value) for name, value in data.items()]
        return cls(fields)

    @classmethod
    def from_str(cls, string: str):
        """Used to initialize a config from user input."""
        auto_name_index = 0
        fields: List[XPField] = []

        for line in string.splitlines():
            if not line or line.isspace():
                continue  # skip whitespace lines

            name, value = line.rpartition(":")[::2]

            auto_name_index += (
                1  # increment lineno to ensure auto-fields have the correct name
            )

            if value.isspace() or value == "":
                # if value is whitespace or empty, we default it
                # if a default doesnt exist for this loop index, we skip the line entirely
                if auto_name_index in DEFAULT_XP_TEMPLATE:
                    value = DEFAULT_XP_TEMPLATE[f"{auto_name_index}"]
                else:
                    continue

            # clean any potential whitespace off of value
            value = value.strip()  # type: ignore

            # Normally XPField handles type casting, however here we want to check
            # if type casting is safe and throw an error to present to the user if it isn't
            try:
                value = int(value)
            except:
                raise IntegerConversionError(
                    f"Error: could not convert {value} to an integer"
                )

            if name.isspace() or name == "":
                # name not provided: assign default name from provided default func
                name = str(auto_name_index)

            # done setting defaults, append to fields
            fields.append(XPField(name, value))

        return cls(fields)

    def to_dict(self):
        """Serialize the XPConfig to a dict to store it in the db."""
        return {field.name: field.value for field in self.fields}

    def to_str(self):
        return "\n".join([f"{field.name} : {field.value}" for field in self.fields])

    @classmethod
    def __get_validators__(cls):
        yield cls.from_dict
