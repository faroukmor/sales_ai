from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ComparisonOperator(StrEnum):
    EQ = "eq"
    GTE = "gte"
    LTE = "lte"


class SpecConstraint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str = Field(min_length=1, max_length=100)
    operator: ComparisonOperator
    value: Decimal


class ProductFilters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: str | None = Field(default=None, min_length=1, max_length=100)
    brand: str | None = Field(default=None, min_length=1, max_length=100)
    min_price: Decimal | None = Field(default=None, ge=0)
    max_price: Decimal | None = Field(default=None, ge=0)
    in_stock_only: bool = False
    spec_constraints: list[SpecConstraint] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def validate_price_range(self) -> "ProductFilters":
        if (
            self.min_price is not None
            and self.max_price is not None
            and self.min_price > self.max_price
        ):
            raise ValueError("min_price must not exceed max_price")
        return self
