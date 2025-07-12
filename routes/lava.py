import hashlib
import hmac
from datetime import datetime
from decimal import Decimal

import requests
import json
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from models import LavaWebhook

from schemas.lava import LavaInvoiceCreateResponse, LavaWebhookRequest
from utils import API_LAVA_CREATE, API_LAVA_TOKEN, LAVA_SUCCESS_URL, LAVA_SHOP_ID

router = APIRouter()


def create_payment(amount: float, order_id: str) -> LavaInvoiceCreateResponse:
    """
    Функция для создания платежа через LAVA.

    :param amount: Сумма платежа (например, 1500.00)
    :param order_id: Уникальный ID заказа в invoices
    :return: Ответ от API в формате JSON
    """
    payment_data = {
        "comment": f"Оплата товара {order_id}",
        "customFields": None,
        "excludeService": [],
        "expire": 60,
        "failUrl": LAVA_SUCCESS_URL,
        "hookUrl": None,
        "includeService": [],
        "orderId": order_id,
        "shopId": LAVA_SHOP_ID,
        "successUrl": LAVA_SUCCESS_URL,
        "sum": amount,
    }

    payment_data = dict(sorted(payment_data.items(), key=lambda x: x[0]))

    json_str = json.dumps(payment_data).encode()
    sign = hmac.new(bytes(API_LAVA_TOKEN, 'UTF-8'), json_str, hashlib.sha256).hexdigest()

    response = requests.post(
        API_LAVA_CREATE,
        json=payment_data,
        headers={
            'Signature': sign,
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
    )
    return LavaInvoiceCreateResponse.model_validate(response.json())


@router.post("/webhook", status_code=status.HTTP_201_CREATED, tags=["lava"])
async def lava_webhook(webhook_data: LavaWebhookRequest, db: AsyncSession = Depends(get_db)):
    webhook_dict = webhook_data.model_dump(exclude_unset=True)
    pay_time = datetime.strptime(webhook_data.pay_time, "%Y-%m-%d %H:%M:%S")
    amount = Decimal(webhook_data.amount)
    credited = Decimal(webhook_data.credited)

    known_fields = {
        "invoice_id": webhook_dict.pop("invoice_id"),
        "order_id": webhook_dict.pop("order_id"),
        "status": webhook_dict.pop("status"),
        "pay_time": pay_time,
        "amount": amount,
        "credited": credited,
        "custom_fields": webhook_dict.pop("custom_fields", None),
    }

    db_webhook = LavaWebhook(**known_fields)

    db.add(db_webhook)
    await db.commit()
    await db.refresh(db_webhook)

    return {"status": "success", "message": "Webhook received and stored"}
