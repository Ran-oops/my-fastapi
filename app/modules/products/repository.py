from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repository import BaseRepository
from app.modules.products.models import Product
from app.modules.products.schemas import ProductCreate, ProductUpdate


class ProductRepository(BaseRepository[Product, ProductCreate, ProductUpdate]):
    async def get_by_sku(self, session: AsyncSession, sku: str) -> Product | None:
        result = await session.execute(select(Product).where(Product.sku == sku))
        return result.scalar_one_or_none()

    async def get_by_category(
        self, session: AsyncSession, category: str, skip: int = 0, limit: int = 100
    ) -> list[Product]:
        result = await session.execute(
            select(Product).where(Product.category == category).order_by(Product.id.desc()).offset(skip).limit(limit)
        )
        return list(result.scalars().all())


product_repo = ProductRepository(Product)
