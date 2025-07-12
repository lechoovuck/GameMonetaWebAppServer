import hashlib
import hmac
import re

from passlib.context import CryptContext
import jwt
import httpx

from models import TokenBlacklist
from models.user import User
from fastapi.security import OAuth2PasswordBearer
from fastapi import Depends, HTTPException, status, Header
import requests
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from database import get_db
import os
import datetime as dt
from typing import Optional, Literal, Dict, Any
from apscheduler.schedulers.asyncio import AsyncIOScheduler

import atexit

IS_TEST = os.getenv("IS_TEST")

LOGIN_REGEX = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_]*[a-zA-Z0-9]$")
STEAM_LOGIN_TOKEN = os.getenv("STEAM_LOGIN_TOKEN")
STEAM_API_TOKEN = os.getenv("STEAM_API_TOKEN")
STEAM_LOGIN_URL = os.getenv("STEAM_LOGIN_URL")
RESOLVE_VANITY_URL = "https://api.steampowered.com/ISteamUser/ResolveVanityURL/v1/"
GET_PLAYER_SUMMARIES = "https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/"

EMAIL_API = os.getenv("EMAIL_API")

SECRET_KEY = os.getenv("JWT_SECRET")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440

SECRET_DIGI = os.getenv("SECRET_DIGI")

API_LAVA_CREATE = os.getenv("API_LAVA_CREATE")
API_LAVA_TOKEN = os.getenv("API_LAVA_TOKEN")
LAVA_SUCCESS_URL = os.getenv("LAVA_SUCCESS_URL")
LAVA_SHOP_ID = os.getenv("LAVA_SHOP_ID")

url = f'http://195.161.62.92/steam_currency/get_currency_rate?api_key={STEAM_LOGIN_TOKEN}&code='

currencies = {
    "KZT": 0.189490353604604,
    "USD": 98.12,
    "update_time": 1738793134
}

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


async def find_user_by_token(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        sub = payload.get("sub")
        if not sub:
            raise HTTPException(status_code=403, detail="Invalid token payload")
        user = (await db.execute(select(User).where(User.id == sub))).scalar_one_or_none()

        if user is None:
            raise HTTPException(status_code=404, detail="User not found")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=403, detail="Invalid token")


def create_access_token(data: dict, expires_delta: Optional[dt.timedelta] = dt.timedelta(minutes=30)):
    if not SECRET_KEY:
        raise ValueError("JWT_SECRET is not set in environment variables")
    to_encode = data.copy()
    if expires_delta:
        expire = dt.datetime.now(dt.UTC) + expires_delta
    else:
        expire = dt.datetime.now(dt.UTC) + dt.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_jwt(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=403, detail="Invalid token")


def verify_token(authorization: Optional[str] = Header(None)):
    """
    Raises:
        HTTPException.
    """
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing authorization header")

    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authorization scheme")
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authorization format")

    return decode_jwt(token)


async def verify_password_reset_token(token: str = None, db: AsyncSession = Depends(get_db)):
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")

    if (await db.execute(select(TokenBlacklist).where(TokenBlacklist.token == token))).scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token already used")

    return decode_jwt(token)


async def verify_telegram_token(token: str):
    if not os.getenv('TELEGRAM_BOT_TOKEN'):
        raise ValueError("TELEGRAM_BOT_TOKEN not set")
    tg_url = f"https://api.telegram.org/bot{os.getenv('TELEGRAM_BOT_TOKEN')}/getMe"
    async with httpx.AsyncClient() as client:
        response = await client.get(tg_url)
        if response.status_code == 200:
            user_info = response.json()
            if user_info.get("ok"):
                return user_info["result"]
    return None


def is_valid_steam_login(login: str):
    if not (3 <= len(login) <= 32):
        return False
    return bool(LOGIN_REGEX.fullmatch(login))


async def send_email(
        recipient_email: str,
        template_type: Literal['password_reset', 'email_reset', 'transaction', 'activate_profile'],
        subject: str,
        email_data: Dict[str, Any],
        email_api_url: str = f"{EMAIL_API}/create-email/"
) -> bool:
    """
    Запрос для отправки письма.

    Args:
        recipient_email: Получатель.
        template_type: Тип письма.
        subject: Тема письма.
        email_data: Данные для письма. Словари разного содержания в зависимости от типа письма.
        email_api_url: URL сервиса.

    Returns:
        bool: Отправлено ли письмо.

    Raises:
        HTTPException.
    """
    async with httpx.AsyncClient(verify=False, timeout=10.0) as client:
        try:
            response = await client.post(
                email_api_url,
                json={
                    "template_type": template_type,
                    "recipient_email": recipient_email,
                    "subject": subject,
                    "email_data": email_data
                },
                headers={"accept": "application/json"}
            )  # {success: bool, email_id: int}
            response.raise_for_status()
            return response.json().get('success', False)

        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Error communicating with email service: {e.response.text}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"An unexpected error occurred: {str(e)}"
            )


def verify_signature(uuid: str, status: str, signature: str) -> bool:
    message = f"{uuid}:{status}".encode('utf-8')
    computed_signature = hmac.new(
        key=SECRET_DIGI.encode('utf-8'),
        msg=message,
        digestmod=hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(computed_signature, signature)


async def refresh_currencies():
    async with httpx.AsyncClient(verify=False) as client:
        rub_response = await client.get(f'{url}RUB', follow_redirects=True)
        rub_response.raise_for_status()
        rub_response = rub_response.json()['data']

        kzt_response = await client.get(f'{url}KZT', follow_redirects=True)
        kzt_response.raise_for_status()
        kzt_response = kzt_response.json()['data']

        rub_value = rub_response['value']
        kzt_value = kzt_response['value']
        update_time = kzt_response['update_time']

        global currencies
        currencies = {
            "KZT": rub_value / 100,
            "USD": rub_value / kzt_value,
            "update_time": update_time
        }


scheduler = AsyncIOScheduler()
scheduler.add_job(refresh_currencies, 'interval', hours=12)
scheduler.start()
atexit.register(scheduler.shutdown)
