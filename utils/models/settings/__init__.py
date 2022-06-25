from pydantic import BaseModel


class SettingsBaseModel(BaseModel):
    class Config:
        validate_assignment = True
        smart_union = False


from .guild import ServerSettings  # noqa: E402

__all__ = ("ServerSettings", "CharacterSettings")
