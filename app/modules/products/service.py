from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, NotFoundException
from app.modules.products.models import Product
from app.modules.products.repository import product_repo
from app.modules.products.schemas import ProductCreate, ProductUpdate
from app.modules.search.utils import update_product_search_vector


async def get_product_by_id(session: AsyncSession, product_id: int) -> Product | None:
    return await product_repo.get(session, id=product_id)


async def get_product_by_sku(session: AsyncSession, sku: str) -> Product | None:
    return await product_repo.get_by_sku(session, sku=sku)


async def get_products(session: AsyncSession, skip: int = 0, limit: int = 100) -> list[Product]:
    return await product_repo.get_multi(session, skip=skip, limit=limit)


async def get_products_by_category(
    session: AsyncSession, category: str, skip: int = 0, limit: int = 100
) -> list[Product]:
    return await product_repo.get_by_category(session, category, skip=skip, limit=limit)


async def get_products_count(session: AsyncSession) -> int:
    return await product_repo.count(session)


async def get_products_count_by_category(session: AsyncSession, category: str) -> int:
    return await product_repo.count_by_category(session, category)


async def create_product(session: AsyncSession, data: ProductCreate) -> Product:
    existing = await product_repo.get_by_sku(session, sku=data.sku)
    if existing:
        raise ConflictException(f"Product with SKU '{data.sku}' already exists")
    product = await product_repo.create(session, data=data)
    update_product_search_vector(product)
    return product


async def update_product(session: AsyncSession, product_id: int, data: ProductUpdate) -> Product:
    product = await product_repo.get(session, id=product_id)
    if not product:
        raise NotFoundException(f"Product with id {product_id} not found")
    product = await product_repo.update(session, instance=product, data=data)
    update_product_search_vector(product)
    return product


async def delete_product(session: AsyncSession, product_id: int) -> Product:
    product = await product_repo.get(session, id=product_id)
    if not product:
        raise NotFoundException(f"Product with id {product_id} not found")
    return await product_repo.delete(session, id=product_id)
