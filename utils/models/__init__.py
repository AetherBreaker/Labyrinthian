import inspect
import typing
from pydantic import BaseModel


class LabyrinthianBaseModel(BaseModel):
    @classmethod
    def no_validate(cls, data: typing.Dict[str, typing.Any]):
        for field_name, field in cls.__fields__.items():
            value = data[field_name]
            field_type = field.type_
            container_type = typing.get_origin(field.outer_type_) or field.outer_type_
            # Get converter...
            convert: typing.Callable[[typing.Any], typing.Any]
            try:
                isinitialized = isinstance(value, BaseModel)
            except TypeError:
                isinitialized = False
            if isinitialized:  # Check if value has already been initialized.
                convert = lambda obj: obj  # Return input unmodified.
            elif inspect.isclass(field_type) and issubclass(field_type, BaseModel):
                convert = field_type.parse_obj
            elif hasattr(field_type, "from_dict"):
                convert = field_type.from_dict
            else:
                convert = lambda obj: obj  # Return input unmodified.
            # Do conversion (both type and container type, if applicable)...
            if container_type is field_type:
                data[field_name] = convert(value)
            elif inspect.isclass(container_type) and issubclass(
                container_type, typing.Mapping
            ):
                data[field_name] = container_type.__call__(
                    (k, convert(v)) for k, v in value.items()
                )
            elif inspect.isclass(container_type) and issubclass(
                container_type, typing.Collection
            ):
                data[field_name] = container_type.__call__(map(convert, value))
            else:
                data[field_name] = convert(value)
        return cls.construct(**data)

    class Config:
        validate_assignment = True
        smart_union = False
        error_msg_templates = {
            "value_error.url.scheme": "This is not an accepted sheet URL."
        }
