from collections.abc import AsyncIterator
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.cart import AddCartItemRequest, CartItemResponse, CartResponse
from app.api.v1.routers.user_auth import get_current_user
from app.domain.enums import UserRole
from app.exceptions import ProductDoesNotExistError, ProductQuantityInvalidError, ProductStockInsufficientError
from app.infrastructure.database_engine import AsyncSessionLocal
from app.infrastructure.dtos.user import AuthenticatedUser
from app.infrastructure.persistence.models.carts import Cart
from app.infrastructure.persistence.repositories.postgresql.cart import CartRepository

router = APIRouter(prefix="/cart", tags=["shopping cart"])


async def get_cart_session() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        yield session


def _require_customer(user: AuthenticatedUser) -> None:
    if UserRole(user.user_role) != UserRole.CUSTOMER:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo los clientes pueden usar el carrito")


def _to_response(cart: Cart | None) -> CartResponse:
    if cart is None:
        return CartResponse(cart_id=None, items=[], total=Decimal("0.00"))
    items = [
        CartItemResponse(
            product_id=item.product_id,
            product_name=item.product.name,
            unit_price=item.product.price,
            quantity=item.quantity,
            line_total=item.product.price * item.quantity,
            unit_of_measure=item.product.unit_of_measure,
            image_path=item.product.image_path,
        )
        for item in cart.items
    ]
    total = sum((item.line_total for item in items), start=Decimal("0.00"))
    return CartResponse(cart_id=cart.id, items=items, total=total)


@router.get("/", response_model=CartResponse)
async def get_cart(
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_cart_session)],
) -> CartResponse:
    _require_customer(user)
    return _to_response(await CartRepository(session).get_cart(user.user_id))


@router.post("/items", response_model=CartResponse)
async def add_cart_item(
    data: AddCartItemRequest,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_cart_session)],
) -> CartResponse:
    _require_customer(user)
    repository = CartRepository(session)
    try:
        await repository.add_item(user.user_id, data.product_id, data.quantity)
        await session.commit()
        return _to_response(await repository.get_cart(user.user_id))
    except ProductDoesNotExistError as e:
        await session.rollback()
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ProductStockInsufficientError as e:
        await session.rollback()
        raise HTTPException(status_code=409, detail=str(e)) from e
    except ProductQuantityInvalidError as e:
        await session.rollback()
        raise HTTPException(status_code=422, detail=str(e)) from e


@router.delete("/items/{product_id}", response_model=CartResponse)
async def remove_cart_item(
    product_id: int,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_cart_session)],
) -> CartResponse:
    _require_customer(user)
    repository = CartRepository(session)
    removed = await repository.remove_item(user.user_id, product_id)
    if not removed:
        await session.rollback()
        raise HTTPException(status_code=404, detail="El producto no está en el carrito")
    await session.commit()
    return _to_response(await repository.get_cart(user.user_id))
