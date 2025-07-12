from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from database import get_db

from models.category import Category as CategoryModel
from schemas.category import Category, CategoryCreate, CategoryUpdate, CategoryListResponse

from models.subcategory import Subcategory as SubcategoryModel
from schemas.subcategory import Subcategory, SubcategoryCreate, SubcategoryListResponse

router = APIRouter()


@router.get("/", response_model=CategoryListResponse, status_code=status.HTTP_200_OK, tags=["categories"])
async def get_categories(db: AsyncSession = Depends(get_db)) -> CategoryListResponse:
    categories = (await db.execute(select(CategoryModel))).scalars().all()
    return CategoryListResponse(categories=categories)


@router.post("/", response_model=Category, status_code=status.HTTP_201_CREATED, tags=["categories"])
async def create_category(category: CategoryCreate, db: AsyncSession = Depends(get_db)) -> Category:
    new_category = CategoryModel(**category.model_dump())
    db.add(new_category)
    await db.commit()
    await db.refresh(new_category)
    return new_category


@router.put("/{uid}", response_model=Category, status_code=status.HTTP_200_OK, tags=["categories"])
async def update_category(uid: int, category: CategoryUpdate, db: AsyncSession = Depends(get_db)) -> Category:
    db_category = db.get(CategoryModel, uid)
    if not db_category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    for key, value in category.model_dump(exclude_unset=True).items():
        setattr(db_category, key, value)

    await db.commit()
    await db.refresh(db_category)
    return Category.model_validate(db_category)


@router.delete("/{uid}", status_code=status.HTTP_204_NO_CONTENT, tags=["categories"])
async def delete_category(uid: int, db: AsyncSession = Depends(get_db)) -> None:
    db_category = db.get(CategoryModel, uid)
    if not db_category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    await db.delete(db_category)
    await db.commit()
    return


@router.get("/{category_id}/subcategories", response_model=SubcategoryListResponse, status_code=status.HTTP_200_OK,
            tags=["subcategories"])
async def get_subcategories(category_id: int, db: AsyncSession = Depends(get_db)):
    db_category = (await db.execute(select(CategoryModel).where(CategoryModel.id == category_id))).scalars().first()
    if not db_category:
        raise HTTPException(status_code=404, detail="Category not found")

    subcategories = (
        await db.execute(
            select(SubcategoryModel)
            .where(SubcategoryModel.category_id == category_id)
            .options(joinedload(SubcategoryModel.category))
        )
    ).scalars().all()

    return {"subcategories": subcategories}


@router.post("/{category_id}/subcategories", response_model=Subcategory, status_code=status.HTTP_201_CREATED,
             tags=["subcategories"])
async def create_subcategory(category_id: int, subcategory: SubcategoryCreate, db: AsyncSession = Depends(get_db)):
    db_category = (await db.execute(select(CategoryModel).where(CategoryModel.id == category_id))).scalar_one_or_none()

    if not db_category:
        raise HTTPException(status_code=404, detail="Category not found")

    new_subcategory = SubcategoryModel(category_id=category_id, **subcategory.model_dump())
    db.add(new_subcategory)
    await db.commit()
    await db.refresh(new_subcategory)
    return new_subcategory
