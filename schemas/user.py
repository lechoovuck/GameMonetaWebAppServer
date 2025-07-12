from pydantic import BaseModel, EmailStr, ConfigDict, SecretStr
from typing import Annotated, Optional
from enum import Enum


class GenderEnum(str, Enum):
    male = "male"
    female = "female"


class UserBase(BaseModel):
    email: EmailStr
    name: str

    model_config = ConfigDict(from_attributes=True)


class UserLogin(BaseModel):
    email: EmailStr
    password: Annotated[str, SecretStr]


class UserCreate(UserBase):
    password: Annotated[str, SecretStr]


class UserInDB(UserBase):
    id: int
    is_active: bool = True

    model_config = ConfigDict(from_attributes=True)


class UserResponse(UserBase):
    email: Optional[EmailStr] = None
    id: int
    is_active: bool
    gender: Optional[GenderEnum] = None
    photo: Optional[str] = None
    bonuses: int
    telegramId: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class UserDataResponse(BaseModel):
    data: UserResponse


class UserConnectEmailLoginResponse(BaseModel):
    message: str
    success: bool


class UserChangeData(BaseModel):
    gender: GenderEnum
    name: str


class UserTokenResponse(BaseModel):
    token: Optional[str] = None
    error: Optional[str] = None


class SessionCheckResponse(BaseModel):
    success: bool


class UserConnectEmailLogin(UserLogin):
    email: EmailStr
    password: Annotated[str, SecretStr]
    token: Optional[str] = None


class ChangeEmailBody(BaseModel):
    password: str


class ChangeEmailData(BaseModel):
    body: ChangeEmailBody
