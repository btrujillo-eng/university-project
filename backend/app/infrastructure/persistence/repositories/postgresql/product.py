import logging
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.ports import IProductRepository
from app.exceptions import (
    ProductAlreadyExistsError,
    ProductDoesNotExistError,
    ProductQuantityInvalidError,
    ProductRegistrationServiceError,
)
from app.infrastructure.dtos import (
    ProductSummary,
    RegisteredProduct,
    RegisterProductData,
    UpdatedProduct,
)
from app.infrastructure.persistence.models import Product

logger = logging.getLogger(__name__)


class ProductRepository(IProductRepository):
    def __init__(self, db_session: AsyncSession) -> None:
        self.db_session = db_session

    def _to_product_data(self, product: Product) -> RegisterProductData:
        return RegisterProductData(
            product_name=product.name,
            section_id=product.section_id,
            price=product.price,
            stock=product.stock,
            unit_of_measure=product.unit_of_measure.value,
            image_path=product.image_path,
        )

    def _to_updated_product(self, product: Product) -> UpdatedProduct:
        return UpdatedProduct(
            id=product.id,
            name=product.name,
            price=product.price,
            stock=product.stock,
            unit_of_measure=product.unit_of_measure.value,
        )

    async def _get_product(self, product_id: int) -> Product:
        product = await self.db_session.get(Product, product_id)
        if product is None:
            raise ProductDoesNotExistError("The product does not exist in the system")
        return product

    async def get_product_by_id(self, product_id: int) -> RegisterProductData | None:
        product = await self.db_session.get(Product, product_id)
        return None if product is None else self._to_product_data(product)

    async def get_product_by_name(self, name: str) -> RegisterProductData | None:
        stmt = select(Product).where(Product.name == name)
        product = await self.db_session.scalar(stmt)
        return None if product is None else self._to_product_data(product)

    async def list_products(
        self,
        search_term: str | None = None,
        section_id: int | None = None,
    ) -> list[ProductSummary]:
        stmt = select(Product).order_by(Product.name)
        if search_term and search_term.strip():
            stmt = stmt.where(Product.name.ilike(f"%{search_term.strip()}%"))
        if section_id is not None:
            stmt = stmt.where(Product.section_id == section_id)
        products = (await self.db_session.scalars(stmt)).all()
        return [
            ProductSummary(
                id=p.id,
                name=p.name,
                section_id=p.section_id,
                price=p.price,
                stock=p.stock,
                unit_of_measure=p.unit_of_measure.value,
                image_path=p.image_path,
            )
            for p in products
        ]

    async def add_product(self, product_data: RegisterProductData) -> RegisteredProduct:
        product = Product(
            name=product_data.product_name,
            section_id=product_data.section_id,
            price=product_data.price,
            unit_of_measure=product_data.unit_of_measure,
            stock=product_data.stock,
            image_path=product_data.image_path,
        )
        try:
            self.db_session.add(product)
            await self.db_session.flush()
            await self.db_session.refresh(product)
            return RegisteredProduct(
                id=product.id,
                product_name=product.name,
                section_id=product.section_id,
                price=product.price,
                stock=product.stock,
                unit_of_measure=product.unit_of_measure.value,
            )
        except IntegrityError as e:
            sqlstate = getattr(e.orig, "sqlstate", None) or getattr(e.orig, "pgcode", None)
            if sqlstate == "23505":
                raise ProductAlreadyExistsError("The product already exists in the system") from e
            logger.exception("Product registration failed")
            raise ProductRegistrationServiceError("Product registration service unavailable") from e

    async def update_price(self, product_id: int, new_price: Decimal) -> UpdatedProduct:
        product = await self._get_product(product_id)
        product.price = new_price
        await self.db_session.flush()
        return self._to_updated_product(product)

    async def update_stock(self, product_id: int, new_stock: Decimal) -> UpdatedProduct:
        new_stock = Decimal(str(new_stock))
        product = await self._get_product(product_id)
        if product.unit_of_measure.value == "unit" and new_stock != new_stock.to_integral_value():
            raise ProductQuantityInvalidError("El stock de productos por unidad debe ser un número entero")
        product.stock = new_stock
        await self.db_session.flush()
        return self._to_updated_product(product)
