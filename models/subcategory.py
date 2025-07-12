from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from database import Base


class Subcategory(Base):
    __tablename__ = 'subcategories'

    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(Integer, ForeignKey('categories.id'), nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)

    category = relationship("Category", back_populates="subcategories")
    products = relationship("Product", back_populates="subcategory")
