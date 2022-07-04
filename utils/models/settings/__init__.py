from pydantic import BaseModel


class SettingsBaseModel(BaseModel):
    class Config:
        validate_assignment = True
        smart_union = False
        error_msg_templates = {
            "value_error.url.scheme": "This is not an accepted sheet URL."
        }


__all__ = "ServerSettings"
