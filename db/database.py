# db/database.py
import sqlite3
from pathlib import Path

SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


def connect(db_path) -> sqlite3.Connection:
    """يفتح اتصالًا مع تفعيل المفاتيح الأجنبية (تُفعَّل لكل اتصال على حدة)."""
    if str(db_path) != ":memory:":
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    """ينشئ الجداول إن لم تكن موجودة. آمن عند التكرار."""
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    conn.commit()
