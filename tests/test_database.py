# tests/test_database.py
import sqlite3

import pytest

from db.seed_test_data import add_product, seed


def test_deleting_product_cascades_to_specs(conn):
    pid = add_product(conn, "X", "laptop", specs={"ram_gb": 8})
    conn.execute("DELETE FROM products WHERE id = ?", (pid,))
    left = conn.execute("SELECT COUNT(*) FROM product_specs").fetchone()[0]
    assert left == 0


def test_duplicate_spec_key_for_same_product_is_rejected(conn):
    pid = add_product(conn, "X", "laptop", specs={"ram_gb": 8})
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO product_specs (product_id, key, value_num) VALUES (?, 'ram_gb', 16)",
            (pid,),
        )


def test_negative_price_is_rejected(conn):
    with pytest.raises(sqlite3.IntegrityError):
        add_product(conn, "X", "laptop", price=-1)


def test_spec_for_missing_product_is_rejected(conn):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO product_specs (product_id, key, value_num) VALUES (999, 'ram_gb', 8)"
        )


def test_seed_is_idempotent_and_marks_test_data(conn):
    seed(conn)
    seed(conn)
    total = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    flagged = conn.execute("SELECT COUNT(*) FROM products WHERE is_test_data = 1").fetchone()[0]
    assert total == 4
    assert flagged == total


def test_promotion_rejects_non_iso_dates(conn):
    for bad in ("2026/11/30", "now", "2026-13-45", "2026-11-30 10:00"):
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO promotions (title, source, starts_at) VALUES ('x', 's', ?)", (bad,)
            )


def test_promotion_rejects_end_before_start(conn):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO promotions (title, source, starts_at, ends_at) "
            "VALUES ('x', 's', '2026-12-01', '2026-11-01')"
        )


def test_chunk_embedding_and_model_must_be_set_together(conn):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO knowledge_chunks (source, text, embedding) VALUES ('s', 't', x'00')"
        )
