from sqlalchemy import Column, Integer, String, Text, ForeignKey, DECIMAL, Boolean, Enum
from sqlalchemy.dialects.mssql import JSON
from sqlalchemy.orm import relationship
from database import Base


class ProductOption(Base):
    """
    В силу того, что реализация с фронта предполагает чересчур разнообразные
    интерфейсы, принято решение использовать просто JSON

    TODO: Редактирование из веб-интерфейса
    """
    __tablename__ = 'product_options'

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey('products.id', ondelete='CASCADE'))
    type = Column(Enum('select',
                       'radio',
                       'checkbox',
                       'amount',
                       'deposit',
                       'bonus',
                       'input_text',
                       'input_email',
                       '__parent_toggle',
                       '__parent_radio',
                       'steam_link'), nullable=False)
    option_name = Column(String(50), nullable=False)
    title = Column(String(50), nullable=True)
    cols = Column(Integer, nullable=True)
    items = Column(JSON, nullable=True)
    item = Column(JSON, nullable=True)
    default_value = Column(JSON, nullable=True)
    label = Column(String(50), nullable=True)
    tooltip = Column(String(50), nullable=True)
    description = Column(String(100), nullable=True)
    child_group_name = Column(String(50), nullable=True)
    is_required = Column(Boolean, nullable=True, default=False)
    icon = Column(String(127), nullable=True)
    can_be_disabled = Column(Boolean, nullable=True, default=False)

    product = relationship("Product", back_populates="options")


class ProductDelivery(Base):
    __tablename__ = 'product_delivery'

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey('products.id', ondelete='CASCADE'))
    type = Column(String(50), nullable=False)
    key = Column(String(50), nullable=False)
    is_required = Column(Boolean, nullable=False)
    label = Column(String(50), nullable=False)
    placeholder = Column(String(50), nullable=True)
    value = Column(String(50), nullable=True)
    tooltip = Column(String(50), nullable=True)
    description = Column(String(150), nullable=True)

    product = relationship("Product", back_populates="delivery_inputs")


class Faq(Base):
    __tablename__ = 'faq'
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    question = Column(String(127), nullable=False)
    answer = Column(Text, nullable=False)

    product = relationship("Product", back_populates="faq")


class Product(Base):
    __tablename__ = 'products'

    id = Column(Integer, primary_key=True, index=True)
    subcategory_id = Column(Integer, ForeignKey('subcategories.id'), nullable=False)
    name = Column(String, nullable=False)
    price = Column(DECIMAL, nullable=True)
    description = Column(Text, nullable=True)
    image_url = Column(String, nullable=True)
    preview_image_url = Column(String, nullable=True)

    subcategory = relationship("Subcategory", back_populates="products")
    order_items = relationship("OrderItem", back_populates="product")
    options = relationship("ProductOption", back_populates="product")
    faq = relationship("Faq", back_populates="product")
    delivery_inputs = relationship("ProductDelivery", back_populates="product")
    aliases = relationship("Alias", back_populates="product")
    invoices = relationship("Invoice", back_populates="product")


class Alias(Base):
    __tablename__ = 'aliases'

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    alias = Column(String, nullable=False)

    product = relationship("Product", back_populates="aliases")
