"""
Market Basket Analysis service
================================
Pipeline:
  1. Pull order_items + menu_items from Postgres
  2. Build a transaction matrix (one-hot encoded)
  3. Run Apriori to find frequent itemsets
  4. Generate association rules (confidence, lift, support)
  5. Return rules + product pair counts + bundle suggestions
"""

import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import text
from mlxtend.frequent_patterns import apriori, association_rules
from mlxtend.preprocessing import TransactionEncoder

from schemas.mba import AssociationRule, ProductPairCount, BundleSuggestion, MBAResult


# ── 1. Load transactions from DB ───────────────────────────────────────────
def _load_transactions(db: Session, min_orders: int) -> tuple[list[list[str]], int]:
    """
    Returns a list of baskets, e.g.:
      [["Latte", "Croissant"], ["Espresso"], ["Cold Brew", "Blueberry Muffin"], ...]
    and the total order count.
    """
    rows = db.execute(text("""
        SELECT o.order_id, m.name
        FROM order_items oi
        JOIN orders     o  ON oi.order_id = o.order_id
        JOIN menu_items m  ON oi.item_id  = m.item_id
        ORDER BY o.order_id
    """)).fetchall()

    if not rows:
        return [], 0

    df = pd.DataFrame(rows, columns=["order_id", "item_name"])
    baskets = df.groupby("order_id")["item_name"].apply(list).tolist()
    return baskets, len(baskets)


# ── 2. Run Apriori ─────────────────────────────────────────────────────────
def _run_apriori(
    baskets: list[list[str]],
    min_support: float,
    min_confidence: float,
    min_lift: float,
) -> pd.DataFrame:
    """Encode transactions and return association rules DataFrame."""
    te = TransactionEncoder()
    te_array = te.fit(baskets).transform(baskets)
    basket_df = pd.DataFrame(te_array, columns=te.columns_)

    frequent_itemsets = apriori(
        basket_df,
        min_support=min_support,
        use_colnames=True,
        max_len=2,          # pairs only — keeps it interpretable
    )

    if frequent_itemsets.empty:
        return pd.DataFrame()

    rules = association_rules(
        frequent_itemsets,
        metric="lift",
        min_threshold=min_lift,
        num_itemsets=len(frequent_itemsets),
    )
    rules = rules[rules["confidence"] >= min_confidence]
    return rules


# ── 3. Product pair co-occurrence counts ───────────────────────────────────
def _get_product_pairs(db: Session, top_n: int = 40) -> list[ProductPairCount]:
    """
    Raw co-occurrence count for every item pair —
    feeds the heatmap without needing Apriori.
    """
    rows = db.execute(text("""
        SELECT
            m1.name   AS item_a,
            m2.name   AS item_b,
            COUNT(*)  AS co_count
        FROM order_items oi1
        JOIN order_items oi2 ON oi1.order_id = oi2.order_id
                             AND oi1.item_id < oi2.item_id
        JOIN menu_items m1   ON oi1.item_id = m1.item_id
        JOIN menu_items m2   ON oi2.item_id = m2.item_id
        GROUP BY m1.name, m2.name
        ORDER BY co_count DESC
        LIMIT :top_n
    """), {"top_n": top_n}).fetchall()

    return [
        ProductPairCount(item_a=r[0], item_b=r[1], co_count=int(r[2]))
        for r in rows
    ]


# ── 4. Build human-readable bundle suggestions ─────────────────────────────
def _build_bundle_suggestions(rules: pd.DataFrame) -> list[BundleSuggestion]:
    """
    Take the top rules by lift and turn them into UI-ready cards.
    Only includes 1-item → 1-item rules for clarity.
    """
    suggestions = []

    # Filter to single-item antecedent and consequent
    single_rules = rules[
        rules["antecedents"].apply(len) == 1
    ].copy()
    single_rules = single_rules[
        single_rules["consequents"].apply(len) == 1
    ]
    single_rules = single_rules.sort_values("lift", ascending=False).head(10)

    for _, row in single_rules.iterrows():
        trigger = list(row["antecedents"])[0]
        paired  = list(row["consequents"])[0]
        conf    = round(float(row["confidence"]) * 100, 1)
        lift    = round(float(row["lift"]), 2)

        insight = (
            f"Customers who order {trigger} also order {paired} "
            f"{conf}% of the time (lift {lift}x) — "
            f"consider bundling as a combo deal."
        )

        suggestions.append(BundleSuggestion(
            trigger_item   = trigger,
            paired_item    = paired,
            confidence_pct = conf,
            lift           = lift,
            insight        = insight,
        ))

    return suggestions


# ── 5. Format rules for API response ──────────────────────────────────────
def _format_rules(rules: pd.DataFrame, top_n: int = 20) -> list[AssociationRule]:
    if rules.empty:
        return []

    top = rules.sort_values("lift", ascending=False).head(top_n)
    result = []
    for _, row in top.iterrows():
        antecedent = ", ".join(sorted(row["antecedents"]))
        consequent = ", ".join(sorted(row["consequents"]))
        result.append(AssociationRule(
            antecedent = antecedent,
            consequent = consequent,
            support    = round(float(row["support"]), 4),
            confidence = round(float(row["confidence"]), 4),
            lift       = round(float(row["lift"]), 4),
        ))
    return result


# ── PUBLIC: main entry point ───────────────────────────────────────────────
def get_mba_results(
    db:             Session,
    min_support:    float = 0.01,   # item pair appears in ≥1% of orders
    min_confidence: float = 0.20,   # rule fires ≥20% of the time
    min_lift:       float = 1.0,    # rule is better than random
) -> MBAResult:
    baskets, total_orders = _load_transactions(db, min_orders=2)

    if not baskets:
        return MBAResult(
            rules=[],
            product_pairs=[],
            bundle_suggestions=[],
            total_orders_analysed=0,
        )

    rules_df      = _run_apriori(baskets, min_support, min_confidence, min_lift)
    formatted     = _format_rules(rules_df)
    pairs         = _get_product_pairs(db)
    bundles       = _build_bundle_suggestions(rules_df) if not rules_df.empty else []

    return MBAResult(
        rules                 = formatted,
        product_pairs         = pairs,
        bundle_suggestions    = bundles,
        total_orders_analysed = total_orders,
    )