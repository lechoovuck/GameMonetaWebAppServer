from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.orm import relationship
from database import Base


class TokenBlacklist(Base):
    __tablename__ = "token_blacklist"

    token = Column(String(500), primary_key=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)

    user = relationship("User", back_populates="TokensBlacklisted")
