"""
Cafe BI System — Synthetic Data Generator
==========================================
Generates all 9 tables with realistic patterns baked in:
  - Time-weighted orders (morning rush, lunch spike, dead zone)
  - Seasonal effects (Diwali bump, monsoon dip, January slump)
  - MBA-ready combos (latte+croissant co-occur 60%+)
  - Inventory depletion + Monday wastage spikes
  - Sentiment-matched reviews with aspect tags
  - Prophet-ready daily_sales_summary with holiday regressors

Usage:
  pip install faker pandas psycopg2-binary sqlalchemy
  python generate_cafe_data.py

Set your DB connection string in DB_URL below.
"""

import random
import math
from datetime import datetime, timedelta, date

import pandas as pd
from faker import Faker
from sqlalchemy import create_engine, text

# ─────────────────────────────────────────────
# CONFIG — edit these
# ─────────────────────────────────────────────
DB_URL = "postgresql://postgres:saniyadb@localhost:5432/cafe_db"
SEED   = 42          # reproducibility
START  = date(2024, 1, 1)
END    = date(2024, 12, 31)

random.seed(SEED)
fake = Faker()
Faker.seed(SEED)

engine = create_engine(DB_URL)

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def daterange(start: date, end: date):
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)

def is_weekend(d: date) -> bool:
    return d.weekday() >= 5   # Sat=5, Sun=6

def is_monday(d: date) -> bool:
    return d.weekday() == 0

# Mumbai public holidays / events 2024
HOLIDAYS = {
    date(2024,  1, 26): ("Republic Day",      0.60),   # lower footfall
    date(2024,  3, 25): ("Holi",              1.20),
    date(2024,  4, 14): ("Ambedkar Jayanti",  0.80),
    date(2024,  4, 17): ("Ram Navami",        0.85),
    date(2024,  8, 15): ("Independence Day",  0.70),
    date(2024,  8, 26): ("Janmashtami",       0.75),
    date(2024, 10,  2): ("Gandhi Jayanti",    0.65),
    date(2024, 10, 12): ("Dussehra",          1.15),
    date(2024, 10, 31): ("Diwali Eve",        1.30),
    date(2024, 11,  1): ("Diwali",            1.25),
    date(2024, 11,  2): ("Diwali Day 2",      1.20),
    date(2024, 11,  3): ("Diwali Day 3",      1.10),
    date(2024, 12, 25): ("Christmas",         1.15),
    date(2024, 12, 31): ("New Year Eve",      1.35),
}

# Monsoon months (July–September) → lower footfall for outdoor/dine-in
def monsoon_factor(d: date) -> float:
    if d.month in (7, 8, 9):
        return 0.78
    return 1.0

# January slump
def month_factor(d: date) -> float:
    factors = {
        1: 0.72,   # January — post-holiday slump
        2: 0.85,
        3: 0.92,
        4: 0.95,
        5: 0.98,
        6: 0.96,
        7: 0.80,   # monsoon starts
        8: 0.78,
        9: 0.82,
        10: 1.05,
        11: 1.15,  # Diwali month
        12: 1.20,  # December festive
    }
    return factors.get(d.month, 1.0)

def daily_order_count(d: date) -> int:
    """Target number of orders for a given date."""
    base = 55
    if is_weekend(d):
        base = int(base * 1.40)
    base = int(base * month_factor(d) * monsoon_factor(d))
    if d in HOLIDAYS:
        base = int(base * HOLIDAYS[d][1])
    return max(10, base + random.randint(-5, 5))

# Hour-of-day weights: index = hour 0–23
HOUR_WEIGHTS = [
    0, 0, 0, 0, 0, 0,   # 0–5am  (closed)
    0.5, 2,              # 6–7am  (early openers)
    5, 6,                # 8–9am  MORNING RUSH
    4, 2,                # 10–11am
    5, 6,                # 12–1pm LUNCH SPIKE
    3, 1,                # 2–3pm
    0.5, 0.5,            # 3–4pm  DEAD ZONE
    2, 3,                # 5–6pm  evening pick-up
    2, 1,                # 7–8pm
    0.5, 0,              # 9–10pm (closing)
]

def random_timestamp(d: date) -> datetime:
    hour = random.choices(range(24), weights=HOUR_WEIGHTS)[0]
    minute = random.randint(0, 59)
    second = random.randint(0, 59)
    return datetime(d.year, d.month, d.day, hour, minute, second)


# ─────────────────────────────────────────────
# TABLE 1 — customers
# ─────────────────────────────────────────────
print("Generating customers...")

segments = ["regular", "occasional", "new"]
seg_weights = [25, 45, 30]

customers = []
for cid in range(1, 3001):
    seg = random.choices(segments, weights=seg_weights)[0]
    first_visit = fake.date_between(start_date=START, end_date=END)
    if seg == "regular":
        last_visit = fake.date_between(
            start_date=max(first_visit, END - timedelta(days=7)), end_date=END
        )
    elif seg == "occasional":
        last_visit = fake.date_between(
            start_date=max(first_visit, END - timedelta(days=30)), end_date=END
        )
    else:
        last_visit = fake.date_between(start_date=first_visit, end_date=END)

    customers.append({
        "customer_id":     cid,
        "name":            fake.name(),
        "segment":         seg,
        "loyalty_points":  random.randint(0, 800) if seg == "regular" else random.randint(0, 150),
        "first_visit":     first_visit,
        "last_visit":      last_visit,
    })

customers_df = pd.DataFrame(customers)


# ─────────────────────────────────────────────
# TABLE 2 — menu_items
# ─────────────────────────────────────────────
print("Generating menu items...")

MENU = [
    # id, name,                  category,      price, cost,  seasonal
    (1,  "Espresso",             "hot drinks",  2.50,  0.60,  False),
    (2,  "Latte",                "hot drinks",  3.80,  0.90,  False),
    (3,  "Cappuccino",           "hot drinks",  3.50,  0.85,  False),
    (4,  "Americano",            "hot drinks",  3.00,  0.65,  False),
    (5,  "Flat White",           "hot drinks",  3.80,  0.90,  False),
    (6,  "Cold Brew",            "cold drinks", 4.20,  1.10,  True),
    (7,  "Iced Latte",           "cold drinks", 4.00,  1.00,  True),
    (8,  "Iced Matcha",          "cold drinks", 4.20,  1.05,  True),
    (9,  "Mango Cooler",         "cold drinks", 3.80,  0.90,  True),
    (10, "Masala Chai",          "hot drinks",  2.80,  0.55,  False),
    (11, "Croissant",            "food",        2.80,  0.70,  False),
    (12, "Blueberry Muffin",     "food",        3.00,  0.75,  False),
    (13, "Avocado Toast",        "food",        5.50,  1.80,  False),
    (14, "Club Sandwich",        "food",        6.00,  2.00,  False),
    (15, "Banana Bread",         "food",        2.50,  0.65,  False),
    (16, "Cheesecake",           "desserts",    4.50,  1.20,  False),
    (17, "Brownie",              "desserts",    3.50,  0.90,  False),
    (18, "Tiramisu",             "desserts",    5.00,  1.50,  False),
    (19, "Veg Puff",             "food",        1.80,  0.45,  False),
    (20, "Chicken Sandwich",     "food",        5.50,  1.90,  False),
]

menu_df = pd.DataFrame(MENU, columns=[
    "item_id", "name", "category", "price", "cost_price", "is_seasonal"
])
menu_df["is_active"] = True

ITEM_PRICE = {row.item_id: row.price for row in menu_df.itertuples()}
ITEM_COST  = {row.item_id: row.cost_price for row in menu_df.itertuples()}
ITEM_NAME  = {row.item_id: row.name for row in menu_df.itertuples()}

# ─────────────────────────────────────────────
# MBA COMBO RULES
# trigger_item_id → [(paired_item_id, probability)]
# ─────────────────────────────────────────────
COMBO_RULES = {
    2:  [(11, 0.62)],          # Latte  → Croissant         62%
    3:  [(11, 0.55)],          # Cappuccino → Croissant     55%
    5:  [(11, 0.50)],          # Flat White → Croissant     50%
    6:  [(12, 0.58)],          # Cold Brew → Blueberry Muffin 58%
    7:  [(12, 0.45)],          # Iced Latte → Blueberry Muffin 45%
    1:  [(16, 0.30)],          # Espresso → Cheesecake      30%
    8:  [(15, 0.40)],          # Iced Matcha → Banana Bread 40%
    13: [(4,  0.65), (7, 0.35)], # Avocado Toast → Americano or Iced Latte
    14: [(4,  0.60)],          # Club Sandwich → Americano  60%
    10: [(19, 0.50)],          # Masala Chai → Veg Puff     50%
}

# Seasonal items only available May–Sep
SEASONAL_ITEMS = {6, 7, 8, 9}

def available_items(d: date):
    if d.month in (5, 6, 7, 8, 9):
        return list(range(1, 21))
    return [i for i in range(1, 21) if i not in SEASONAL_ITEMS]

# ─────────────────────────────────────────────
# TABLE 3 — orders  +  TABLE 4 — order_items
# ─────────────────────────────────────────────
print("Generating orders and order_items (this takes a moment)...")

all_orders = []
all_order_items = []
order_id = 1
line_id  = 1

# For inventory depletion tracking: ingredient consumption per day
# ingredient_id → daily usage accumulator
daily_usage = {}  # date -> {ingredient_id: qty}

for d in daterange(START, END):
    n_orders = daily_order_count(d)
    daily_usage[d] = {}

    for _ in range(n_orders):
        ts  = random_timestamp(d)
        cid = random.randint(1, 3000)
        pay = random.choices(["cash", "card", "upi"], weights=[15, 50, 35])[0]
        # Delivery lower on rainy days
        if d.month in (7, 8, 9):
            chan_w = [40, 35, 25]
        else:
            chan_w = [50, 30, 20]
        channel = random.choices(["dine-in", "takeaway", "delivery"], weights=chan_w)[0]

        avail = available_items(d)
        n_items = random.choices([1, 2, 3], weights=[45, 38, 17])[0]
        chosen  = random.sample(avail, k=min(n_items, len(avail)))

        # Apply combo rules
        for trigger, pairs in COMBO_RULES.items():
            if trigger in chosen:
                for paired_id, prob in pairs:
                    if paired_id not in chosen and paired_id in avail and random.random() < prob:
                        chosen.append(paired_id)

        order_total = 0.0
        for item_id in chosen:
            qty  = random.choices([1, 2], weights=[88, 12])[0]
            disc = random.choices([0.0, 0.10, 0.15], weights=[78, 14, 8])[0]
            all_order_items.append({
                "line_id":          line_id,
                "order_id":         order_id,
                "item_id":          item_id,
                "quantity":         qty,
                "unit_price":       ITEM_PRICE[item_id],
                "discount_applied": disc,
            })
            order_total += ITEM_PRICE[item_id] * qty * (1 - disc)
            line_id += 1

        all_orders.append({
            "order_id":       order_id,
            "timestamp":      ts,
            "customer_id":    cid,
            "total_amount":   round(order_total, 2),
            "payment_method": pay,
            "channel":        channel,
        })
        order_id += 1

orders_df      = pd.DataFrame(all_orders)
order_items_df = pd.DataFrame(all_order_items)
print(f"  {len(orders_df):,} orders, {len(order_items_df):,} order items")


# ─────────────────────────────────────────────
# TABLE 5 — weather_daily
# ─────────────────────────────────────────────
print("Generating weather data...")

MONTHLY_WEATHER = {
    1:  (28, "sunny",  0.05),
    2:  (30, "sunny",  0.05),
    3:  (33, "sunny",  0.10),
    4:  (36, "sunny",  0.10),
    5:  (35, "cloudy", 0.20),
    6:  (30, "rainy",  0.75),
    7:  (28, "rainy",  0.85),
    8:  (28, "rainy",  0.80),
    9:  (30, "rainy",  0.60),
    10: (32, "cloudy", 0.15),
    11: (30, "sunny",  0.08),
    12: (28, "sunny",  0.05),
}

weather_rows = []
for d in daterange(START, END):
    base_temp, base_cond, rain_prob = MONTHLY_WEATHER[d.month]
    temp = round(base_temp + random.uniform(-2, 2), 1)
    if random.random() < rain_prob:
        cond = "rainy"
    elif base_cond == "cloudy" or random.random() < 0.2:
        cond = "cloudy"
    else:
        cond = "sunny"

    weather_rows.append({
        "date":       d,
        "avg_temp_c": temp,
        "condition":  cond,
        "is_holiday": d in HOLIDAYS,
        "holiday_name": HOLIDAYS[d][0] if d in HOLIDAYS else None,
        "is_weekend": is_weekend(d),
    })

weather_df = pd.DataFrame(weather_rows)


# ─────────────────────────────────────────────
# TABLE 6 — daily_sales_summary
# ─────────────────────────────────────────────
print("Generating daily sales summary...")

orders_df["date"] = pd.to_datetime(orders_df["timestamp"]).dt.date

daily_agg = (
    orders_df.groupby("date")
    .agg(
        total_revenue=("total_amount", "sum"),
        total_orders=("order_id", "count"),
    )
    .reset_index()
)
daily_agg["avg_order_value"] = (daily_agg["total_revenue"] / daily_agg["total_orders"]).round(2)
daily_agg["total_revenue"]   = daily_agg["total_revenue"].round(2)

# Top category per day
oi_with_cat = order_items_df.merge(
    orders_df[["order_id", "date"]], on="order_id"
).merge(
    menu_df[["item_id", "category"]], on="item_id"
)
oi_with_cat["revenue"] = oi_with_cat["unit_price"] * oi_with_cat["quantity"] * (1 - oi_with_cat["discount_applied"])
top_cat = (
    oi_with_cat.groupby(["date", "category"])["revenue"]
    .sum()
    .reset_index()
    .sort_values("revenue", ascending=False)
    .drop_duplicates("date")
    .rename(columns={"category": "top_category"})
    [["date", "top_category"]]
)
daily_sales_df = daily_agg.merge(top_cat, on="date", how="left")

# Footfall ≈ orders × avg party size (1.0 dine-in, takeaway counts 1)
daily_sales_df["footfall"] = (daily_sales_df["total_orders"] * 1.15).astype(int)

# Merge weather flags for Prophet regressors
daily_sales_df = daily_sales_df.merge(
    weather_df[["date", "condition", "is_holiday", "holiday_name", "is_weekend"]],
    on="date", how="left"
)


# ─────────────────────────────────────────────
# TABLE 7 — inventory  (ingredient master)
# ─────────────────────────────────────────────
print("Generating inventory master...")

INGREDIENTS = [
    # id, name,              unit,  reorder_level, supplier
    (1,  "Milk",             "L",    20,   "Amul Dairy"),
    (2,  "Coffee Beans",     "kg",    5,   "Blue Tokai"),
    (3,  "All-Purpose Flour","kg",    8,   "Pillsbury"),
    (4,  "Sugar",            "kg",    5,   "Local Supplier"),
    (5,  "Butter",           "kg",    3,   "Amul Dairy"),
    (6,  "Eggs",             "pcs",  30,   "Local Farm"),
    (7,  "Matcha Powder",    "kg",    1,   "Imported"),
    (8,  "Cold Brew Conc.",  "L",     5,   "Third Wave"),
    (9,  "Cream",            "L",     4,   "Amul Dairy"),
    (10, "Vanilla Extract",  "ml",  200,   "Nielsen-Massey"),
    (11, "Blueberries",      "kg",    2,   "Fresh Market"),
    (12, "Avocado",          "pcs",  15,   "Fresh Market"),
    (13, "Bread",            "loaf",  5,   "Local Bakery"),
    (14, "Chicken",          "kg",    3,   "Venky's"),
    (15, "Cheese",           "kg",    2,   "Amul Dairy"),
    (16, "Cocoa Powder",     "kg",    1,   "Cadbury"),
    (17, "Masala Mix",       "kg",    1,   "MDH"),
    (18, "Puff Pastry",      "pcs",  20,   "Local Bakery"),
    (19, "Cream Cheese",     "kg",    1,   "Dlecta"),
    (20, "Ladyfinger",       "pcs",  30,   "Local Bakery"),
]

inventory_rows = []
for iid, name, unit, reorder_lvl, supplier in INGREDIENTS:
    # Intentionally put 4 items below reorder level
    if iid in (1, 8, 12, 18):
        current = round(reorder_lvl * random.uniform(0.3, 0.8), 1)
    else:
        current = round(reorder_lvl * random.uniform(1.5, 4.0), 1)

    inventory_rows.append({
        "ingredient_id":   iid,
        "name":            name,
        "unit":            unit,
        "current_stock":   current,
        "reorder_level":   reorder_lvl,
        "last_restocked_at": fake.date_between(
            start_date=END - timedelta(days=14), end_date=END
        ),
        "supplier":        supplier,
    })

inventory_df = pd.DataFrame(inventory_rows)


# ─────────────────────────────────────────────
# TABLE 8 — inventory_transactions
# Deplete daily proportional to orders.
# Monday wastage spikes.
# Restocks every ~7–10 days.
# ─────────────────────────────────────────────
print("Generating inventory transactions...")

# How much of each ingredient is used per order (approximate)
USAGE_PER_ORDER = {
    1:  0.25,   # Milk      — 250ml per espresso-based order
    2:  0.018,  # Coffee Beans — 18g per shot
    3:  0.040,  # Flour     — per pastry
    4:  0.015,  # Sugar
    5:  0.020,  # Butter
    6:  0.10,   # Eggs      — fraction per order
    7:  0.005,  # Matcha    — 5g per matcha drink
    8:  0.060,  # Cold Brew concentrate
    9:  0.030,  # Cream
    10: 2.0,    # Vanilla extract (ml)
    11: 0.030,  # Blueberries
    12: 0.05,   # Avocado
    13: 0.10,   # Bread
    14: 0.08,   # Chicken
    15: 0.04,   # Cheese
    16: 0.008,  # Cocoa
    17: 0.005,  # Masala
    18: 0.15,   # Puff pastry
    19: 0.04,   # Cream cheese
    20: 0.20,   # Ladyfinger
}

inv_txns = []
txn_id   = 1
stock    = {row["ingredient_id"]: 50.0 for _, row in inventory_df.iterrows()}
last_restock = {iid: START - timedelta(days=random.randint(1, 7))
                for iid in stock}

orders_by_date = orders_df.groupby("date")["order_id"].count().to_dict()

for d in daterange(START, END):
    n_orders = orders_by_date.get(d, 0)

    # Daily usage
    for iid, rate in USAGE_PER_ORDER.items():
        usage = round(rate * n_orders * random.uniform(0.9, 1.1), 3)
        stock[iid] = max(0, stock[iid] - usage)
        inv_txns.append({
            "txn_id":        txn_id,
            "ingredient_id": iid,
            "type":          "usage",
            "quantity":      -usage,
            "timestamp":     datetime(d.year, d.month, d.day,
                                      random.randint(9, 11), 0, 0),
            "note":          "daily consumption",
        })
        txn_id += 1

    # Monday wastage spike — leftover weekend stock
    if is_monday(d):
        # Perishables get wasted more on Mondays
        for iid in (1, 5, 6, 9, 11, 12, 13, 14):
            waste = round(stock[iid] * random.uniform(0.05, 0.18), 3)
            if waste > 0.01:
                stock[iid] = max(0, stock[iid] - waste)
                inv_txns.append({
                    "txn_id":        txn_id,
                    "ingredient_id": iid,
                    "type":          "wastage",
                    "quantity":      -waste,
                    "timestamp":     datetime(d.year, d.month, d.day, 8, 30, 0),
                    "note":          "Monday clearance — weekend leftover",
                })
                txn_id += 1

    # Restocks: every 7–12 days if below reorder level or due
    for iid, row in inventory_df.set_index("ingredient_id").iterrows():
        days_since = (d - last_restock[iid]).days
        below_reorder = stock[iid] < row["reorder_level"]
        if below_reorder or days_since >= random.randint(7, 12):
            restock_qty = round(row["reorder_level"] * random.uniform(3, 6), 1)
            stock[iid] += restock_qty
            last_restock[iid] = d
            inv_txns.append({
                "txn_id":        txn_id,
                "ingredient_id": iid,
                "type":          "restock",
                "quantity":      restock_qty,
                "timestamp":     datetime(d.year, d.month, d.day, 7, 0, 0),
                "note":          f"restock from {row['supplier']}",
            })
            txn_id += 1

inv_txns_df = pd.DataFrame(inv_txns)
print(f"  {len(inv_txns_df):,} inventory transactions")


# ─────────────────────────────────────────────
# TABLE 9 — reviews
# ─────────────────────────────────────────────
print("Generating reviews...")

# Review template phrases by sentiment + aspect
POSITIVE_FOOD    = ["amazing croissant", "the muffins are to die for", "freshest avocado toast",
                    "brownie was absolutely delicious", "cheesecake worth every bite",
                    "loved the veg puff", "tiramisu was incredible", "banana bread is a must-try"]
POSITIVE_DRINKS  = ["best latte in the city", "cold brew is outstanding", "perfect espresso",
                    "iced matcha was refreshing", "loved the masala chai",
                    "cappuccino was exactly right", "flat white was smooth and rich"]
POSITIVE_SERVICE = ["staff was super friendly", "quick service even during rush hour",
                    "barista remembered my order", "always greeted with a smile",
                    "great vibe and attentive staff"]
POSITIVE_AMBIENCE= ["cozy atmosphere", "great place to work", "beautiful interiors",
                    "love the playlist", "perfect for a coffee date", "very Instagrammable"]

NEGATIVE_SERVICE = ["slow service on weekends", "waited 20 minutes for a latte",
                    "staff seemed overwhelmed during lunch", "took too long to get my order",
                    "understaffed on weekday afternoons", "service could be much faster"]
NEGATIVE_PRICE   = ["a bit pricey for the portion size", "overpriced compared to nearby cafes",
                    "good but not worth the price", "expensive for a regular cafe",
                    "wish the prices were more reasonable"]
NEGATIVE_FOOD    = ["croissant was stale", "sandwich was a bit bland",
                    "coffee was lukewarm", "muffin felt store-bought"]
NEGATIVE_AMBIENCE= ["too noisy to work", "parking is a nightmare",
                    "seating is cramped", "AC was too cold"]

def build_review(sentiment: str, d: date) -> tuple[str, list[str]]:
    """Return (review_text, aspect_tags)."""
    tags = []
    parts = []

    if sentiment == "positive":
        picks = random.sample(POSITIVE_DRINKS + POSITIVE_FOOD, k=random.randint(1, 2))
        parts.extend(picks)
        tags.append("food_positive")
        tags.append("drinks_positive")
        if random.random() < 0.6:
            parts.append(random.choice(POSITIVE_SERVICE))
            tags.append("service_positive")
        if random.random() < 0.4:
            parts.append(random.choice(POSITIVE_AMBIENCE))
            tags.append("ambience_positive")

    elif sentiment == "negative":
        # Service complaints cluster on weekday afternoons
        if not is_weekend(d) and random.random() < 0.55:
            parts.append(random.choice(NEGATIVE_SERVICE))
            tags.append("service_negative")
        if random.random() < 0.45:
            parts.append(random.choice(NEGATIVE_PRICE))
            tags.append("price_negative")
        if random.random() < 0.35:
            parts.append(random.choice(NEGATIVE_FOOD))
            tags.append("food_negative")
        if not parts:
            parts.append(random.choice(NEGATIVE_AMBIENCE))
            tags.append("ambience_negative")

    else:  # neutral
        parts.append(random.choice(POSITIVE_DRINKS))
        parts.append(random.choice(NEGATIVE_PRICE))
        tags = ["drinks_positive", "price_negative"]

    text = ". ".join(p.capitalize() for p in parts) + "."
    return text, tags

reviews = []
review_id = 1

for d in daterange(START, END):
    # 4–8 reviews per day on weekends, 1–4 on weekdays
    n = random.randint(4, 8) if is_weekend(d) else random.randint(1, 4)
    for _ in range(n):
        # Sentiment distribution: 65% positive, 20% negative, 15% neutral
        sentiment = random.choices(
            ["positive", "negative", "neutral"], weights=[65, 20, 15]
        )[0]
        # Rating aligned to sentiment
        if sentiment == "positive":
            rating = random.choices([4, 5], weights=[30, 70])[0]
        elif sentiment == "negative":
            rating = random.choices([1, 2, 3], weights=[20, 40, 40])[0]
        else:
            rating = random.choices([3, 4], weights=[60, 40])[0]

        text, tags = build_review(sentiment, d)
        source = random.choices(["Google", "Zomato"], weights=[60, 40])[0]

        reviews.append({
            "review_id":   review_id,
            "source":      source,
            "rating":      rating,
            "review_text": text,
            "sentiment":   sentiment,
            "aspect_tags": ",".join(tags),
            "date":        d,
        })
        review_id += 1

reviews_df = pd.DataFrame(reviews)
print(f"  {len(reviews_df):,} reviews")


# ─────────────────────────────────────────────
# PUSH ALL TABLES TO POSTGRESQL
# ─────────────────────────────────────────────
print("\nPushing to PostgreSQL...")

TABLES = [
    (customers_df,      "customers"),
    (menu_df,           "menu_items"),
    (orders_df,         "orders"),
    (order_items_df,    "order_items"),
    (weather_df,        "weather_daily"),
    (daily_sales_df,    "daily_sales_summary"),
    (inventory_df,      "inventory"),
    (inv_txns_df,       "inventory_transactions"),
    (reviews_df,        "reviews"),
]

for df, table_name in TABLES:
    df.to_sql(table_name, engine, if_exists="replace", index=False)
    print(f"  {table_name:<28} {len(df):>7,} rows pushed")

# ── Verify row counts ──
from sqlalchemy import text as sa_text
print("\nVerification:")
with engine.connect() as conn:
    for _, table_name in TABLES:
        result = conn.execute(sa_text(f"SELECT COUNT(*) FROM {table_name}"))
        count  = result.scalar()
        print(f"  {table_name:<28} -> {count:,} rows")

print("\nDone. All tables seeded successfully.")