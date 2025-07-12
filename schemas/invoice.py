from decimal import Decimal

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, Dict, Any, Literal

from enum import Enum
from datetime import datetime
from schemas.product import Product
from schemas.user import UserResponse


class InvoiceStatus(str, Enum):
    paid = "paid"
    wait = "wait"
    canceled = "canceled"
    refunded = "refunded"
    error = "error"
    process = "process"
    order_ok = "order_ok"
    order_error = "order_error"


class InvoiceBase(BaseModel):
    payment_method: str = Field(..., max_length=50, description="The payment method used.")
    bonus: Optional[int] = Field(None, description="Bonus points or value associated with the transaction.")
    order_info: Optional[Dict[str, Any]] = Field(None, description="Dynamic data stored as JSON.")


class InvoiceCreateRequest(InvoiceBase):
    delivery_email: Optional[EmailStr] = Field(None, description="The email address for delivery.")
    product_id: int = Field(..., description="The ID of the product being purchased.")
    amount: Decimal = Field(..., ge=0, description="The amount to be paid.")
    payment_system: Literal['lava', 'profitable']


class Invoice(InvoiceBase):
    id: int = Field(..., description="The unique numeric ID of the invoice.")
    created_at: datetime = Field(..., description="The timestamp when the invoice was created.")
    uuid: str = Field(pattern=r"^[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}$",
                      description="The unique UUID of the invoice.")
    status: InvoiceStatus = Field(..., description="The current status of the invoice.")
    product: Product = Field(..., description="The product being purchased.")

    class Config:
        from_attributes = True


class PaymentInvoiceSchema(BaseModel):
    id: int = Field(..., description="The unique numeric ID of the profitable invoice.")
    payment_datetime: datetime = Field(..., description="The timestamp when the invoice was created.")
    status: InvoiceStatus = Field(..., description="The current status of the invoice.")
    amount: Decimal = Field(..., ge=0, description="The amount to be paid.")

    class Config:
        from_attributes = True



class InvoiceAuthed(Invoice):
    delivery_email: Optional[EmailStr] = Field(None, description="The email address for delivery.")
    login: Optional[str] = Field(None, max_length=255, description="The Steam login provided by the user.")
    user: UserResponse


class InvoiceResponse(BaseModel):
    data: Invoice
    payment_invoice: Optional[PaymentInvoiceSchema] = None
    success: bool = False


class InvoiceAuthedResponse(BaseModel):
    data: InvoiceAuthed
    payment_invoice: Optional[PaymentInvoiceSchema] = None
    success: bool = False


class InvoiceListResponse(BaseModel):
    data: list[InvoiceAuthed]
    success: bool = False


class InvoiceNew(BaseModel):
    uuid: str


class InvoiceChangeStatusResponse(BaseModel):
    success: bool = False
    status: InvoiceStatus = Field(..., description="The new status of the invoice.")
    detail: Optional[str] = Field(None, description="Additional details about the operation's result.")


class ChangeInvoiceStatusRequest(BaseModel):
    uuid: str
    status: InvoiceStatus = Field(..., description="The new status of the invoice.")


class ChangeInvoiceStatusResponse(BaseModel):
    success: bool = False
    details: Optional[dict] = None
    error: Optional[str] = None


class InvoicePayRequest(BaseModel):
    gamemoneta_invoice_uuid: str = Field(pattern=r"^[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-"
                                                 r"[a-fA-F0-9]{4}-[a-fA-F0-9]{12}$",
                                         description="The unique UUID of the invoice.")
    email: EmailStr = Field(None, description="The email address for delivery.")
    amount: Decimal = Field(..., ge=0, description="The amount to pay.")


class InvoiceLoginCheckResponse(BaseModel):
    success: bool = False
    error: Optional[str] = None


class InvoicePendingResponse(BaseModel):
    invoices: Optional[list[Invoice]] = None
    error: Optional[str] = None


class InvoicePaymentIdResponse(BaseModel):
    invoice: Optional[Invoice] = None
    payment_invoice: Optional[PaymentInvoiceSchema] = None
    error: Optional[str] = None
