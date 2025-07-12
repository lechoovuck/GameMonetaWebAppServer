from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from models.user import User as UserModel
from schemas.user import UserResponse
from database import get_db

router = APIRouter()


@router.get("/{user_id}", response_model=UserResponse, tags=["users"])
async def get_user(user_id: int, db: AsyncSession = Depends(get_db)):
    user = await db.get(UserModel, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User  not found")
    return user
