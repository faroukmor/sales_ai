# models/product.py
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Spec:
    """مواصفة واحدة لمنتج، مثل ram_gb = 16."""
    key: str
    value_text: str | None = None
    value_num: float | None = None
    unit: str | None = None


@dataclass(frozen=True)
class Product:
    id: int
    name: str
    category: str
    currency: str
    brand: str | None = None
    price: float | None = None
    in_stock: bool | None = None
    url: str | None = None
    specs: dict[str, Spec] = field(default_factory=dict)
    is_test_data: bool = False

    def get_spec(self, key: str) -> Spec | None:
        return self.specs.get(key)
