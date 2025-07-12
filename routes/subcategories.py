from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from database import get_db
from models.subcategory import Subcategory as SubcategoryModel
from schemas.subcategory import Subcategory, SubcategoryUpdate

from models.product import Product as ProductModel
from schemas.product import Product, ProductCreate, ProductListResponse

router = APIRouter()


@router.put("/{uid}", response_model=Subcategory, status_code=status.HTTP_200_OK, tags=["subcategories"])
async def update_subcategory(uid: int, subcategory: SubcategoryUpdate, db: AsyncSession = Depends(get_db)):
    db_subcategory = await db.get(SubcategoryModel, uid)
    if not db_subcategory:
        raise HTTPException(status_code=404, detail="Subcategory not found")

    for key, value in subcategory.model_dump(exclude_unset=True).items():
        setattr(db_subcategory, key, value)

    await db.commit()
    await db.refresh(db_subcategory)
    return db_subcategory


@router.delete("/{uid}", status_code=status.HTTP_204_NO_CONTENT, tags=["subcategories"])
async def delete_subcategory(uid: int, db: AsyncSession = Depends(get_db)) -> None:
    db_subcategory = await db.get(SubcategoryModel, uid)
    if not db_subcategory:
        raise HTTPException(status_code=404, detail="Subcategory not found")

    await db.delete(db_subcategory)
    await db.commit()
    return


@router.get("/{subcategory_id}/products", response_model=ProductListResponse, status_code=status.HTTP_200_OK,
            tags=["products"])
async def get_products(subcategory_id: int, db: AsyncSession = Depends(get_db)):
    db_subcategory = await db.get(SubcategoryModel, subcategory_id)

    if not db_subcategory:
        raise HTTPException(status_code=404, detail="Subcategory not found")

    products = (await db.execute(
        select(ProductModel).where(ProductModel.subcategory_id == subcategory_id))).scalars().scalars().all()

    return {"products": products}


@router.post("/{subcategory_id}/products", response_model=Product, status_code=status.HTTP_201_CREATED,
             tags=["products"])
async def create_product(subcategory_id: int, product: ProductCreate, db: AsyncSession = Depends(get_db)):
    db_subcategory = await db.get(SubcategoryModel, subcategory_id)
    if not db_subcategory:
        raise HTTPException(status_code=404, detail="Subcategory not found")

    new_product = ProductModel(subcategory_id=subcategory_id, **product.model_dump())
    db.add(new_product)
    await db.commit()
    await db.refresh(new_product)
    return new_product
