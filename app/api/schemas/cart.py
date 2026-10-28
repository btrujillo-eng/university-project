from decimal import Decimal

from pydantic import BaseModel, Field

from app.domain.enums import UnitOfMeasure


class AddCartItemRequest(BaseModel):
    product_id: int = Field(gt=0)
    quantity: int = Field(gt=0, le=1000)


class CartItemResponse(BaseModel):
    product_id: int
    product_name: str
    unit_price: Decimal
    quantity: int
    line_total: Decimal
    unit_of_measure: UnitOfMeasure
    image_path: str | None = None


class CartResponse(BaseModel):
    cart_id: int | None
    items: list[CartItemResponse]
    total: Decimal
