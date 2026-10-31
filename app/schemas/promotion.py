from datetime import date

from pydantic import BaseModel, ConfigDict


class PromotionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None
    conditions: str | None
    starts_at: date | None
    ends_at: date | None
    product_id: int | None
    category: str | None
    source: str
