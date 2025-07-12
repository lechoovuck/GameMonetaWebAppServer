from typing import List

from pydantic import BaseModel, ConfigDict
from schemas.product import Product


class AliasBase(BaseModel):
    id: int
    product_id: int
    alias: str

    model_config = ConfigDict(from_attributes=True)


class AliasesGetAllResponse(BaseModel):
    aliases: List[AliasBase]
    success: bool
