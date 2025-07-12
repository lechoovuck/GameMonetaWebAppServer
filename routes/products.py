from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload, selectinload

from models.product import Product as ProductModel, ProductOption as ProductOptionModel
from models.subcategory import Subcategory as SubcategoryModel
from schemas.product import Product, ProductUpdate, ProductListGetAllResponse, ProductGetByIdResponse, ProductFull, \
    ProductCreate, ProductOptionBase
from database import get_db
from utils import currencies

router = APIRouter()


@router.post("/", response_model=ProductFull, status_code=status.HTTP_201_CREATED, tags=["products"])
async def create_product(product_data: ProductCreate, db: AsyncSession = Depends(get_db)):
    try:
        db_product = ProductModel(
            name=product_data.name,
            description=product_data.description,
            price=product_data.price,
            image_url=product_data.image_url,
            subcategory_id=product_data.subcategory_id
        )
        db.add(db_product)
        await db.flush()

        if hasattr(product_data, 'options') and product_data.options:
            for option in product_data.options:
                db_option = ProductOptionModel(
                    product_id=db_product.id,
                    option_name=option.option_name,
                    title=option.title,
                    cols=option.cols,
                    child_group_name=option.child_group_name,
                    type=option.type,
                    items=option.items,
                    item=option.item,
                    default_value=option.default_value,
                    label=option.label,
                    tooltip=option.tooltip,
                    description=option.description,
                    icon=option.icon,
                    is_required=option.is_required,
                    can_be_disabled=option.can_be_disabled
                )
                db.add(db_option)

        await db.commit()
        await db.refresh(db_product, attribute_names=["options"])

        return db_product

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating product: {str(e)}")


@router.put("/{uid}/options/", response_model=ProductFull, status_code=status.HTTP_200_OK, tags=["products"])
async def update_product_options(
        uid: int,
        options_data: List[ProductOptionBase],
        db: AsyncSession = Depends(get_db)
):
    try:
        result = await db.execute(
            select(ProductModel)
            .where(ProductModel.id == uid)
            .options(selectinload(ProductModel.options))
        )
        db_product = result.unique().scalar_one_or_none()
        if not db_product:
            raise HTTPException(status_code=404, detail="Product not found")

        existing_options = {option.option_name: option for option in db_product.options}

        for option_data in options_data:
            if option_data.option_name in existing_options:
                db_option = existing_options[option_data.option_name]
                for key, value in option_data.model_dump(exclude_unset=True).items():
                    setattr(db_option, key, value)
            else:
                db_option = ProductOptionModel(
                    product_id=uid,
                    **option_data.model_dump(exclude_unset=True)
                )
                db.add(db_option)

        await db.commit()
        await db.refresh(db_product, attribute_names=["options"])

        return db_product

    except HTTPException as e:
        raise e
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating product options: {str(e)}")


@router.put("/{uid}", response_model=Product, status_code=status.HTTP_200_OK, tags=["products"])
async def update_product(uid: int, product: ProductUpdate, db: AsyncSession = Depends(get_db)):
    db_product = await db.get(ProductModel, uid)
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")

    for key, value in product.model_dump().items():
        setattr(db_product, key, value)

    await db.commit()
    await db.refresh(db_product)
    return db_product


@router.delete("/{uid}", status_code=status.HTTP_204_NO_CONTENT, tags=["products"])
async def delete_product(uid: int, db: AsyncSession = Depends(get_db)):
    db_product = await db.get(ProductModel, uid)
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")

    await db.delete(db_product)
    await db.commit()
    return


@router.get("/", response_model=ProductListGetAllResponse, tags=["products"])
async def get_all_products(db: AsyncSession = Depends(get_db)):
    products = (
        await db.execute(
            select(ProductModel)
            .options(
                joinedload(ProductModel.subcategory).joinedload(SubcategoryModel.category),
                selectinload(ProductModel.aliases),
                selectinload(ProductModel.options),
            )
        )
    ).unique().scalars().all()

    return {
        'products': list(products),
        'success': len(list(products)) > 0
    }


@router.get("/{uuid}", response_model=ProductGetByIdResponse, tags=["products"])
async def get_product_by_id(uuid: int, db: AsyncSession = Depends(get_db)):
    db_product = (
        await db.execute(
            select(ProductModel)
            .where(ProductModel.id == uuid)
            .options(
                joinedload(ProductModel.subcategory).joinedload(SubcategoryModel.category),
                joinedload(ProductModel.options),
                joinedload(ProductModel.delivery_inputs),
                joinedload(ProductModel.faq),
                joinedload(ProductModel.aliases),
            )
        )
    ).unique().scalar_one_or_none()
    if not db_product or (db_product.subcategory and db_product.subcategory.category.id == 2):
        raise HTTPException(status_code=404, detail="Product not found")

    return {'data': db_product, 'success': True, 'currencies': currencies}
