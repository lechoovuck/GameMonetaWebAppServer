from pydantic import BaseModel, ConfigDict
from typing import List, Optional


class CategoryBase(BaseModel):
    name: str
    type: str
    description: Optional[str] = None
    image_url: Optional[str] = None


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(CategoryBase):
    pass


class Category(CategoryBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class CategoryListResponse(BaseModel):
    categories: List[Category]
