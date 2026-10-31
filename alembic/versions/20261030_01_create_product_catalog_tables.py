"""create product catalog tables

Revision ID: 20261030_01
Revises:
Create Date: 2026-10-30
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261030_01"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("brand", sa.String(length=100), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("price", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("in_stock", sa.Boolean(), nullable=True),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("is_test_data", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.CheckConstraint("length(currency) = 3", name="ck_products_currency_length"),
        sa.CheckConstraint("price >= 0", name="ck_products_price_nonnegative"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_products_brand", "products", ["brand"], unique=False)
    op.create_index("ix_products_category", "products", ["category"], unique=False)
    op.create_index(
        "ix_products_category_in_stock", "products", ["category", "in_stock"], unique=False
    )
    op.create_index("ix_products_category_price", "products", ["category", "price"], unique=False)
    op.create_index("ix_products_in_stock", "products", ["in_stock"], unique=False)
    op.create_index("ix_products_is_test_data", "products", ["is_test_data"], unique=False)
    op.create_index("ix_products_name", "products", ["name"], unique=False)
    op.create_index("ix_products_price", "products", ["price"], unique=False)

    op.create_table(
        "product_specs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column("value_text", sa.String(length=255), nullable=True),
        sa.Column("value_num", sa.Numeric(), nullable=True),
        sa.Column("unit", sa.String(length=50), nullable=True),
        sa.CheckConstraint(
            "value_text IS NOT NULL OR value_num IS NOT NULL", name="ck_product_specs_has_value"
        ),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("product_id", "key", name="uq_product_specs_product_key"),
    )
    op.create_index("ix_product_specs_key_value_num", "product_specs", ["key", "value_num"])
    op.create_index("ix_product_specs_product_id", "product_specs", ["product_id"])

    op.create_table(
        "promotions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("conditions", sa.Text(), nullable=True),
        sa.Column("starts_at", sa.Date(), nullable=True),
        sa.Column("ends_at", sa.Date(), nullable=True),
        sa.Column("product_id", sa.Integer(), nullable=True),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("source", sa.String(length=255), nullable=False),
        sa.Column("is_test_data", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.CheckConstraint(
            "starts_at IS NULL OR ends_at IS NULL OR starts_at <= ends_at",
            name="ck_promotions_valid_interval",
        ),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_promotions_category", "promotions", ["category"])
    op.create_index(
        "ix_promotions_category_validity",
        "promotions",
        ["category", "starts_at", "ends_at"],
    )
    op.create_index("ix_promotions_is_test_data", "promotions", ["is_test_data"])
    op.create_index("ix_promotions_product_id", "promotions", ["product_id"])
    op.create_index("ix_promotions_title", "promotions", ["title"])
    op.create_index("ix_promotions_validity", "promotions", ["starts_at", "ends_at"])


def downgrade() -> None:
    op.drop_index("ix_promotions_validity", table_name="promotions")
    op.drop_index("ix_promotions_title", table_name="promotions")
    op.drop_index("ix_promotions_product_id", table_name="promotions")
    op.drop_index("ix_promotions_is_test_data", table_name="promotions")
    op.drop_index("ix_promotions_category_validity", table_name="promotions")
    op.drop_index("ix_promotions_category", table_name="promotions")
    op.drop_table("promotions")
    op.drop_index("ix_product_specs_product_id", table_name="product_specs")
    op.drop_index("ix_product_specs_key_value_num", table_name="product_specs")
    op.drop_table("product_specs")
    op.drop_index("ix_products_price", table_name="products")
    op.drop_index("ix_products_name", table_name="products")
    op.drop_index("ix_products_is_test_data", table_name="products")
    op.drop_index("ix_products_in_stock", table_name="products")
    op.drop_index("ix_products_category_price", table_name="products")
    op.drop_index("ix_products_category_in_stock", table_name="products")
    op.drop_index("ix_products_category", table_name="products")
    op.drop_index("ix_products_brand", table_name="products")
    op.drop_table("products")
