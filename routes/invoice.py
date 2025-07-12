import asyncio
import random
import re
import string
from datetime import timedelta
from typing import List

from fastapi import APIRouter, Depends, status, HTTPException, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import update

from routes import lava
from models import Subcategory, User
from models.invoice import Invoice as InvoiceModel, PaymentInvoice
from models.product import Product as ProductModel
from routes.auth import register
from schemas.invoice import *
from database import get_db
from schemas.user import UserCreate
from utils import is_valid_steam_login, STEAM_LOGIN_TOKEN, STEAM_LOGIN_URL, verify_token, SECRET_DIGI, \
    create_access_token, send_email, verify_signature

import httpx

router = APIRouter()


@router.post("/", tags=["invoices"], status_code=status.HTTP_201_CREATED)
async def create_invoice(invoice: InvoiceCreateRequest,
                         authorization: Optional[str] = Header(None),
                         db: AsyncSession = Depends(get_db)):
    bonus = invoice.order_info.get('bonus', invoice.bonus)
    try:
        payload = verify_token(authorization)
        db_invoice = InvoiceModel(
            product_id=invoice.product_id,
            payment_method=invoice.payment_method,
            delivery_email=invoice.delivery_email,
            order_info=invoice.order_info,
            bonus=bonus or 0,
            status="wait",
            user_id=int(payload['sub']),
        )
    except HTTPException:
        db_invoice = InvoiceModel(
            product_id=invoice.product_id,
            payment_method=invoice.payment_method,
            delivery_email=invoice.delivery_email,
            order_info=invoice.order_info,
            bonus=bonus or 0,
            status="wait",
        )
        result = await db.execute(
            select(User).where(User.email == invoice.delivery_email)
        )
        existing_user = result.scalars().first()
        if existing_user:
            db_invoice.user_id = existing_user.id
        else:
            random_password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
            new_user = await register(UserCreate(
                email=invoice.delivery_email,
                name='Пользователь',
                password=random_password
            ), db)
            if new_user.token:
                reset_token = new_user.token
                await send_email(
                    recipient_email=invoice.delivery_email,
                    template_type="activate_profile",
                    subject="Активация профиля",
                    email_data={"reset_token": reset_token}
                )
            db_invoice.user_id = new_user.id

    db.add(db_invoice)
    await db.commit()
    await db.refresh(db_invoice)
    redirect_data = InvoicePayRequest(
        gamemoneta_invoice_uuid=db_invoice.uuid,
        email=invoice.delivery_email,
        amount=invoice.amount
    )

    if invoice.payment_system == 'lava':
        lava_resp = lava.create_payment(float(invoice.amount), db_invoice.uuid)
        return {'redirect_url': lava_resp.data.url}
    elif invoice.payment_system == 'profitable':
        async with httpx.AsyncClient(verify=False) as client:
            try:
                payment_url = "https://pay.gamemoneta.com/pay/init_payment_gamemoneta"
                response = await client.post(payment_url, data=redirect_data.model_dump())

                response.raise_for_status()

                response_data = response.json()
                encoded_id = response_data.get('uuid')
                if not encoded_id:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Failed to retrieve UUID from payment service."
                    )

                redirect_url = f"https://pay.gamemoneta.com/?uuid={encoded_id}"

                return {'redirect_url': redirect_url}

            except httpx.HTTPStatusError as e:
                raise HTTPException(
                    status_code=e.response.status_code,
                    detail=f"Error communicating with payment service: {e.response.text}"
                )
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"An unexpected error occurred: {str(e)}")


MAX_RETRIES = 20
INITIAL_RETRY_DELAY = 1
BACKOFF_FACTOR = 2


@router.get("/check_login", tags=["invoices"])
async def check_login(login: str):
    login_is_valid = is_valid_steam_login(login)
    if login_is_valid:
        async with httpx.AsyncClient(verify=False) as client:
            check = await client.get(
                f'{STEAM_LOGIN_URL}check_steam_login?api_key={STEAM_LOGIN_TOKEN}&steam_login={login}&steam_value=26')
            check.raise_for_status()

            check = check.json()
            if not check["success"]:
                return {"success": False, "error": "Проверьте правильность логина"}

            trans_id = check["request_id"]

            retry_delay = INITIAL_RETRY_DELAY
            for attempt in range(MAX_RETRIES):
                trans_response = await client.get(
                    f"{STEAM_LOGIN_URL}get_steam_response",
                    params={"api_key": STEAM_LOGIN_TOKEN, "trans_id": trans_id}
                )
                trans_response.raise_for_status()
                trans_data = trans_response.json()

                trans_status = trans_data.get("status")
                if trans_status != "process":
                    break

                await asyncio.sleep(retry_delay)
                retry_delay *= BACKOFF_FACTOR

            if trans_status == "ready" and trans_data["response"]["success"]:
                return {"success": True}
            return {
                "success": False,
                "error": (
                    "Нет возможности пополнить данный аккаунт, если вы уверены, "
                    "что регион вашего аккаунта верный - повторите попытку позже."
                )
            }
    return {"success": False, "error": 'Проверьте правильность логина'}


@router.get("/check_steam_link", tags=["invoices"])
async def check_login(link: str):
    if not re.compile(r'^(https?://)?(s\.team/p/[A-Za-z0-9_-]+/[A-Za-z0-9_-]+)$').match(link):
        return {'success': False, 'error': 'Неверная ссылка'}

    return {"success": True, "error": ''}


@router.get("/get/{uuid}", status_code=status.HTTP_200_OK, tags=["invoices"])
async def get_invoice(uuid: str, authorization: Optional[str] = Header(None), db: AsyncSession = Depends(get_db)):
    try:
        assert len(uuid) == 36 and uuid.count('-') == 4
    except AssertionError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")

    db_invoice = (await db.execute(select(InvoiceModel).where(InvoiceModel.uuid == uuid).options(
        selectinload(InvoiceModel.product)
        .selectinload(ProductModel.subcategory)
        .selectinload(Subcategory.category),
        selectinload(InvoiceModel.user)
    ))).scalar_one_or_none()

    if not db_invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    payment_invoice = (await db.execute(
        select(PaymentInvoice).where(PaymentInvoice.gamemoneta_invoice_uuid == uuid))).scalar_one_or_none()

    if authorization:
        try:
            payload = verify_token(authorization)
            if int(payload['sub']) == db_invoice.user_id:
                return InvoiceAuthedResponse(data=db_invoice, payment_invoice=payment_invoice, success=True)
        except HTTPException as e:
            pass

    return InvoiceResponse(data=db_invoice, payment_invoice=payment_invoice, success=True)


@router.get("/", response_model=InvoiceListResponse, status_code=status.HTTP_200_OK, tags=["orders", "invoices"])
async def get_all_orders(authorization: Optional[str] = Header(None),
                         cursor: Optional[int] = Query(None, description="The ID of the last fetched invoice"),
                         limit: int = Query(10, description="Number of invoices to fetch", gt=0, le=100),
                         status: Optional[List[InvoiceStatus]] = Query(None,
                                                                       description="Status for the loaded invoices"),
                         db: AsyncSession = Depends(get_db)):
    if authorization:
        try:
            payload = verify_token(authorization)
            user_id = int(payload["sub"])

            query = select(InvoiceModel).where(InvoiceModel.user_id == user_id).options(
                selectinload(InvoiceModel.product)
                .selectinload(ProductModel.subcategory)
                .selectinload(Subcategory.category),
                selectinload(InvoiceModel.user)
            )
            if cursor:
                query = query.where(InvoiceModel.id < cursor)
            if status:
                query = query.where(InvoiceModel.status.in_(status))

            invoices = (await db.execute(query.order_by(-InvoiceModel.id).limit(limit))).scalars().all()

            return InvoiceListResponse(data=list(invoices), success=True)
        except HTTPException as e:
            return InvoiceListResponse(data=[], success=False)
    else:
        return InvoiceListResponse(data=[], success=False)


@router.post("/change_status", response_model=InvoiceChangeStatusResponse, tags=["invoices"])
async def change_invoice_status(
        invoice: ChangeInvoiceStatusRequest,
        x_signature: str = Header(..., alias="X-Signature"),
        db: AsyncSession = Depends(get_db)):
    print('Invalid UUID format')
    print(invoice, x_signature)
    if not verify_signature(invoice.uuid, invoice.status.value, x_signature):
        raise HTTPException(status_code=403,
                            detail=f"Invalid signature. Authorization failed: {x_signature}, {invoice.uuid}, {invoice.status.value}")

    try:
        assert len(invoice.uuid) == 36 and invoice.uuid.count('-') == 4
    except AssertionError:
        print('Invalid UUID format')
        return InvoiceChangeStatusResponse(success=False, status=invoice.status, detail='Invalid UUID format.')

    db_invoice = (await db.execute(select(InvoiceModel).where(InvoiceModel.uuid == invoice.uuid))).scalar_one_or_none()
    if not db_invoice:
        return InvoiceChangeStatusResponse(success=False, status=invoice.status, detail='Invoice not found.')
    elif db_invoice.status == invoice.status.value or db_invoice.status == invoice.status:
        return InvoiceChangeStatusResponse(success=True, status=invoice.status,
                                           detail=f'Status is already {invoice.status.value}.')

    db_invoice.status = invoice.status
    if invoice.status == InvoiceStatus.paid:
        db_invoice.order_confirm = True
        email_created = await send_email(
            recipient_email=db_invoice.delivery_email,
            template_type="transaction",
            subject="Успешная покупка",
            email_data={"order_uuid": invoice.uuid}
        )

    await db.commit()
    await db.refresh(db_invoice)

    return InvoiceChangeStatusResponse(success=True, status=invoice.status)


@router.get("/get_pending_transactions", response_model=InvoicePendingResponse, tags=["invoices"])
async def get_pending_transactions(secret_key: str, db: AsyncSession = Depends(get_db)):
    if secret_key != SECRET_DIGI:
        return {
            'error': f'Invalid key {secret_key}',
        }

    query = select(InvoiceModel).where(InvoiceModel.status == "paid").options(
        selectinload(InvoiceModel.product)
        .selectinload(ProductModel.subcategory)
        .selectinload(Subcategory.category),
        selectinload(InvoiceModel.user))

    result = list((await db.execute(query)).scalars().all())

    if not result:
        return InvoicePendingResponse(error='No transactions found with status "paid".')

    try:
        update_query = (
            update(InvoiceModel)
            .where(InvoiceModel.status == 'paid')
            .values(status='process')
        )
        await db.execute(update_query)
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update transactions: {str(e)}"
        )

    return InvoicePendingResponse(invoices=result)


@router.get("/get_payment_transaction_id", response_model=InvoicePaymentIdResponse, tags=["invoices"])
async def get_payment_transaction_id(uuid: str, secret_key: str, db: AsyncSession = Depends(get_db)):
    if secret_key != SECRET_DIGI:
        return InvoicePaymentIdResponse(error="Invalid secret key}")

    invoice = (await db.execute(
        select(InvoiceModel).where(InvoiceModel.uuid == uuid).options(
            selectinload(InvoiceModel.product)
            .selectinload(ProductModel.subcategory)
            .selectinload(Subcategory.category),
            selectinload(InvoiceModel.user))
    )).scalar_one_or_none()

    if not invoice:
        return InvoicePaymentIdResponse(error="Invoice not found.")

    payment_invoice = (await db.execute(
        select(PaymentInvoice).where(PaymentInvoice.gamemoneta_invoice_uuid == uuid))).scalar_one_or_none()

    if not payment_invoice:
        return InvoicePaymentIdResponse(error="Payment invoice not found.")

    return InvoicePaymentIdResponse(invoice=invoice, payment_invoice=payment_invoice)
