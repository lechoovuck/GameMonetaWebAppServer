import datetime as dt

from sqlalchemy import Column, Integer, String, ForeignKey, DECIMAL, DateTime
from sqlalchemy.orm import relationship
from database import Base


class Order(Base):
    __tablename__ = 'orders'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    order_date = Column(DateTime, default=dt.datetime.now(dt.UTC))
    status = Column(String, nullable=False)
    total_price = Column(DECIMAL(10, 2), nullable=False)

    order_items = relationship("OrderItem", back_populates="order")
