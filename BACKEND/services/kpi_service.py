from sqlalchemy.orm import Session
from sqlalchemy import text
from schemas.kpi import (
    KPISummary, RevenueByDay, TopItem,
    ChannelSplit, HourlyHeatmap, CustomerStats,
    PaymentSplit, KPIDashboard,
)


# ── date range filter helper ───────────────────────────────────────────────
def _date_filter(period: str) -> str:
    periods = {
        "7d":   "o.timestamp >= (SELECT MAX(timestamp) FROM ORDERS o ) - INTERVAL '7 days'",
        "30d":  "o.timestamp >= (SELECT MAX(timestamp) FROM ORDERS o ) - INTERVAL '30 days'",
        "90d":  "o.timestamp >= (SELECT MAX(timestamp) FROM ORDERS o ) - INTERVAL '90 days'",
        "365d": "o.timestamp >= (SELECT MAX(timestamp) FROM ORDERS o ) - INTERVAL '365 days'",
        "all":  "1=1",
    }
    return periods.get(period, periods["30d"])


# ── 1. Summary KPIs ────────────────────────────────────────────────────────
def get_summary(db: Session, period: str) -> KPISummary:
    where = _date_filter(period)
    row = db.execute(text(f"""
        SELECT
            ROUND(SUM(o.total_amount)::numeric, 2)          AS total_revenue,
            COUNT(DISTINCT o.order_id)                       AS total_orders,
            ROUND(AVG(o.total_amount)::numeric, 2)           AS avg_order_value,
            ROUND(SUM(
                oi.quantity * (oi.unit_price - m.cost_price)
                * (1 - oi.discount_applied)
            )::numeric, 2)                                   AS gross_profit
        FROM orders o
        JOIN order_items oi ON o.order_id = oi.order_id
        JOIN menu_items  m  ON oi.item_id = m.item_id
        WHERE {where}
    """)).fetchone()

    total_revenue = float(row[0] or 0)
    gross_profit  = float(row[3] or 0)
    profit_margin = round((gross_profit / total_revenue * 100), 2) if total_revenue else 0

    return KPISummary(
        total_revenue     = total_revenue,
        total_orders      = int(row[1] or 0),
        avg_order_value   = float(row[2] or 0),
        gross_profit      = gross_profit,
        profit_margin_pct = profit_margin,
    )


# ── 2. Revenue trend (daily) ───────────────────────────────────────────────
def get_revenue_trend(db: Session, period: str) -> list[RevenueByDay]:
    where = _date_filter(period)
    rows = db.execute(text(f"""
        SELECT
            DATE(timestamp)              AS day,
            ROUND(SUM(total_amount)::numeric, 2) AS revenue,
            COUNT(*)                     AS orders
        FROM ORDERS o 
        WHERE {where}
        GROUP BY day
        ORDER BY day
    """)).fetchall()

    return [
        RevenueByDay(
            date    = str(r[0]),
            revenue = float(r[1]),
            orders  = int(r[2]),
        )
        for r in rows
    ]


# ── 3. Top 5 items by revenue ──────────────────────────────────────────────
def get_top_items(db: Session, period: str) -> list[TopItem]:
    where = _date_filter(period)
    rows = db.execute(text(f"""
        SELECT
            m.name,
            m.category,
            ROUND(SUM(oi.quantity * oi.unit_price * (1 - oi.discount_applied))::numeric, 2) AS total_revenue,
            SUM(oi.quantity)  AS total_qty
        FROM order_items oi
        JOIN menu_items  m  ON oi.item_id = m.item_id
        JOIN orders      o  ON oi.order_id = o.order_id
        WHERE {where}
        GROUP BY m.name, m.category
        ORDER BY total_revenue DESC
        LIMIT 10
    """)).fetchall()

    return [
        TopItem(
            name          = r[0],
            category      = r[1],
            total_revenue = float(r[2]),
            total_qty     = int(r[3]),
        )
        for r in rows
    ]


# ── 4. Channel split ───────────────────────────────────────────────────────
def get_channel_split(db: Session, period: str) -> list[ChannelSplit]:
    where = _date_filter(period)
    rows = db.execute(text(f"""
        SELECT
            channel,
            COUNT(*)                             AS orders,
            ROUND(SUM(total_amount)::numeric, 2) AS revenue
        FROM ORDERS o 
        WHERE {where}
        GROUP BY channel
        ORDER BY orders DESC
    """)).fetchall()

    total_orders = sum(r[1] for r in rows) or 1
    return [
        ChannelSplit(
            channel    = r[0],
            orders     = int(r[1]),
            revenue    = float(r[2]),
            percentage = round(r[1] / total_orders * 100, 1),
        )
        for r in rows
    ]


# ── 5. Hourly heatmap (orders by hour × day-of-week) ──────────────────────
def get_hourly_heatmap(db: Session, period: str) -> list[HourlyHeatmap]:
    where = _date_filter(period)
    rows = db.execute(text(f"""
        SELECT
            EXTRACT(HOUR FROM timestamp)::int      AS hour,
            TO_CHAR(timestamp, 'Dy')               AS day_of_week,
            COUNT(*)                               AS order_count
        FROM ORDERS o 
        WHERE {where}
        GROUP BY hour, day_of_week
        ORDER BY hour, day_of_week
    """)).fetchall()

    return [
        HourlyHeatmap(
            hour        = r[0],
            day_of_week = r[1],
            order_count = int(r[2]),
        )
        for r in rows
    ]


# ── 6. Customer stats ──────────────────────────────────────────────────────
def get_customer_stats(db: Session, period: str) -> CustomerStats:
    where = _date_filter(period)

    # Customers who ordered in this period
    active = db.execute(text(f"""
        SELECT COUNT(DISTINCT customer_id) FROM ORDERS o  WHERE {where}
    """)).scalar() or 0

    # Repeat = ordered more than once
    repeat = db.execute(text(f"""
        SELECT COUNT(*) FROM (
            SELECT customer_id
            FROM ORDERS o 
            WHERE {where}
            GROUP BY customer_id
            HAVING COUNT(*) > 1
        ) t
    """)).scalar() or 0

    # Segment breakdown from customers table
    seg = db.execute(text("""
        SELECT segment, COUNT(*) FROM customers GROUP BY segment
    """)).fetchall()
    seg_map = {r[0]: int(r[1]) for r in seg}

    retention = round(repeat / active * 100, 1) if active else 0

    return CustomerStats(
        total_customers    = int(active),
        repeat_customers   = int(repeat),
        retention_rate_pct = retention,
        regular_count      = seg_map.get("regular", 0),
        occasional_count   = seg_map.get("occasional", 0),
        new_count          = seg_map.get("new", 0),
    )


# ── 7. Payment method split ────────────────────────────────────────────────
def get_payment_split(db: Session, period: str) -> list[PaymentSplit]:
    where = _date_filter(period)
    rows = db.execute(text(f"""
        SELECT payment_method, COUNT(*) AS cnt
        FROM ORDERS o 
        WHERE {where}
        GROUP BY payment_method
        ORDER BY cnt DESC
    """)).fetchall()

    total = sum(r[1] for r in rows) or 1
    return [
        PaymentSplit(
            method     = r[0],
            count      = int(r[1]),
            percentage = round(r[1] / total * 100, 1),
        )
        for r in rows
    ]


# ── MAIN: full dashboard in one call ──────────────────────────────────────
def get_dashboard(db: Session, period: str = "30d") -> KPIDashboard:
    return KPIDashboard(
        summary        = get_summary(db, period),
        revenue_trend  = get_revenue_trend(db, period),
        top_items      = get_top_items(db, period),
        channel_split  = get_channel_split(db, period),
        hourly_heatmap = get_hourly_heatmap(db, period),
        customer_stats = get_customer_stats(db, period),
        payment_split  = get_payment_split(db, period),
    )