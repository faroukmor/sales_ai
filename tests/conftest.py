# tests/conftest.py
import pytest

from db.database import connect, init_schema
from db.seed_test_data import add_product
from repositories.product_repository import ProductRepository


@pytest.fixture
def conn():
    connection = connect(":memory:")
    init_schema(connection)
    yield connection
    connection.close()


@pytest.fixture
def repo(conn):
    """قاعدة صغيرة بصفوف مصمَّمة لتغطية الحالات الحدّية."""
    add_product(conn, "Test Laptop A", "laptop", brand="BrandX", price=95000,
                in_stock=True,
                specs={"ram_gb": (16, "GB"), "storage_gb": (512, "GB")})
    add_product(conn, "Test Laptop B", "laptop", brand="BrandY", price=120000,
                in_stock=True,
                specs={"ram_gb": (16, "GB"), "storage_gb": (1024, "GB")})
    add_product(conn, "Test Laptop C", "laptop", brand="BrandX", price=80000,
                in_stock=False,
                specs={"ram_gb": (8, "GB"), "storage_gb": (256, "GB")})
    # سعر وتوفر غير معروفين
    add_product(conn, "Test Laptop D", "laptop", brand="BrandY",
                specs={"ram_gb": (32, "GB")})
    # بلا أي مواصفات مسجَّلة
    add_product(conn, "Test Laptop E", "laptop", price=90000, in_stock=True)
    add_product(conn, "Test TV A", "tv", brand="BrandX", price=70000,
                in_stock=True,
                specs={"panel_type": "OLED", "screen_inches": (55, "inch")})
    conn.commit()
    return ProductRepository(conn)
