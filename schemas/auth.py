from pydantic import BaseModel, EmailStr, SecretStr
from typing import Annotated, Optional


class InitiatePasswordResetRequest(BaseModel):
    email: EmailStr


class InitiatePasswordResetResponse(BaseModel):
    message: Optional[str] = "Ссылка отправлена на почту, если такой пользователь существует"


class PasswordResetRequest(BaseModel):
    token: str
    new_password: str


class PasswordResetResponse(BaseModel):
    message: Optional[str] = None
    success: bool = True


class TokenCheckRequest(BaseModel):
    token: str


class TokenCheckResponse(BaseModel):
    message: Optional[str] = None
    valid: bool = True


class EmailResetReq(BaseModel):
    token: str
    new_email: EmailStr


class EmailResetRes(BaseModel):
    message: Optional[str] = None
    success: bool = False
