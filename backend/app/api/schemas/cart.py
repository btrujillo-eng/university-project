from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import UnitOfMeasure


class AddCartItemRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    product_id: int = Field(gt=0)
    quantity: Decimal = Field(gt=0, max_digits=10, decimal_places=3, le=1000)


class CartItemResponse(BaseModel):
    product_id: int
    product_name: str
    unit_price: Decimal
    quantity: Decimal
    line_total: Decimal
    unit_of_measure: UnitOfMeasure
    image_path: str | None = None


class CartResponse(BaseModel):
    cart_id: int | None
    items: list[CartItemResponse]
    total: Decimal
