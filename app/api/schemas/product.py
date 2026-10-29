from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import UnitOfMeasure


class ProductCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=2, max_length=120)
    section_id: int = Field(gt=0)
    price: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    stock: int = Field(ge=0)
    unit_of_measure: UnitOfMeasure
    image_path: str | None = Field(default=None, max_length=255)


class ProductResponse(BaseModel):
    id: int
    name: str
    section_id: int
    section_name: str | None = None
    price: Decimal
    stock: int
    unit_of_measure: UnitOfMeasure
    image_path: str | None = None


class ProductSectionResponse(BaseModel):
    id: int
    name: str


class ProductPriceUpdateRequest(BaseModel):
    price: Decimal = Field(gt=0, max_digits=10, decimal_places=2)


class ProductStockUpdateRequest(BaseModel):
    stock: int = Field(ge=0)
