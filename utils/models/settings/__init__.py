from pydantic import BaseModel


class SettingsBaseModel(BaseModel):
    class Config:
        validate_assignment = True
        smart_union = False

    @classmethod
    def from_dict(cls, *args, **kwargs):
        return cls.parse_obj(*args, **kwargs)

    def to_dict(self, *args, **kwargs):
        return self.dict(*args, **kwargs)


from .guild import ServerSettings  # noqa: E402

__all__ = ("ServerSettings", "CharacterSettings")
