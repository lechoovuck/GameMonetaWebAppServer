from datetime import timedelta
from typing import Optional

from fastapi import Depends, APIRouter, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from database import get_db
from models.user import User, OAuthProfile

from schemas.user import UserDataResponse, UserChangeData, ChangeEmailData, UserConnectEmailLogin, \
    UserConnectEmailLoginResponse
from utils import oauth2_scheme, find_user_by_token, pwd_context, send_email, create_access_token, verify_token
import jwt

router = APIRouter()


@router.get("/", response_model=UserDataResponse, tags=["profile"])
async def get_user_profile(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    try:
        user = await find_user_by_token(token, db)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid token")

    telegram_profile = (await db.execute(select(OAuthProfile).where(
        OAuthProfile.user_id == user.id and OAuthProfile.provider == "telegram"))).scalar_one_or_none()

    return {
        "data": {
            "id": user.id,
            "email": user.email,
            "photo": user.photo,
            "name": user.name,
            "gender": user.gender,
            "is_active": user.is_active,
            "bonuses": user.bonuses,
            "telegramId": int(telegram_profile.oauth_id) if telegram_profile else None
        }
    }


@router.post("/info", response_model=UserDataResponse, tags=["profile"])
async def change_info(user_data: UserChangeData, token: str = Depends(oauth2_scheme),
                      db: AsyncSession = Depends(get_db)):
    user = await find_user_by_token(token, db)

    user.gender = user_data.gender
    user.name = user_data.name

    await db.commit()
    await db.refresh(user)

    return {
        "data": {
            "id": user.id,
            "email": user.email,
            "photo": user.photo,
            "name": user.name,
            "gender": user.gender,
            "is_active": user.is_active,
            "bonuses": user.bonuses,
        }
    }


@router.post("/connect_email", response_model=UserConnectEmailLoginResponse, tags=["profile"])
async def connect_email(user_data: UserConnectEmailLogin, db: AsyncSession = Depends(get_db)):
    if not user_data.token:
        return {
            'message': 'Вы не авторизованы, пожалуйста, обновите страницу',
            'success': False,
        }
    current_user = await find_user_by_token(user_data.token, db)

    oauth_profile = (
        await db.execute(select(OAuthProfile).where(OAuthProfile.user_id == current_user.id))).scalar_one_or_none()

    if not oauth_profile:
        return {
            'message': 'Вы выполнили вход без использования дополнительных способов входа; сейчас привязка невозможна',
            'success': False,
        }

    if current_user.email or current_user.hashed_password:
        return {
            'message': "К текущему аккаунту уже привязана почта",
            'success': False,
        }

    existing_user = (await db.execute(select(User).where(User.email == user_data.email))).scalar_one_or_none()

    if not existing_user:
        reset_token = create_access_token(
            data={"sub": str(current_user.id), "type": "password_reset"},
            expires_delta=timedelta(minutes=30)
        )

        await send_email(
            recipient_email=user_data.email,
            template_type="email_reset",
            subject="Смена почты",
            email_data={"reset_token": reset_token}
        )

        return {
            'message': f"Подтвердите смену почты в письме",
            'success': True,
        }

    elif not pwd_context.verify(user_data.password, existing_user.hashed_password):
        return {
            'message': "Неправильный пароль, попробуйте снова",
            'success': False,
        }

    oauth_profile.user_id = existing_user.id
    await db.commit()
    await db.refresh(oauth_profile)

    return {
        'message': f"Профиль {oauth_profile.provider} привязан к {existing_user.email}",
        'success': True,
    }


@router.post("/change_email", tags=["profile"])
async def change_email(user_data: ChangeEmailData,
                       authorization: Optional[str] = Header(None),
                       db: AsyncSession = Depends(get_db)):
    scheme, token = authorization.split()
    user = await find_user_by_token(token, db)
    reset_token = create_access_token(
        data={"sub": str(user.id), "type": "email_reset"},
        expires_delta=timedelta(minutes=60)
    )

    await send_email(
        recipient_email=user.email,
        template_type="email_reset",
        subject="Смена почты",
        email_data={"reset_token": reset_token}
    )

    return {'reset_token': reset_token, 'message': 'Успешно'}
