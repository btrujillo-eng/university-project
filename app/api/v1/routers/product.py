from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.product import (
    ProductCreateRequest,
    ProductPriceUpdateRequest,
    ProductResponse,
    ProductStockUpdateRequest,
)
from app.api.v1.routers.user_auth import get_current_user
from app.domain.enums import UserRole
from app.exceptions import (
    ProductAlreadyExistsError,
    ProductDoesNotExistError,
    ProductRegistrationServiceError,
)
from app.infrastructure.database_engine import AsyncSessionLocal
from app.infrastructure.dtos import RegisterProductData
from app.infrastructure.dtos.user import AuthenticatedUser
from app.infrastructure.persistence.models import Product
from app.infrastructure.persistence.repositories.postgresql.product import ProductRepository

router = APIRouter(prefix="/products", tags=["products"])


async def get_product_session() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        yield session


def require_role(user: AuthenticatedUser, *roles: UserRole) -> None:
    if UserRole(user.user_role) not in roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para esta operación",
        )


def product_response(product: Product) -> ProductResponse:
    return ProductResponse(
        id=product.id,
        name=product.name,
        section_id=product.section_id,
        price=product.price,
        stock=product.stock,
        unit_of_measure=product.unit_of_measure,
        image_path=product.image_path,
    )


@router.get("/", response_model=list[ProductResponse])
async def search_products(
    session: Annotated[AsyncSession, Depends(get_product_session)],
    search: Annotated[str | None, Query(min_length=1, max_length=120)] = None,
    section_id: Annotated[int | None, Query(gt=0)] = None,
) -> list[ProductResponse]:
    products = await ProductRepository(session).list_products(search, section_id)
    return [
        ProductResponse(
            id=p.id,
            name=p.name,
            section_id=p.section_id,
            price=p.price,
            stock=p.stock,
            unit_of_measure=p.unit_of_measure,
            image_path=p.image_path,
        )
        for p in products
    ]


@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    data: ProductCreateRequest,
    session: Annotated[AsyncSession, Depends(get_product_session)],
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> ProductResponse:
    require_role(user, UserRole.STORE_MANAGER)
    repository = ProductRepository(session)
    try:
        registered = await repository.add_product(
            RegisterProductData(
                product_name=data.name,
                section_id=data.section_id,
                price=data.price,
                stock=data.stock,
                unit_of_measure=data.unit_of_measure.value,
                image_path=data.image_path,
            )
        )
        await session.commit()
        product = await session.get(Product, registered.id)
        if product is None:
            raise HTTPException(status_code=500, detail="No se pudo recuperar el producto creado")
        return product_response(product)
    except ProductAlreadyExistsError as e:
        await session.rollback()
        raise HTTPException(status_code=409, detail=str(e)) from e
    except ProductRegistrationServiceError as e:
        await session.rollback()
        raise HTTPException(status_code=503, detail=str(e)) from e


@router.patch("/{product_id}/price", response_model=ProductResponse)
async def update_product_price(
    product_id: int,
    data: ProductPriceUpdateRequest,
    session: Annotated[AsyncSession, Depends(get_product_session)],
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> ProductResponse:
    require_role(user, UserRole.STORE_MANAGER)
    try:
        await ProductRepository(session).update_price(product_id, data.price)
        await session.commit()
        product = await session.get(Product, product_id)
        if product is None:
            raise HTTPException(status_code=404, detail="El producto no existe")
        return product_response(product)
    except ProductDoesNotExistError as e:
        await session.rollback()
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.patch("/{product_id}/stock", response_model=ProductResponse)
async def update_product_stock(
    product_id: int,
    data: ProductStockUpdateRequest,
    session: Annotated[AsyncSession, Depends(get_product_session)],
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> ProductResponse:
    require_role(user, UserRole.WAREHOUSE_MANAGER, UserRole.STORE_MANAGER)
    try:
        await ProductRepository(session).update_stock(product_id, data.stock)
        await session.commit()
        product = await session.get(Product, product_id)
        if product is None:
            raise HTTPException(status_code=404, detail="El producto no existe")
        return product_response(product)
    except ProductDoesNotExistError as e:
        await session.rollback()
        raise HTTPException(status_code=404, detail=str(e)) from e
