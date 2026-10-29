# repositories/promotion_repository.py
import sqlite3
from datetime import date
from typing import Callable

from models.promotion import Promotion


class PromotionRepository:
    """الوصول إلى العروض. يقرر ما هو "ساري" اعتمادًا على تاريخ يُحقَن من الخارج."""

    def __init__(self, conn: sqlite3.Connection, today: Callable[[], date] = date.today):
        self._conn = conn
        self._today = today   # دالة، حتى نثبّت "اليوم" في الاختبارات

    def find_valid(self, category: str | None = None) -> list[Promotion]:
        """عروض ساريةٌ اليوم. شرطنا المتحفظ: يجب أن يكون تاريخا البداية والنهاية معروفين."""
        today = self._today().isoformat()
        sql = (
            "SELECT pr.id, pr.title, pr.conditions, pr.starts_at, pr.ends_at, "
            "       pr.product_id, pr.category, pr.source "
            "FROM promotions pr LEFT JOIN products p ON p.id = pr.product_id "
            "WHERE pr.starts_at IS NOT NULL AND pr.ends_at IS NOT NULL "
            "  AND pr.starts_at <= ? AND pr.ends_at >= ?"
        )
        params: list = [today, today]
        if category is not None:
            sql += " AND (pr.category = ? COLLATE NOCASE OR p.category = ? COLLATE NOCASE)"
            params += [category, category]
        sql += " ORDER BY pr.ends_at ASC, pr.id ASC"

        cur = self._conn.cursor()
        cur.row_factory = sqlite3.Row
        cur.execute(sql, params)
        return [self._to_promotion(row) for row in cur.fetchall()]

    @staticmethod
    def _to_promotion(row: sqlite3.Row) -> Promotion:
        return Promotion(
            id=row["id"],
            title=row["title"],
            source=row["source"],
            starts_at=date.fromisoformat(row["starts_at"]) if row["starts_at"] else None,
            ends_at=date.fromisoformat(row["ends_at"]) if row["ends_at"] else None,
            conditions=row["conditions"],
            product_id=row["product_id"],
            category=row["category"],
        )
