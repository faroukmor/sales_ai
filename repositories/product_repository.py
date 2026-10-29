# repositories/product_repository.py
import sqlite3

from core.config import MAX_PRODUCT_RESULTS
from models.product import Product, Spec
from models.query_plan import Comparison, ProductFilters

# المشغّلات لا يمكن تمريرها كمعاملات (?)، لذلك نأخذها من قائمة بيضاء مغلقة فقط.
_OPERATORS = {
    Comparison.GTE: ">=",
    Comparison.LTE: "<=",
    Comparison.EQ: "=",
}

_PRODUCT_COLUMNS = (
    "p.id, p.name, p.category, p.brand, p.price, "
    "p.currency, p.in_stock, p.url, p.is_test_data"
)


class ProductRepository:
    """الوصول إلى بيانات المنتجات المنظَّمة. قراءة فقط، بلا LLM وبلا embeddings."""

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    # ---------- الواجهة العامة ----------

    def search(
        self, filters: ProductFilters, limit: int = MAX_PRODUCT_RESULTS
    ) -> list[Product]:
        if limit < 1:
            raise ValueError("limit must be >= 1")

        where, params = self._build_where(filters)
        sql = (
            f"SELECT {_PRODUCT_COLUMNS} FROM products p {where} "
            "ORDER BY (p.price IS NULL), p.price ASC, p.id ASC LIMIT ?"
        )
        rows = self._query(sql, (*params, limit))
        return self._rows_to_products(rows)

    def get_by_id(self, product_id: int) -> Product | None:
        rows = self._query(
            f"SELECT {_PRODUCT_COLUMNS} FROM products p WHERE p.id = ?",
            (product_id,),
        )
        products = self._rows_to_products(rows)
        return products[0] if products else None

    def find_by_name(self, ref: str, limit: int = 5) -> list[Product]:
        """يطابق اسم منتج: التطابق التام أولًا، وإلا تطابق جزئي. للمقارنة."""
        ref = ref.strip()
        if not ref:
            return []
        exact = self._query(
            f"SELECT {_PRODUCT_COLUMNS} FROM products p "
            "WHERE p.name = ? COLLATE NOCASE ORDER BY p.id LIMIT ?",
            (ref, limit),
        )
        if exact:
            return self._rows_to_products(exact)
        escaped = ref.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        partial = self._query(
            f"SELECT {_PRODUCT_COLUMNS} FROM products p "
            "WHERE p.name LIKE ? ESCAPE '\\' ORDER BY p.id LIMIT ?",
            (f"%{escaped}%", limit),
        )
        return self._rows_to_products(partial)

    def list_brands(self) -> list[str]:
        rows = self._query(
            "SELECT DISTINCT brand FROM products WHERE brand IS NOT NULL ORDER BY brand"
        )
        return [row["brand"] for row in rows]

    # ---------- بناء الاستعلام ----------

    @staticmethod
    def _build_where(filters: ProductFilters) -> tuple[str, list]:
        clauses: list[str] = []
        params: list = []

        if filters.category is not None:
            clauses.append("p.category = ? COLLATE NOCASE")
            params.append(filters.category)
        if filters.brand is not None:
            clauses.append("p.brand = ? COLLATE NOCASE")
            params.append(filters.brand)
        # NULL لا يحقق أي مقارنة في SQL: منتج بلا سعر لا يظهر في نطاق السعر.
        if filters.min_price is not None:
            clauses.append("p.price >= ?")
            params.append(filters.min_price)
        if filters.max_price is not None:
            clauses.append("p.price <= ?")
            params.append(filters.max_price)
        if filters.in_stock_only:
            clauses.append("p.in_stock = 1")

        for constraint in filters.spec_constraints:
            op = _OPERATORS.get(constraint.op)
            if op is None:
                raise ValueError(f"Unsupported comparison: {constraint.op!r}")
            clauses.append(
                "EXISTS (SELECT 1 FROM product_specs s "
                "WHERE s.product_id = p.id AND s.key = ? "
                f"AND s.value_num {op} ?)"
            )
            params.extend([constraint.key, constraint.value])

        where = "WHERE " + " AND ".join(clauses) if clauses else ""
        return where, params

    # ---------- تحويل الصفوف إلى كائنات ----------

    def _query(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        cur = self._conn.cursor()
        cur.row_factory = sqlite3.Row
        cur.execute(sql, params)
        return cur.fetchall()

    def _rows_to_products(self, rows: list[sqlite3.Row]) -> list[Product]:
        if not rows:
            return []
        specs_by_product = self._load_specs([row["id"] for row in rows])
        return [
            self._to_product(row, specs_by_product.get(row["id"], {}))
            for row in rows
        ]

    def _load_specs(self, product_ids: list[int]) -> dict[int, dict[str, Spec]]:
        # عدد علامات (?) فقط هو ما يُبنى نصًا، والقيم نفسها تُمرَّر كمعاملات.
        placeholders = ",".join("?" * len(product_ids))
        rows = self._query(
            "SELECT product_id, key, value_text, value_num, unit "
            f"FROM product_specs WHERE product_id IN ({placeholders}) "
            "ORDER BY key",
            tuple(product_ids),
        )
        result: dict[int, dict[str, Spec]] = {}
        for row in rows:
            result.setdefault(row["product_id"], {})[row["key"]] = Spec(
                key=row["key"],
                value_text=row["value_text"],
                value_num=row["value_num"],
                unit=row["unit"],
            )
        return result

    @staticmethod
    def _to_product(row: sqlite3.Row, specs: dict[str, Spec]) -> Product:
        return Product(
            id=row["id"],
            name=row["name"],
            category=row["category"],
            currency=row["currency"],
            brand=row["brand"],
            price=row["price"],
            in_stock=None if row["in_stock"] is None else bool(row["in_stock"]),
            url=row["url"],
            specs=specs,
            is_test_data=bool(row["is_test_data"]),
        )
