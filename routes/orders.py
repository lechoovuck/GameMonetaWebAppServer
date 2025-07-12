from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from models.order import Order as OrderModel
from models.order_item import OrderItem as OrderItemModel
from models.user import User as UserModel
from models.product import Product as ProductModel
from schemas.order import Order, OrderCreate, OrderListResponse, OrderItemBase
from database import get_db
from datetime import datetime

router = APIRouter()


@router.post("/", response_model=Order, status_code=status.HTTP_201_CREATED, tags=["orders"])
async def create_order(order: OrderCreate, user_id: int, db: AsyncSession = Depends(get_db)):
    db_user = (await db.execute(select(UserModel).where(UserModel.id == user_id))).scalar_one_or_none()

    if not db_user:
        raise HTTPException(status_code=404, detail="User  not found")

    total_price = 0.0
    order_items = []

    for item in order.items:
        db_product = db.get(ProductModel, item.product_id)
        if not db_product:
            raise HTTPException(status_code=404, detail=f"Product with id {item.product_id} not found")

        item_price = db_product.price
        total_price += item_price * item.quantity

        order_item = OrderItemModel(order_id=0, product_id=item.product_id, quantity=item.quantity, price=item_price)
        order_items.append(order_item)

    new_order = OrderModel(user_id=user_id, order_date=datetime.now(), status="Pending", total_price=total_price)
    db.add(new_order)
    await db.commit()
    await db.refresh(new_order)

    for item in order_items:
        item.order_id = new_order.id
        db.add(item)

    await db.commit()
    return new_order


@router.get("/{user_id}", response_model=OrderListResponse, status_code=status.HTTP_200_OK, tags=["orders"])
async def get_orders(user_id: int, db: AsyncSession = Depends(get_db)):
    db_user = await db.get(UserModel, user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User  not found")

    orders = (await db.execute(select(OrderModel).where(OrderModel.user_id == user_id))).scalars().all()

    return {"orders": orders}
