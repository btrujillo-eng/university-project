import logging
from decimal import Decimal
import os
import re
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.schemas.product import (
    ProductCreateRequest,
    ProductPriceUpdateRequest,
    ProductResponse,
    ProductSectionResponse,
    ProductStockUpdateRequest,
)
from app.api.v1.routers.user_auth import get_current_user
from app.domain.enums import UnitOfMeasure, UserRole
from app.exceptions import (
    ProductAlreadyExistsError,
    ProductDoesNotExistError,
    ProductQuantityInvalidError,
    ProductRegistrationServiceError,
)
from app.infrastructure.database_engine import AsyncSessionLocal
from app.infrastructure.dtos import RegisterProductData
from app.infrastructure.dtos.user import AuthenticatedUser
from app.infrastructure.persistence.models import Product, ProductSection
from app.infrastructure.persistence.repositories.postgresql.product import ProductRepository

router = APIRouter(prefix="/products", tags=["products"])
logger = logging.getLogger(__name__)

MEDIA_ROOT = Path(os.getenv("MEDIA_ROOT", "media")).resolve()
PRODUCT_IMAGES_DIR = MEDIA_ROOT / "products"
MAX_IMAGE_BYTES = 5 * 1024 * 1024
ALLOWED_IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
IMAGE_SIGNATURES = {
    "image/jpeg": lambda data: data.startswith(b"\xff\xd8\xff"),
    "image/png": lambda data: data.startswith(b"\x89PNG\r\n\x1a\n"),
    "image/webp": lambda data: len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP",
}


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
        section_name=product.section.name if product.section else None,
        price=product.price,
        stock=product.stock,
        unit_of_measure=product.unit_of_measure,
        image_path=product.image_path,
    )


async def save_product_image(image: UploadFile) -> str:
    content_type = (image.content_type or "").lower()
    if content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Formato de imagen no permitido. Usa JPEG, PNG o WebP.",
        )
    content = await image.read(MAX_IMAGE_BYTES + 1)
    if not content or len(content) > MAX_IMAGE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="La imagen debe pesar entre 1 byte y 5 MB.",
        )
    if not IMAGE_SIGNATURES[content_type](content):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="El contenido del archivo no coincide con su formato de imagen.",
        )
    PRODUCT_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid4().hex}{ALLOWED_IMAGE_TYPES[content_type]}"
    destination = PRODUCT_IMAGES_DIR / filename
    try:
        destination.write_bytes(content)
    except OSError as exc:
        logger.exception("Unable to save product image")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No fue posible guardar la imagen del producto.",
        ) from exc
    return f"/media/products/{filename}"


def remove_product_image(image_path: str | None) -> None:
    if not image_path or not image_path.startswith("/media/products/"):
        return
    filename = image_path.rsplit("/", maxsplit=1)[-1]
    if not re.fullmatch(r"[0-9a-f]{32}\.(jpg|png|webp)", filename):
        return
    try:
        (PRODUCT_IMAGES_DIR / filename).unlink(missing_ok=True)
    except OSError:
        logger.exception("Unable to remove orphaned product image %s", filename)


@router.get("/sections", response_model=list[ProductSectionResponse])
async def list_product_sections(
    session: Annotated[AsyncSession, Depends(get_product_session)],
) -> list[ProductSectionResponse]:
    sections = (await session.scalars(select(ProductSection).order_by(ProductSection.name))).all()
    return [ProductSectionResponse(id=section.id, name=section.name) for section in sections]


@router.get("/", response_model=list[ProductResponse])
async def search_products(
    session: Annotated[AsyncSession, Depends(get_product_session)],
    search: Annotated[str | None, Query(min_length=1, max_length=120)] = None,
    section_id: Annotated[int | None, Query(gt=0)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[ProductResponse]:
    stmt = select(Product).options(selectinload(Product.section)).order_by(Product.name)
    if search and search.strip():
        term = f"%{search.strip()}%"
        stmt = stmt.join(ProductSection).where(
            Product.name.ilike(term) | ProductSection.name.ilike(term)
        )
    if section_id is not None:
        stmt = stmt.where(Product.section_id == section_id)
    stmt = stmt.limit(limit).offset(offset)
    products = (await session.scalars(stmt)).all()
    return [product_response(p) for p in products]


@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    name: Annotated[str, Form(min_length=2, max_length=120)],
    section_id: Annotated[int, Form(gt=0)],
    price: Annotated[str, Form()],
    stock: Annotated[Decimal, Form(ge=0, max_digits=10, decimal_places=3)],
    unit_of_measure: Annotated[UnitOfMeasure, Form()],
    image: Annotated[UploadFile, File()],
    session: Annotated[AsyncSession, Depends(get_product_session)],
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> ProductResponse:
    require_role(user, UserRole.STORE_MANAGER)
    try:
        data = ProductCreateRequest(
            name=name,
            section_id=section_id,
            price=price,
            stock=stock,
            unit_of_measure=unit_of_measure,
        )
    except Exception as exc:
        from pydantic import ValidationError
        if isinstance(exc, ValidationError):
            raise HTTPException(status_code=422, detail=exc.errors(include_url=False)) from exc
        raise

    image_path = await save_product_image(image)
    try:
        registered = await ProductRepository(session).add_product(
            RegisterProductData(
                product_name=data.name,
                section_id=data.section_id,
                price=data.price,
                stock=data.stock,
                unit_of_measure=data.unit_of_measure.value,
                image_path=image_path,
            )
        )
        await session.commit()
        product = await session.scalar(
            select(Product)
            .where(Product.id == registered.id)
            .options(selectinload(Product.section))
        )
        if product is None:
            remove_product_image(image_path)
            raise HTTPException(status_code=500, detail="No se pudo recuperar el producto creado")
        return product_response(product)
    except ProductAlreadyExistsError as exc:
        await session.rollback()
        remove_product_image(image_path)
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ProductRegistrationServiceError as exc:
        await session.rollback()
        remove_product_image(image_path)
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception:
        await session.rollback()
        remove_product_image(image_path)
        raise
    finally:
        await image.close()


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
        product = await session.scalar(
            select(Product).where(Product.id == product_id).options(selectinload(Product.section))
        )
        if product is None:
            raise HTTPException(status_code=404, detail="El producto no existe")
        return product_response(product)
    except ProductDoesNotExistError as exc:
        await session.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ProductQuantityInvalidError as exc:
        await session.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.patch("/{product_id}/stock", response_model=ProductResponse)
async def update_product_stock(
    product_id: int,
    data: ProductStockUpdateRequest,
    session: Annotated[AsyncSession, Depends(get_product_session)],
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> ProductResponse:
    require_role(user, UserRole.WAREHOUSE_MANAGER)
    try:
        await ProductRepository(session).update_stock(product_id, data.stock)
        await session.commit()
        product = await session.scalar(
            select(Product).where(Product.id == product_id).options(selectinload(Product.section))
        )
        if product is None:
            raise HTTPException(status_code=404, detail="El producto no existe")
        return product_response(product)
    except ProductDoesNotExistError as exc:
        await session.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ProductQuantityInvalidError as exc:
        await session.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
