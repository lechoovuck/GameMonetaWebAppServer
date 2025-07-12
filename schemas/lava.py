from datetime import datetime

from pydantic import BaseModel, Field
from typing import Annotated, Optional, Any


class LavaInvoiceCreateResponseData(BaseModel):
    id: str = Field(..., description="The id of the lava invoice")
    amount: float = Field(..., description="The price of the lava invoice")
    expired: Annotated[str, datetime] = Field(..., description="The duration of life of the lava invoice")
    status: int = Field(..., description="The status of the lava invoice")
    shop_id: str = Field(..., description="The shop id of the lava system")
    url: str = Field(..., description="The url of the lava payment page")
    comment: Optional[str] = Field(None, description="The comment on the lava invoice")
    fail_url: Optional[str] = Field(None, description="The url of the lava redirect in case of unsuccessful payment")
    success_url: Optional[str] = Field(None, description="The url of the lava redirect in case of successful payment")
    hook_url: Optional[str] = Field(None, description="The url of the lava webhook on payment status updates")
    custom_fields: Optional[any] = Field(None, description="The custom fields of the lava invoice")
    merchantName: str = Field(..., description="The name of the merchant")
    exclude_service: Optional[any] = Field(None, description="The excluded service of the lava invoice")
    include_service: Optional[any] = Field(None, description="The included service of the lava invoice")


class LavaInvoiceCreateResponse(BaseModel):
    data: Optional[LavaInvoiceCreateResponseData] = None
    status: int
    status_check: bool
    error: Optional[any] = None


class LavaWebhookRequest(BaseModel):
    invoice_id: str = Field(..., description="Unique identifier of the invoice")
    order_id: str = Field(..., description="Unique identifier of the order")
    status: str = Field(..., description="Status of the payment (e.g., 'success')")
    pay_time: str = Field(..., description="Timestamp of the payment in 'YYYY-MM-DD HH:MM:SS' format")
    amount: str = Field(..., description="Payment amount")
    credited: str = Field(..., description="Amount credited after fees")
    pay_service: Optional[str] = Field(None, description="Payment service used (e.g., 'sbp')")
    payer_details: Optional[str] = Field(None, description="Details of the payer (e.g., phone number)")
    custom_fields: Optional[Any] = Field(None, description="Custom fields, can be any type")
    type: Optional[int] = Field(None, description="Webhook type (e.g., 1 for payment confirmation)")

    class Config:
        extra = "allow"  # Разрешаем дополнительные поля
