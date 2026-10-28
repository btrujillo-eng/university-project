from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.order import CashPaymentUpdateRequest, OrderItemResponse, OrderResponse
from app.api.v1.routers.user_auth import get_current_user
from app.domain.enums import DeliveryStatus, PaymentMethods, PaymentStatus, UserRole
from app.domain.ports.order_repository import IOrderRepository
from app.infrastructure.database_engine import AsyncSessionLocal
from app.infrastructure.dtos.user import AuthenticatedUser
from app.infrastructure.persistence.models.orders import Order
from app.infrastructure.persistence.repositories.postgresql.order import OrderRepository

router = APIRouter(prefix="/orders", tags=["orders"])


async def get_order_session() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        yield session


def _require_role(user: AuthenticatedUser, role: UserRole) -> None:
    if UserRole(user.user_role) != role:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permisos para esta operación")


def _to_response(order: Order) -> OrderResponse:
    return OrderResponse(
        id=order.id,
        user_id=order.user_id,
        courier_id=order.courier_id,
        total_price=order.total_price,
        delivery_status=order.delivery_status,
        payment_method=order.payment_method,
        payment_status=order.payment_status,
        created_at=order.created_at,
        items=[
            OrderItemResponse(
                product_id=item.product_id,
                product_name=item.product.name,
                unit_price=item.unit_price,
                quantity=item.quantity,
            )
            for item in order.order_items
        ],
    )


@router.get("/me", response_model=list[OrderResponse])
async def get_my_orders(
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_order_session)],
) -> list[OrderResponse]:
    _require_role(user, UserRole.CUSTOMER)
    orders = await OrderRepository(session).get_customer_orders(user.user_id)
    return [_to_response(order) for order in orders]


@router.get("/packaging/pending", response_model=list[OrderResponse])
async def get_orders_pending_packaging(
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_order_session)],
) -> list[OrderResponse]:
    _require_role(user, UserRole.PACKAGING_MANAGER)
    orders = await OrderRepository(session).list_by_delivery_status(DeliveryStatus.PENDING)
    return [_to_response(order) for order in orders]


@router.post("/{order_id}/packaged", response_model=OrderResponse)
async def mark_order_packaged(
    order_id: int,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_order_session)],
) -> OrderResponse:
    _require_role(user, UserRole.PACKAGING_MANAGER)
    repository: IOrderRepository = OrderRepository(session)
    order = await repository.get_by_id_for_update(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="El pedido no existe")
    if order.delivery_status != DeliveryStatus.PENDING:
        raise HTTPException(status_code=409, detail="El pedido no está pendiente de empaque")
    order.delivery_status = DeliveryStatus.PACKAGED
    await session.commit()
    return _to_response(order)


@router.get("/courier/assigned", response_model=list[OrderResponse])
async def get_assigned_orders(
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_order_session)],
) -> list[OrderResponse]:
    _require_role(user, UserRole.COURIER)
    orders = await OrderRepository(session).list_for_courier(user.user_id)
    return [_to_response(order) for order in orders]


@router.patch("/{order_id}/delivery-status", response_model=OrderResponse)
async def update_delivery_status(
    order_id: int,
    new_status: DeliveryStatus,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_order_session)],
) -> OrderResponse:
    _require_role(user, UserRole.COURIER)
    order = await OrderRepository(session).get_by_id_for_update(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="El pedido no existe")
    if order.courier_id != user.user_id:
        raise HTTPException(status_code=403, detail="El pedido no está asignado a este domiciliario")
    allowed_transitions = {
        DeliveryStatus.PACKAGED: DeliveryStatus.IN_TRANSIT,
        DeliveryStatus.IN_TRANSIT: DeliveryStatus.DELIVERED,
    }
    if allowed_transitions.get(order.delivery_status) != new_status:
        raise HTTPException(status_code=409, detail="Transición de estado de entrega no permitida")
    order.delivery_status = new_status
    await session.commit()
    return _to_response(order)


@router.patch("/{order_id}/cash-payment", response_model=OrderResponse)
async def update_cash_payment_status(
    order_id: int,
    data: CashPaymentUpdateRequest,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_order_session)],
) -> OrderResponse:
    _require_role(user, UserRole.COURIER)
    order = await OrderRepository(session).get_by_id_for_update(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="El pedido no existe")
    if order.courier_id != user.user_id:
        raise HTTPException(status_code=403, detail="El pedido no está asignado a este domiciliario")
    if order.payment_method != PaymentMethods.CASH:
        raise HTTPException(status_code=409, detail="Solo se puede actualizar el pago de pedidos en efectivo")
    if data.payment_status != PaymentStatus.SUCCEDED:
        raise HTTPException(status_code=422, detail="El domiciliario solo puede confirmar un pago recibido")
    order.payment_status = PaymentStatus.SUCCEDED
    await session.commit()
    return _to_response(order)
