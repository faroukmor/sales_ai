from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class ProductSpecRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    key: str
    value_text: str | None
    value_num: Decimal | None
    unit: str | None


class ProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    category: str
    brand: str | None
    description: str | None
    price: Decimal | None
    currency: str
    in_stock: bool | None
    url: str | None
    specs: list[ProductSpecRead]
