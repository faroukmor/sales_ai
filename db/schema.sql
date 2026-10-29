-- db/schema.sql

CREATE TABLE IF NOT EXISTS products (
    id           INTEGER PRIMARY KEY,
    name         TEXT    NOT NULL,
    category     TEXT    NOT NULL,
    brand        TEXT,
    price        REAL    CHECK (price IS NULL OR price >= 0),
    currency     TEXT    NOT NULL DEFAULT 'DZD',
    in_stock     INTEGER CHECK (in_stock IS NULL OR in_stock IN (0, 1)),
    url          TEXT,
    is_test_data INTEGER NOT NULL DEFAULT 0 CHECK (is_test_data IN (0, 1))
);

CREATE TABLE IF NOT EXISTS product_specs (
    id         INTEGER PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    key        TEXT    NOT NULL,
    value_text TEXT,
    value_num  REAL,
    unit       TEXT,
    UNIQUE (product_id, key)
);

-- مقاطع المعرفة مع embedding مخزَّن كـ float32 BLOB واسم النموذج الذي ولّده.
CREATE TABLE IF NOT EXISTS knowledge_chunks (
    id              INTEGER PRIMARY KEY,
    source          TEXT NOT NULL,
    title           TEXT,
    text            TEXT NOT NULL,
    product_id      INTEGER REFERENCES products(id) ON DELETE SET NULL,
    embedding       BLOB,
    embedding_model TEXT,
    CHECK ((embedding IS NULL) = (embedding_model IS NULL))
);

-- التواريخ بصيغة ISO (YYYY-MM-DD) حصرًا؛ NULL تعني "غير معروف".
CREATE TABLE IF NOT EXISTS promotions (
    id           INTEGER PRIMARY KEY,
    title        TEXT NOT NULL,
    conditions   TEXT,
    starts_at    TEXT CHECK (starts_at IS NULL OR (starts_at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]' AND date(starts_at) IS starts_at)),
    ends_at      TEXT CHECK (ends_at IS NULL OR (ends_at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]' AND date(ends_at) IS ends_at)),
    product_id   INTEGER REFERENCES products(id) ON DELETE CASCADE,
    category     TEXT,
    source       TEXT NOT NULL,
    is_test_data INTEGER NOT NULL DEFAULT 0 CHECK (is_test_data IN (0, 1)),
    CHECK (starts_at IS NULL OR ends_at IS NULL OR starts_at <= ends_at)
);

CREATE INDEX IF NOT EXISTS idx_products_category ON products (category);
CREATE INDEX IF NOT EXISTS idx_specs_key_num     ON product_specs (key, value_num);
CREATE INDEX IF NOT EXISTS idx_chunks_model      ON knowledge_chunks (embedding_model);
CREATE INDEX IF NOT EXISTS idx_promotions_dates  ON promotions (starts_at, ends_at);
