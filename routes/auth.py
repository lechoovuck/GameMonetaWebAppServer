from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from models import TokenBlacklist
from schemas.auth import *
from utils import pwd_context, create_access_token, verify_token, verify_password_reset_token, send_email
from models.user import User
from schemas.user import UserCreate, UserLogin, UserTokenResponse, SessionCheckResponse
from database import get_db

from dotenv import load_dotenv
from datetime import timedelta

load_dotenv()

router = APIRouter()


@router.post("/register", response_model=UserTokenResponse, status_code=status.HTTP_201_CREATED, tags=["auth"])
async def register(user: UserCreate, db: AsyncSession = Depends(get_db)):
    user_db = (await db.execute(select(User).where(User.email == user.email))).scalar_one_or_none()

    if user_db:
        return UserTokenResponse(error='Пользователь с такой почтой уже зарегистрирован')

    new_user = User(
        email=user.email,
        hashed_password=pwd_context.hash(user.password),
        name=user.name
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    token = create_access_token({"sub": str(new_user.id)})

    return UserTokenResponse(token=token)


@router.post("/login", response_model=UserTokenResponse, tags=["auth"])
async def login(user: UserLogin, db: AsyncSession = Depends(get_db)):
    existing_user = (await db.execute(select(User).where(User.email == user.email))).scalar_one_or_none()

    if not existing_user or not pwd_context.verify(user.password, existing_user.hashed_password):
        return UserTokenResponse(error='Неверные почта или пароль')

    token = create_access_token({"sub": str(existing_user.id)})

    return UserTokenResponse(token=token)


@router.get("/check_session", response_model=SessionCheckResponse, tags=["auth"])
async def check_session(authorization: Optional[str] = Header(None)):
    try:
        verify_token(authorization)
        return {"success": True}
    except:
        return {"success": False}


@router.post("/password_reset_request", response_model=InitiatePasswordResetResponse, tags=["auth"])
async def request_password_reset(body: InitiatePasswordResetRequest, db: AsyncSession = Depends(get_db)):
    user = (await db.execute(select(User).where(User.email == body.email))).scalar_one_or_none()

    if not user:
        return InitiatePasswordResetResponse()

    reset_token = create_access_token(
        data={"sub": str(user.id), "type": "password_reset"},
        expires_delta=timedelta(minutes=30)
    )
    email_sent = await send_email(
        recipient_email=body.email,
        template_type="password_reset",
        subject="Смена пароля",
        email_data={"reset_token": reset_token}
    )

    if email_sent:
        return InitiatePasswordResetResponse()
    else:
        return InitiatePasswordResetResponse(message="Возникла ошибка. Попробуйте позже.")


@router.post("/password_reset", response_model=PasswordResetResponse, tags=["auth"])
async def reset_password(body: PasswordResetRequest, db: AsyncSession = Depends(get_db)):
    try:
        payload = await verify_password_reset_token(body.token, db)

        if payload.get("type") != "password_reset":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid token type"
            )

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid token"
            )

        user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        user.hashed_password = pwd_context.hash(body.new_password)
        blacklisted_token = TokenBlacklist(token=body.token, user_id=user_id)
        db.add(blacklisted_token)

        await db.commit()

        return PasswordResetResponse(message="Пароль успешно обновлен", success=True)
    except HTTPException as e:
        return PasswordResetResponse(message=e.detail, success=False)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )


TYPES_EMAIL = ('password_reset', 'email_reset')


@router.post("/check_reset_token", response_model=TokenCheckResponse, tags=["auth"])
async def check_reset_token(body: TokenCheckRequest, db: AsyncSession = Depends(get_db)):
    payload = await verify_password_reset_token(body.token, db)
    try:
        if payload.get("type") not in TYPES_EMAIL:
            return TokenCheckResponse(message="Invalid token type", valid=False)

        if not payload.get("sub"):
            return TokenCheckResponse(message="Invalid token", valid=False)

        return TokenCheckResponse(valid=True)

    except HTTPException as e:
        if e.status_code == 401 and e.detail == "Token already used":
            return TokenCheckResponse(message="Эта ссылка уже использована", valid=False)
        elif e.status_code == 401:
            return TokenCheckResponse(message="Срок действия ссылки истек", valid=False)
        elif e.status_code == 403:
            return TokenCheckResponse(message="Недействительная ссылка", valid=False)
        return TokenCheckResponse(message=e.detail, valid=False)
    except Exception:
        return TokenCheckResponse(message="Недействительная ссылка", valid=False)


@router.post("/email_reset", response_model=EmailResetRes, tags=["auth"])
async def reset_email(request: EmailResetReq, db: AsyncSession = Depends(get_db)):
    try:
        payload = await verify_password_reset_token(request.token, db)
        if payload.get("type") != "email_reset":
            return EmailResetRes(message="Недействительный токен", success=False)

        user_id = payload["sub"]
        user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()

        if not user:
            return EmailResetRes(message="Пользователь не найден", success=False)

        if (await db.execute(select(User).where(User.email == request.new_email))).scalar_one_or_none():
            return EmailResetRes(message="Этот email уже используется", success=False)

        user.email = request.new_email
        await db.commit()
        return EmailResetRes(message="Email успешно изменен", success=True)

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
