import enum
import datetime as dt

from sqlalchemy import Column, Integer, String, ForeignKey, DECIMAL, DateTime, Enum

from database import Base


class StatusEnum(enum.Enum):
    error = "error"
    cancel = "cancel"
    pending = "pending"
    success = "success"


class LavaWebhook(Base):
    __tablename__ = "lava_invoices"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(String(36), nullable=False)
    order_id = Column(String, ForeignKey('invoices.uuid'), nullable=True)
    status = Column(Enum(StatusEnum), nullable=False)
    pay_time = Column(DateTime, nullable=False, default=dt.datetime.now(dt.UTC))
    amount = Column(DECIMAL(10, 2), nullable=False)
    credited = Column(DECIMAL(10, 2), nullable=False)
    custom_fields = Column(String(127), nullable=False)
