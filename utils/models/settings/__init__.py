from pydantic import BaseModel


class SettingsBaseModel(BaseModel):
    class Config:
        validate_assignment = True
        smart_union = False
        # underscore_attrs_are_private = True
        error_msg_templates = {
            "value_error.url.scheme": "This is not an accepted sheet URL."
        }


from .guild import ServerSettings  # noqa: E402

__all__ = ("ServerSettings", "CharacterSettings")
