from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.exceptions import ProductDoesNotExistError, ProductStockInsufficientError
from app.infrastructure.persistence.models.cart_items import CartItem
from app.infrastructure.persistence.models.carts import Cart
from app.infrastructure.persistence.models.products import Product


class CartRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _cart_statement(self):
        return select(Cart).options(selectinload(Cart.items).selectinload(CartItem.product))

    async def get_cart(self, user_id: int) -> Cart | None:
        statement = self._cart_statement().where(Cart.user_id == user_id)
        return await self.session.scalar(statement)

    async def add_item(self, user_id: int, product_id: int, quantity: int) -> None:
        product_statement = select(Product).where(Product.id == product_id).with_for_update()
        product = await self.session.scalar(product_statement)
        if product is None:
            raise ProductDoesNotExistError("El producto no existe")

        cart_statement = self._cart_statement().where(Cart.user_id == user_id).with_for_update()
        cart = await self.session.scalar(cart_statement)
        if cart is None:
            cart = Cart(user_id=user_id)
            self.session.add(cart)
            await self.session.flush()

        existing_item = next((item for item in cart.items if item.product_id == product_id), None)
        new_quantity = quantity + (existing_item.quantity if existing_item is not None else 0)
        if product.stock < new_quantity:
            raise ProductStockInsufficientError(
                f"Stock insuficiente. Disponible: {product.stock}; solicitado: {new_quantity}"
            )
        if existing_item is None:
            cart.items.append(CartItem(product=product, product_id=product_id, quantity=quantity))
        else:
            existing_item.quantity = new_quantity
        await self.session.flush()

    async def remove_item(self, user_id: int, product_id: int) -> bool:
        cart_statement = self._cart_statement().where(Cart.user_id == user_id).with_for_update()
        cart = await self.session.scalar(cart_statement)
        if cart is None:
            return False
        item = next((entry for entry in cart.items if entry.product_id == product_id), None)
        if item is None:
            return False
        await self.session.delete(item)
        await self.session.flush()
        return True
