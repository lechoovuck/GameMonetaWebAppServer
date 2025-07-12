from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from models.product import Alias as AliasModel
from schemas.alias import AliasesGetAllResponse
from database import get_db

router = APIRouter()


@router.get("/", response_model=AliasesGetAllResponse, tags=["products"])
async def get_all_aliases(db: AsyncSession = Depends(get_db)):
    aliases = (await db.execute(select(AliasModel))).scalars().all()

    return {
        'aliases': aliases,
        'success': len(aliases) > 0
    }
