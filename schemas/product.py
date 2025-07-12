from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional, Literal, Dict, Any
from schemas.subcategory import Subcategory


class ProductBase(BaseModel):
    name: str
    description: Optional[str] = None
    price: Optional[float]
    image_url: Optional[str] = None
    preview_image_url: Optional[str] = None


class ProductUpdate(ProductBase):
    pass


class Product(ProductBase):
    id: int
    subcategory: Subcategory

    model_config = ConfigDict(from_attributes=True)


class ProductListResponse(BaseModel):
    products: List[Product]


class ProductListGetAllResponse(ProductListResponse):
    success: bool


class ProductPlainSchema(ProductBase):
    id: int
    subcategory: int

    model_config = ConfigDict(from_attributes=True)


class GiftListResponse(BaseModel):
    gifts: List[Product]


class GiftListGetAllResponse(GiftListResponse):
    success: bool


class ProductOptionBase(BaseModel):
    option_name: str
    title: Optional[str] = None
    cols: Optional[int] = None
    child_group_name: Optional[str] = None
    type: Literal['select',
    'radio',
    'checkbox',
    'amount',
    'deposit',
    'bonus',
    'input_text',
    'input_email',
    '__parent_toggle',
    '__parent_radio',
    'steam_link']
    items: Optional[List[dict]] = None
    item: Optional[dict] = None
    default_value: Optional[dict] = None
    label: Optional[str] = None
    tooltip: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    is_required: Optional[bool] = False
    can_be_disabled: Optional[bool] = False

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ProductCreate(ProductBase):
    options: List[ProductOptionBase] = Field(default_factory=list, description="List of product options")
    subcategory_id: int = Field(..., description="ID of the subcategory")


class ProductDeliveryBase(BaseModel):
    type: str
    key: str
    is_required: bool
    label: str
    placeholder: Optional[str]
    value: Optional[str]
    tooltip: Optional[str]
    description: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class FaqSchema(BaseModel):
    question: str
    answer: str

    model_config = ConfigDict(from_attributes=True)


class ProductFull(Product):
    options: List[ProductOptionBase] = []
    options_text: Optional[str] = None
    delivery_inputs: List[ProductDeliveryBase] = []
    faq: List[FaqSchema] = []

    model_config = ConfigDict(from_attributes=True)


class Currencies(BaseModel):
    KZT: float
    USD: float
    update_time: int


class ProductGetByIdResponse(BaseModel):
    data: ProductFull
    success: bool
    currencies: Currencies


class GiftFull(Product):
    options: List[ProductOptionBase] = []
    options_text: Optional[str] = None
    delivery_inputs: List[ProductDeliveryBase] = []
    faq: List[FaqSchema] = []

    model_config = ConfigDict(from_attributes=True)


class GiftGetByIdResponse(BaseModel):
    data: GiftFull
    success: bool


class ProductOptionCreate(BaseModel):
    type: str
    option_name: str
    title: Optional[str] = None
    cols: Optional[int] = None
    items: Optional[List[Dict[str, Any]]] = None
    item: Optional[Dict[str, Any]] = None
    default_value: Optional[Dict[str, Any]] = None
    label: Optional[str] = None
    tooltip: Optional[str] = None
    description: Optional[str] = None
    child_group_name: Optional[str] = None
    is_required: Optional[bool] = False
    icon: Optional[str] = None
    can_be_disabled: Optional[bool] = False


class GiftCreate(BaseModel):
    name: str
    description: str
    steam_game_id: int
    options: Optional[List[ProductOptionCreate]] = None
    aliases: Optional[List[str]] = None


class BatchGiftCreateRequest(BaseModel):
    gifts: List[GiftCreate]


class BatchGiftCreateResponse(BaseModel):
    success: bool
    created_product_ids: List[int]
