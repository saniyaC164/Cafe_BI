"""
Inventory Management service
==============================
All logic is SQL-based — no ML required.

Provides:
  - Stock status with ok / low / critical classification
  - Depletion rates (avg daily usage → days remaining)
  - Reorder suggestions with urgency levels
  - Wastage trend (daily) and wastage by day-of-week
  - Full dashboard in one call
"""

from sqlalchemy.orm import Session
from sqlalchemy import text

from schemas.inventory import (
    StockStatus, DepletionRate, WastageEntry,
    WastageSummary, ReorderSuggestion,
    WastageByDay, InventoryDashboard,
)


# ── helpers ────────────────────────────────────────────────────────────────

def _status_label(current: float, reorder: float) -> str:
    if current <= 0:
        return "critical"
    ratio = current / reorder
    if ratio <= 0.8:
        return "critical"
    if ratio <= 1.5:
        return "low"
    return "ok"


def _days_remaining(current: float, daily_usage: float) -> float | None:
    if daily_usage and daily_usage > 0:
        return round(current / daily_usage, 1)
    return None


# ── 1. Stock status ────────────────────────────────────────────────────────
def get_stock_status(db: Session) -> list[StockStatus]:
    """
    Current stock for every ingredient with status badge.
    Depletion rate is calculated from last 30 days of usage transactions.
    """
    rows = db.execute(text("""
        WITH daily_usage AS (
            SELECT
                ingredient_id,
                ABS(AVG(quantity)) AS avg_daily_usage
            FROM inventory_transactions
            WHERE type = 'usage'
              AND timestamp >= (
                  SELECT MAX(timestamp) FROM inventory_transactions
              ) - INTERVAL '30 days'
            GROUP BY ingredient_id
        )
        SELECT
            i.ingredient_id,
            i.name,
            i.unit,
            i.current_stock,
            i.reorder_level,
            i.supplier,
            i.last_restocked_at::text,
            COALESCE(du.avg_daily_usage, 0) AS avg_daily_usage
        FROM inventory i
        LEFT JOIN daily_usage du ON i.ingredient_id = du.ingredient_id
        ORDER BY
            CASE
                WHEN i.current_stock / NULLIF(i.reorder_level, 0) <= 0.8 THEN 1
                WHEN i.current_stock / NULLIF(i.reorder_level, 0) <= 1.5 THEN 2
                ELSE 3
            END,
            i.name
    """)).fetchall()

    result = []
    for r in rows:
        current      = float(r[3])
        reorder      = float(r[4])
        daily_usage  = float(r[7])
        status       = _status_label(current, reorder)
        days_left    = _days_remaining(current, daily_usage)

        result.append(StockStatus(
            ingredient_id    = int(r[0]),
            name             = r[1],
            unit             = r[2],
            current_stock    = round(current, 2),
            reorder_level    = round(reorder, 2),
            supplier         = r[5],
            last_restocked   = str(r[6]),
            status           = status,
            days_until_empty = days_left,
        ))
    return result


# ── 2. Depletion rates ─────────────────────────────────────────────────────
def get_depletion_rates(db: Session) -> list[DepletionRate]:
    """Average daily consumption for each ingredient over the last 30 days."""
    rows = db.execute(text("""
        SELECT
            i.ingredient_id,
            i.name,
            i.unit,
            i.current_stock,
            ABS(AVG(t.quantity)) AS avg_daily_usage
        FROM inventory i
        JOIN inventory_transactions t ON i.ingredient_id = t.ingredient_id
        WHERE t.type = 'usage'
          AND t.timestamp >= (
              SELECT MAX(timestamp) FROM inventory_transactions
          ) - INTERVAL '30 days'
        GROUP BY i.ingredient_id, i.name, i.unit, i.current_stock
        ORDER BY avg_daily_usage DESC
    """)).fetchall()

    result = []
    for r in rows:
        current     = float(r[3])
        daily_usage = float(r[4])
        result.append(DepletionRate(
            ingredient_id    = int(r[0]),
            name             = r[1],
            unit             = r[2],
            avg_daily_usage  = round(daily_usage, 3),
            current_stock    = round(current, 2),
            days_remaining   = _days_remaining(current, daily_usage),
        ))
    return result


# ── 3. Reorder suggestions ─────────────────────────────────────────────────
def get_reorder_suggestions(db: Session) -> list[ReorderSuggestion]:
    """
    Items at or below reorder level, sorted by urgency.
    Suggested order = 4× reorder level (enough for ~1 month).
    """
    rows = db.execute(text("""
        WITH daily_usage AS (
            SELECT
                ingredient_id,
                ABS(AVG(quantity)) AS avg_daily_usage
            FROM inventory_transactions
            WHERE type = 'usage'
            GROUP BY ingredient_id
        )
        SELECT
            i.ingredient_id,
            i.name,
            i.unit,
            i.current_stock,
            i.reorder_level,
            i.supplier,
            COALESCE(du.avg_daily_usage, 0) AS avg_daily_usage
        FROM inventory i
        LEFT JOIN daily_usage du ON i.ingredient_id = du.ingredient_id
        WHERE i.current_stock <= i.reorder_level * 1.5
        ORDER BY (i.current_stock / NULLIF(i.reorder_level, 0)) ASC
    """)).fetchall()

    result = []
    for r in rows:
        current     = float(r[3])
        reorder     = float(r[4])
        daily_usage = float(r[6])

        # Urgency based on how many days of stock remain
        days_left = _days_remaining(current, daily_usage)
        if days_left is None or days_left <= 2:
            urgency = "critical"
        elif days_left <= 5:
            urgency = "low"
        else:
            urgency = "scheduled"

        result.append(ReorderSuggestion(
            ingredient_id   = int(r[0]),
            name            = r[1],
            unit            = r[2],
            current_stock   = round(current, 2),
            reorder_level   = round(reorder, 2),
            suggested_order = round(reorder * 4, 1),
            supplier        = r[5],
            urgency         = urgency,
        ))
    return result


# ── 4. Wastage trend (daily) ───────────────────────────────────────────────
def get_wastage_trend(db: Session, days: int = 60) -> list[WastageSummary]:
    """Daily wastage event count and number of affected ingredients."""
    rows = db.execute(text("""
        SELECT
            DATE(timestamp)        AS day,
            COUNT(*)               AS total_events,
            COUNT(DISTINCT ingredient_id) AS ingredients_affected
        FROM inventory_transactions
        WHERE type = 'wastage'
          AND timestamp >= (
              SELECT MAX(timestamp) FROM inventory_transactions
          ) - INTERVAL ':days days'
        GROUP BY day
        ORDER BY day
    """.replace(":days", str(days)))).fetchall()

    return [
        WastageSummary(
            date                  = str(r[0]),
            total_wastage_events  = int(r[1]),
            ingredients_wasted    = int(r[2]),
        )
        for r in rows
    ]


# ── 5. Wastage by day of week ──────────────────────────────────────────────
def get_wastage_by_weekday(db: Session) -> list[WastageByDay]:
    """
    Aggregated wastage by day-of-week — confirms the Monday spike pattern
    baked into the synthetic data.
    """
    rows = db.execute(text("""
        SELECT
            TO_CHAR(timestamp, 'Dy')        AS day_of_week,
            EXTRACT(DOW FROM timestamp)     AS dow_num,
            SUM(ABS(quantity))              AS total_wastage,
            COUNT(*)                        AS event_count
        FROM inventory_transactions
        WHERE type = 'wastage'
        GROUP BY day_of_week, dow_num
        ORDER BY dow_num
    """)).fetchall()

    return [
        WastageByDay(
            day_of_week   = r[0],
            total_wastage = round(float(r[2]), 2),
            event_count   = int(r[3]),
        )
        for r in rows
    ]


# ── PUBLIC: full dashboard ─────────────────────────────────────────────────
def get_dashboard(db: Session) -> InventoryDashboard:
    stock        = get_stock_status(db)
    depletion    = get_depletion_rates(db)
    reorders     = get_reorder_suggestions(db)
    wastage      = get_wastage_trend(db)
    by_weekday   = get_wastage_by_weekday(db)

    alert_count  = sum(1 for s in stock if s.status in ("low", "critical"))

    return InventoryDashboard(
        stock_status        = stock,
        depletion_rates     = depletion,
        reorder_suggestions = reorders,
        wastage_trend       = wastage,
        wastage_by_weekday  = by_weekday,
        alert_count         = alert_count,
    )