from pydantic import BaseModel, ConfigDict
from typing import List, Optional


class TelegramCallbackSchema(BaseModel):
    id: int
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: str
    photo_url: Optional[str] = None
    auth_date: int
    hash: str

class TelegramCallbackConnectSchema(TelegramCallbackSchema):
    token: str