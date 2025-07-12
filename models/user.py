from sqlalchemy import Column, Integer, String, Boolean, Enum, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from database import Base
import enum


class GenderEnum(enum.Enum):
    male = "male"
    female = "female"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=True)
    hashed_password = Column(String(255), nullable=True)
    name = Column(String(50), nullable=True)
    gender = Column(Enum(GenderEnum), nullable=True, default=GenderEnum.male)
    bonuses = Column(Integer, default=0)
    photo = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)

    oauth_profiles = relationship("OAuthProfile", back_populates="user")
    invoices = relationship("Invoice", back_populates="user")
    TokensBlacklisted = relationship("TokenBlacklist", back_populates="user")


class OAuthProviderEnum(enum.Enum):
    telegram = "telegram"
    google = "google"
    vk = "vk"


class OAuthProfile(Base):
    __tablename__ = "oauth_profiles"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    provider = Column(Enum(OAuthProviderEnum), nullable=False)
    oauth_id = Column(String(255), nullable=False)
    photo = Column(String(255), nullable=True)
    name = Column(String(50), nullable=True)

    __table_args__ = (UniqueConstraint("provider", "oauth_id"),)
    user = relationship("User", back_populates="oauth_profiles")