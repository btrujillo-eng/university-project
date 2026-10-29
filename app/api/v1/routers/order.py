from collections.abc import AsyncIterator
import hashlib
from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.payment import get_process_payment
from app.api.schemas.order import (
    CashPaymentUpdateRequest,
    CheckoutRequest,
    CheckoutResponse,
    DigitalReceiptResponse,
    OrderItemResponse,
    OrderResponse,
)
from app.api.schemas.payment import PaymentDataRequest
from app.api.schemas.user import ContactInfoRequest, UserDataRequest
from app.api.v1.routers.user_auth import get_current_user
from app.application import ProcessPaymentUseCase
from app.domain.enums import DeliveryStatus, DiscountStrategy, PaymentMethods, PaymentStatus, TypeCurrency, UserRole
from app.domain.ports.order_repository import IOrderRepository
from app.infrastructure.database_engine import AsyncSessionLocal
from app.infrastructure.dtos.user import AuthenticatedUser
from app.infrastructure.persistence.models import Product, User
from app.infrastructure.persistence.models.order_items import OrderItem
from app.infrastructure.persistence.models.orders import Order
from app.infrastructure.persistence.repositories.postgresql.order import OrderRepository
from app.infrastructure.persistence.repositories.postgresql.cart import CartRepository

router = APIRouter(prefix="/orders", tags=["orders"])
MINIMUM_ORDER_AMOUNT = Decimal("20000.00")
SHIPPING_COST = Decimal("0.00")  # No shipping tariff is defined in the current requirements.


async def get_order_session() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        yield session


def _require_role(user: AuthenticatedUser, role: UserRole) -> None:
    if UserRole(user.user_role) != role:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permisos para esta operación")


def _to_response(order: Order) -> OrderResponse:
    items = [
        OrderItemResponse(
            product_id=item.product_id,
            product_name=item.product.name,
            unit_price=item.unit_price,
            quantity=item.quantity,
            image_path=item.product.image_path,
        )
        for item in order.order_items
    ]
    subtotal = sum((item.unit_price * item.quantity for item in order.order_items), start=Decimal("0.00"))
    return OrderResponse(
        id=order.id,
        user_id=order.user_id,
        customer_name=order.customer_name,
        courier_id=order.courier_id,
        total_price=order.total_price,
        subtotal=subtotal,
        shipping_cost=SHIPPING_COST,
        delivery_status=order.delivery_status,
        payment_method=order.payment_method,
        payment_status=order.payment_status,
        created_at=order.created_at,
        shipping_street=order.shipping_street,
        shipping_neighborhood=order.shipping_neighborhood,
        shipping_department=order.shipping_department,
        shipping_details=order.shipping_details,
        shipping_instructions=order.shipping_instructions,
        shipping_city=order.shipping_city,
        phone_number=order.phone_number,
        items=items,
    )


@router.post("/checkout", response_model=CheckoutResponse, status_code=status.HTTP_201_CREATED)
async def checkout(
    data: CheckoutRequest,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_order_session)],
    payment_use_case: Annotated[ProcessPaymentUseCase, Depends(get_process_payment)],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=16, max_length=255)],
) -> CheckoutResponse:
    _require_role(user, UserRole.CUSTOMER)
    existing_order = await session.scalar(
        select(Order).where(Order.user_id == user.user_id, Order.idempotency_key == idempotency_key)
    )
    if existing_order is not None:
        if existing_order.user_id != user.user_id:
            raise HTTPException(status_code=409, detail="La clave de idempotencia ya fue utilizada")
        raise HTTPException(
            status_code=409,
            detail={"message": "Este checkout ya fue registrado. Consulta tu historial de pedidos.", "order_id": existing_order.id},
        )

    account = await session.get(User, user.user_id)
    if account is None:
        raise HTTPException(status_code=401, detail="La cuenta autenticada ya no existe")

    cart = await CartRepository(session).get_cart_for_update(user.user_id)
    if cart is None or not cart.items:
        await session.rollback()
        raise HTTPException(status_code=422, detail="El carrito está vacío")
    quantities = {item.product_id: item.quantity for item in cart.items}
    statement = select(Product).where(Product.id.in_(quantities)).order_by(Product.id).with_for_update()
    products = list((await session.scalars(statement)).all())
    products_by_id = {product.id: product for product in products}
    missing_ids = set(quantities) - set(products_by_id)
    if missing_ids:
        await session.rollback()
        raise HTTPException(status_code=404, detail={"products_not_found": sorted(missing_ids)})

    for product_id, quantity in quantities.items():
        if products_by_id[product_id].stock < quantity:
            await session.rollback()
            raise HTTPException(status_code=409, detail=f"Stock insuficiente para el producto {product_id}")

    subtotal = sum(
        (products_by_id[product_id].price * quantity for product_id, quantity in quantities.items()),
        start=Decimal("0.00"),
    )
    total = subtotal + SHIPPING_COST
    if total < MINIMUM_ORDER_AMOUNT:
        await session.rollback()
        raise HTTPException(
            status_code=422,
            detail=f"El pedido mínimo es de COP {MINIMUM_ORDER_AMOUNT:.2f}",
        )

    user_data = UserDataRequest(
        first_name=account.first_name,
        middle_name=account.middle_name,
        first_surname=account.first_surname,
        middle_surname=account.middle_surname,
        contact_info=ContactInfoRequest(email=account.email, phone_number=data.shipping.phone_number),
    )
    payment_data = PaymentDataRequest(
        user_data=user_data,
        currency=TypeCurrency.COP,
        discount_type=DiscountStrategy.NODISCOUNT.value,
        transaction_amount=total,
        payment_method=data.payment_method,
        idempotency_key=f"checkout-{user.user_id}-{hashlib.sha256(idempotency_key.encode()).hexdigest()}",
    )
    try:
        payment = await payment_use_case.process(payment_data)
    except Exception:
        await session.rollback()
        raise

    if data.payment_method.method == PaymentMethods.CARD and payment.payment_status != "succeeded":
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={"message": payment.message or "El pago fue rechazado", "transaction_id": payment.transaction_id},
        )

    persisted_payment_status = (
        PaymentStatus.PENDING
        if data.payment_method.method == PaymentMethods.CASH
        else PaymentStatus(payment.payment_status)
    )
    customer_name = " ".join(
        part for part in (account.first_name, account.middle_name, account.first_surname, account.middle_surname) if part
    )
    order = Order(
        user_id=user.user_id,
        idempotency_key=idempotency_key,
        customer_name=customer_name,
        total_price=payment.transaction_amount,
        delivery_status=DeliveryStatus.PENDING,
        payment_method=data.payment_method.method,
        payment_status=persisted_payment_status,
        shipping_street=data.shipping.street,
        shipping_neighborhood=data.shipping.neighborhood,
        shipping_department=data.shipping.department,
        shipping_details=data.shipping.details,
        shipping_instructions=data.shipping.delivery_instructions,
        shipping_city=data.shipping.city,
        phone_number=data.shipping.phone_number,
    )
    session.add(order)
    await session.flush()
    for product_id, quantity in quantities.items():
        product = products_by_id[product_id]
        product.stock -= quantity
        order.order_items.append(
            OrderItem(
                product=product,
                product_id=product.id,
                unit_price=product.price,
                quantity=quantity,
            )
        )
    cart.items.clear()
    await session.commit()
    saved_order = await OrderRepository(session).get_by_id_for_update(order.id)
    if saved_order is None:
        raise HTTPException(status_code=500, detail="No se pudo recuperar el pedido creado")
    order_response = _to_response(saved_order)
    receipt = None
    if data.payment_method.method == PaymentMethods.CARD and payment.payment_status == "succeeded":
        receipt = DigitalReceiptResponse(
            receipt_number=f"REC-{order.id:08d}",
            order_id=order.id,
            issued_at=datetime.now(UTC),
            customer_name=customer_name,
            customer_email=account.email,
            shipping_street=order.shipping_street,
            shipping_neighborhood=order.shipping_neighborhood,
            shipping_department=order.shipping_department,
            shipping_details=order.shipping_details,
            shipping_instructions=order.shipping_instructions,
            shipping_city=order.shipping_city,
            phone_number=order.phone_number,
            payment_method=order.payment_method,
            total_paid=payment.transaction_amount,
            subtotal=subtotal,
            shipping_cost=SHIPPING_COST,
            items=order_response.items,
        )
    return CheckoutResponse(order=order_response, payment=payment, receipt=receipt)


@router.get("/me", response_model=list[OrderResponse])
async def get_my_orders(
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_order_session)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[OrderResponse]:
    _require_role(user, UserRole.CUSTOMER)
    orders = await OrderRepository(session).get_customer_orders(user.user_id, limit, offset)
    return [_to_response(order) for order in orders]


@router.get("/packaging", response_model=list[OrderResponse])
async def get_orders_for_packaging(
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_order_session)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[OrderResponse]:
    _require_role(user, UserRole.PACKAGING_MANAGER)
    orders = await OrderRepository(session).list_all(limit, offset)
    return [_to_response(order) for order in orders]


@router.get("/packaging/pending", response_model=list[OrderResponse])
async def get_orders_pending_packaging(
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_order_session)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[OrderResponse]:
    _require_role(user, UserRole.PACKAGING_MANAGER)
    orders = await OrderRepository(session).list_by_delivery_status(DeliveryStatus.PENDING, limit, offset)
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


@router.post("/{order_id}/assign-courier/{courier_id}", response_model=OrderResponse)
async def assign_courier(
    order_id: int,
    courier_id: int,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_order_session)],
) -> OrderResponse:
    _require_role(user, UserRole.STORE_MANAGER)
    courier = await session.get(User, courier_id)
    if courier is None or courier.user_role != UserRole.COURIER or not courier.is_active:
        raise HTTPException(status_code=404, detail="El domiciliario no existe o está inactivo")
    order = await OrderRepository(session).get_by_id_for_update(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="El pedido no existe")
    if order.delivery_status != DeliveryStatus.PACKAGED:
        raise HTTPException(status_code=409, detail="Solo se pueden asignar pedidos empacados")
    order.courier_id = courier_id
    await session.commit()
    return _to_response(order)


@router.get("/courier/assigned", response_model=list[OrderResponse])
async def get_assigned_orders(
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_order_session)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[OrderResponse]:
    _require_role(user, UserRole.COURIER)
    orders = await OrderRepository(session).list_for_courier(user.user_id, limit, offset)
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
