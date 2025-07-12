from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from .category import Category


class SubcategoryBase(BaseModel):
    name: str
    description: Optional[str] = None


class SubcategoryCreate(SubcategoryBase):
    pass


class SubcategoryUpdate(SubcategoryBase):
    pass


class Subcategory(SubcategoryBase):
    id: int
    category: Category

    model_config = ConfigDict(from_attributes=True)


class SubcategoryListResponse(BaseModel):
    subcategories: List[Subcategory]
