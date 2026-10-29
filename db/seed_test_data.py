# db/seed_test_data.py
import sqlite3
from datetime import date, timedelta

from core.config import DB_PATH, DEFAULT_CURRENCY
from core.formatting import format_number
from db.database import connect, init_schema


def _normalize_spec(value):
    """يحوّل قيمة مواصفة إلى (value_text, value_num, unit)."""
    unit = None
    if isinstance(value, tuple):
        value, unit = value
    if isinstance(value, (int, float)):
        return format_number(value), float(value), unit
    return str(value), None, unit


def add_product(
    conn: sqlite3.Connection,
    name: str,
    category: str,
    *,
    brand: str | None = None,
    price: float | None = None,
    currency: str = DEFAULT_CURRENCY,
    in_stock: bool | None = None,
    url: str | None = None,
    is_test_data: bool = True,
    specs: dict | None = None,
) -> int:
    """يضيف منتجًا ومواصفاته ويرجع id. لا يعمل commit (القرار للمستدعي)."""
    cur = conn.execute(
        "INSERT INTO products "
        "(name, category, brand, price, currency, in_stock, url, is_test_data) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            name, category, brand, price, currency,
            None if in_stock is None else int(in_stock),
            url, int(is_test_data),
        ),
    )
    product_id = cur.lastrowid
    for key, value in (specs or {}).items():
        value_text, value_num, unit = _normalize_spec(value)
        conn.execute(
            "INSERT INTO product_specs (product_id, key, value_text, value_num, unit) "
            "VALUES (?, ?, ?, ?, ?)",
            (product_id, key, value_text, value_num, unit),
        )
    return product_id


def add_promotion(
    conn: sqlite3.Connection,
    title: str,
    *,
    source: str,
    starts_at: str | None = None,
    ends_at: str | None = None,
    conditions: str | None = None,
    product_id: int | None = None,
    category: str | None = None,
    is_test_data: bool = True,
) -> int:
    """يضيف عرضًا. التواريخ نصوص ISO مثل '2026-11-30'. لا يعمل commit."""
    cur = conn.execute(
        "INSERT INTO promotions "
        "(title, conditions, starts_at, ends_at, product_id, category, source, is_test_data) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (title, conditions, starts_at, ends_at, product_id, category, source,
         int(is_test_data)),
    )
    return cur.lastrowid


def seed(conn: sqlite3.Connection) -> None:
    """يُدخل بيانات اختبار وهمية. يحذف بيانات الاختبار القديمة فقط (is_test_data=1)."""
    conn.execute("DELETE FROM promotions WHERE is_test_data = 1")
    conn.execute("DELETE FROM products WHERE is_test_data = 1")

    add_product(
        conn, "TEST-LAPTOP-01", "laptop", brand="TestBrand", price=95000,
        in_stock=True,
        specs={"ram_gb": (16, "GB"), "storage_gb": (512, "GB")},
    )
    add_product(
        conn, "TEST-LAPTOP-02", "laptop", brand="TestBrand", price=60000,
        in_stock=True,
        specs={"ram_gb": (8, "GB"), "storage_gb": (256, "GB")},
    )
    add_product(
        conn, "TEST-LAPTOP-03", "laptop", brand="OtherBrand", price=140000,
        in_stock=False,
        specs={"ram_gb": (32, "GB")},
    )
    add_product(
        conn, "TEST-TV-01", "tv", brand="TestBrand", price=70000,
        in_stock=True,
        specs={"panel_type": "OLED", "screen_inches": (55, "inch")},
    )

    today = date.today()
    day = lambda n: (today + timedelta(days=n)).isoformat()  # noqa: E731
    src = "test-data"
    add_promotion(conn, "TEST-PROMO valid laptops", source=src, category="laptop",
                  starts_at=day(-10), ends_at=day(20),
                  conditions="Test conditions: TEST laptops only")
    add_promotion(conn, "TEST-PROMO expired", source=src, category="laptop",
                  starts_at=day(-30), ends_at=day(-1))
    add_promotion(conn, "TEST-PROMO future", source=src, category="tv",
                  starts_at=day(5), ends_at=day(30))
    add_promotion(conn, "TEST-PROMO no end date", source=src, category="tv",
                  starts_at=day(-5))
    conn.commit()


def main() -> None:
    conn = connect(DB_PATH)
    try:
        init_schema(conn)
        seed(conn)
    finally:
        conn.close()
    print(f"Test data seeded into {DB_PATH}")


if __name__ == "__main__":
    main()
