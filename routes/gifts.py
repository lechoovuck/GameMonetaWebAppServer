from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload, selectinload

from models import Subcategory as SubcategoryModel
from models.product import Product as ProductModel, ProductOption as ProductOptionModel, ProductOption, Product, Alias
from schemas.product import GiftListGetAllResponse, GiftGetByIdResponse, BatchGiftCreateRequest, BatchGiftCreateResponse
from database import get_db
from utils import currencies

router = APIRouter()


@router.get("/", response_model=GiftListGetAllResponse, tags=["gifts"])
async def get_all_gifts(db: AsyncSession = Depends(get_db)):
    gifts = (
        await db.execute(
            select(ProductModel).where(ProductModel.subcategory_id == 2)
            .options(
                joinedload(ProductModel.subcategory).joinedload(SubcategoryModel.category),
                selectinload(ProductModel.aliases),
                selectinload(ProductModel.options),
            )
        )
    ).unique().scalars().all()

    return {
        'gifts': list(gifts),
        'success': len(list(gifts)) > 0
    }


@router.get("/{uuid}", response_model=GiftGetByIdResponse, tags=["gifts"])
async def get_gift_by_id(uuid: int, db: AsyncSession = Depends(get_db)):
    db_gift = (
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
    if not db_gift:
        raise HTTPException(status_code=404, detail="Product not found")

    return {'data': db_gift, 'success': True, 'currencies': currencies}


@router.post("/batch_gifts", response_model=BatchGiftCreateResponse, tags=["gifts"])
async def create_batch_gifts(request: BatchGiftCreateRequest, db: AsyncSession = Depends(get_db)):
    try:
        created_product_ids = []

        async with db.begin():
            for gift in request.gifts:
                product = Product(
                    subcategory_id=7,
                    name=gift.name,
                    description=gift.description,
                    image_url=f'https://cdn.cloudflare.steamstatic.com/steam/apps/{gift.steam_game_id}/library_600x900.jpg',
                    preview_image_url=f'https://cdn.cloudflare.steamstatic.com/steam/apps/{gift.steam_game_id}/capsule_616x353.jpg',
                    price=None
                )
                db.add(product)
                await db.flush()

                created_product_ids.append(product.id)

                if gift.options:
                    for opt in gift.options:
                        product_option = ProductOption(
                            product_id=product.id,
                            type=opt.type,
                            option_name=opt.option_name,
                            title=opt.title,
                            cols=opt.cols,
                            items=opt.items,
                            item=opt.item,
                            default_value=opt.default_value,
                            label=opt.label,
                            tooltip=opt.tooltip,
                            description=opt.description,
                            child_group_name=opt.child_group_name,
                            is_required=opt.is_required,
                            icon=opt.icon,
                            can_be_disabled=opt.can_be_disabled
                        )
                        db.add(product_option)

                if gift.aliases:
                    for alias_str in gift.aliases:
                        alias = Alias(
                            product_id=product.id,
                            alias=alias_str
                        )
                        db.add(alias)

            await db.commit()

        return {"success": True, "created_product_ids": created_product_ids}

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create gifts: {str(e)}")
