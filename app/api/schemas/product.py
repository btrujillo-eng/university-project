from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator, model_validator

from app.domain.enums import UnitOfMeasure


class ProductCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=2, max_length=120)
    section_id: int = Field(gt=0)
    price: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    stock: Decimal = Field(ge=0, max_digits=10, decimal_places=3)
    unit_of_measure: UnitOfMeasure
    image_path: str | None = Field(default=None, max_length=255)

    @model_validator(mode="after")
    def validate_unit_stock(self):
        if self.unit_of_measure == UnitOfMeasure.UNIT and self.stock != self.stock.to_integral_value():
            raise ValueError("El stock de productos por unidad debe ser un número entero")
        return self

    @model_validator(mode="after")
    def validate_unit_stock(self):
        if self.unit_of_measure == UnitOfMeasure.UNIT and self.stock != self.stock.to_integral_value():
            raise ValueError("El stock de productos por unidad debe ser un número entero")
        return self


class ProductResponse(BaseModel):
    id: int
    name: str
    section_id: int
    section_name: str | None = None
    price: Decimal
    stock: Decimal
    unit_of_measure: UnitOfMeasure
    image_path: str | None = None


class ProductSectionResponse(BaseModel):
    id: int
    name: str


class ProductPriceUpdateRequest(BaseModel):
    price: Decimal = Field(gt=0, max_digits=10, decimal_places=2)


class ProductStockUpdateRequest(BaseModel):
    stock: Decimal = Field(ge=0, max_digits=10, decimal_places=3)
