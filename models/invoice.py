from sqlalchemy import (Column, Integer, String, Enum, TIMESTAMP, CHAR, func, ForeignKey, JSON, Boolean,
                        DECIMAL, Text)
from sqlalchemy.orm import relationship
from uuid import uuid4
from database import Base


class Invoice(Base):
    __tablename__ = "invoices"

    uuid = Column(CHAR(36), primary_key=True, nullable=False, default=lambda: str(uuid4()))

    id = Column(Integer, autoincrement=True, unique=True)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    payment_method = Column(String(50), nullable=False)
    delivery_email = Column(String(255), nullable=True)
    order_info = Column(JSON, nullable=True)
    order_confirm = Column(Boolean, nullable=True, default=False)
    bonus = Column(Integer, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), nullable=False)
    status = Column(Enum("paid", "wait", "canceled", "refunded", "error", "process", "order_ok", "order_error"),
                    default="wait", nullable=False)

    product = relationship("Product", back_populates="invoices")
    user = relationship("User", back_populates="invoices")


class PaymentInvoice(Base):
    __tablename__ = "gamemoneta_transactions"
    __table_args__ = (
        {"schema": "majorofficial"},
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    payment_datetime = Column(TIMESTAMP, server_default=func.current_timestamp(), nullable=False)
    wallet_user_login = Column(String(255), nullable=True)
    gamemoneta_invoice_uuid = Column(String(36), nullable=False, unique=True)
    service_payment_id = Column(String(255), nullable=True)
    code_url = Column(Text, nullable=True)
    status = Column(Enum("paid", "wait", "canceled", "refunded", "error", "process", "order_ok", "order_error"),
                    default="wait", nullable=True)
    amount = Column(DECIMAL(precision=18, scale=2), nullable=True)
