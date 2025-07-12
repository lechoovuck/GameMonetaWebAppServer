from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from database import get_db
from models.user import User, OAuthProfile
from schemas.oauth import TelegramCallbackSchema, TelegramCallbackConnectSchema
from utils import create_access_token, find_user_by_token
import os
import hashlib
import hmac
import datetime as dt

router = APIRouter()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


async def verify_telegram_auth(data: TelegramCallbackSchema) -> bool:
    if not data.hash or not data.auth_date:
        return False

    check_data = []
    if data.auth_date:
        check_data.append(f"auth_date={data.auth_date}")
    if data.first_name:
        check_data.append(f"first_name={data.first_name}")
    if data.id:
        check_data.append(f"id={data.id}")
    if data.last_name:
        check_data.append(f"last_name={data.last_name}")
    if data.photo_url:
        check_data.append(f"photo_url={data.photo_url}")
    if data.username:
        check_data.append(f"username={data.username}")
    check_string = "\n".join(check_data)

    secret_key = hashlib.sha256(TELEGRAM_TOKEN.encode()).digest()
    generated_hash = hmac.new(secret_key, check_string.encode(), hashlib.sha256).hexdigest()

    return hmac.compare_digest(generated_hash, data.hash)


@router.get("/telegram", tags=["oauth", "telegram"])
async def start_oauth():
    telegram_login_url = (
        "https://oauth.telegram.org/auth"
        f"?bot_id={os.getenv('TELEGRAM_BOT_ID')}"
        f"&origin={os.getenv('TELEGRAM_ORIGIN')}"
        "&request_access=write"
        f"&return_to={os.getenv('TELEGRAM_ORIGIN')}"
    )
    return RedirectResponse(telegram_login_url)


@router.get("/telegram-connect", tags=["oauth", "telegram"])
async def connect_oauth():
    telegram_login_url = (
        "https://oauth.telegram.org/auth"
        f"?bot_id={os.getenv('TELEGRAM_BOT_ID')}"
        f"&origin={os.getenv('TELEGRAM_ORIGIN')}-connect/"
        "&request_access=write"
    )
    return RedirectResponse(telegram_login_url)


@router.post("/telegram/callback", tags=["oauth", "telegram"])
async def telegram_callback(data: TelegramCallbackSchema, db: AsyncSession = Depends(get_db)):
    verification = await verify_telegram_auth(data)
    if not verification:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid data from Telegram")

    oauth_user = (await db.execute(select(OAuthProfile).where(OAuthProfile.oauth_id == data.id))).scalar_one_or_none()

    if oauth_user:
        user = oauth_user.user
    else:
        user = User(name=f'{data.first_name} {data.last_name}', is_active=True)
        db.add(user)
        await db.commit()
        await db.refresh(user)

        new_profile = OAuthProfile(
            user_id=user.id,
            provider='telegram',
            oauth_id=str(data.id),
            photo=data.photo_url,
            name=f'{data.first_name} {data.last_name}',
        )
        db.add(new_profile)
        await db.commit()
        await db.refresh(new_profile)

    access_token = create_access_token({"sub": str(user.id)})

    return {"token": access_token}


@router.post("/telegram/callback-connect", tags=["oauth", "telegram"])
async def telegram_callback_connect(data: TelegramCallbackConnectSchema, db: AsyncSession = Depends(get_db)):
    if verify_telegram_auth(data):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid data from Telegram")

    real_user = await find_user_by_token(data.token, db)

    if not real_user.email:
        return {
            'message': 'У вашего профиля нет привязанной почты; обратитесь в поддержку',
            'success': False
        }

    oauth_user = (await db.execute(select(OAuthProfile).where(OAuthProfile.oauth_id == data.id))).scalar_one_or_none()

    if oauth_user:
        oauth_user.user_id = real_user.id
    else:
        oauth_user = OAuthProfile(
            user_id=real_user.id,
            provider='telegram',
            oauth_id=str(data.id),
            photo=data.photo_url,
            name=f'{data.first_name} {data.last_name}',
        )
        db.add(oauth_user)

    if not real_user.photo and data.photo_url:
        real_user.photo = data.photo_url

    await db.commit()
    await db.refresh(oauth_user)

    return {
        'message': 'Telegram привязан успешно',
        'success': True
    }
