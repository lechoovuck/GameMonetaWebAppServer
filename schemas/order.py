from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import datetime


class OrderItemBase(BaseModel):
    product_id: int
    quantity: int
    price: float


class OrderItem(OrderItemBase):
    id: int
    order_id: int

    model_config = ConfigDict(from_attributes=True)


class OrderBase(BaseModel):
    items: List[OrderItemBase]


class OrderCreate(OrderBase):
    pass


class Order(OrderBase):
    id: int
    user_id: int
    order_date: datetime
    status: str
    total_price: float

    model_config = ConfigDict(from_attributes=True)


class OrderListResponse(BaseModel):
    orders: List[Order]
