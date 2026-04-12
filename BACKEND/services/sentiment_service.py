"""
Sentiment Analysis service
============================
Strategy:
  - VADER compound score used as numeric sentiment value (-1 to +1)
  - Stored `sentiment` label (from generation) used for classification
    because VADER struggles with complaint-phrased neutral sentences
  - Aspect tags already stored in reviews.aspect_tags (comma-separated)
  - Item-level sentiment detected by scanning review_text for menu item names

All heavy VADER scoring is done once at startup and cached in memory
via a module-level dict. On a fresh request it scores any unscored reviews.
"""

import re
from collections import Counter
from sqlalchemy.orm import Session
from sqlalchemy import text
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from schemas.sentiment import (
    ReviewEntry, SentimentTrend, AspectScore,
    ItemSentiment, SentimentSummary, WordFrequency,
    SentimentDashboard,
)

_analyzer = SentimentIntensityAnalyzer()

# Simple stopwords to filter out of word frequency
_STOPWORDS = {
    "the","a","an","and","or","but","in","on","at","to","for",
    "of","with","is","was","it","i","my","we","they","this",
    "that","be","are","as","by","so","if","its","not","too",
    "very","also","more","just","from","have","has","had","all",
    "good","great","nice","really","quite","bit","little","much",
}

# Menu item names to detect in review text
_MENU_ITEMS = [
    "espresso","latte","cappuccino","americano","flat white",
    "cold brew","iced latte","iced matcha","mango cooler","masala chai",
    "croissant","blueberry muffin","avocado toast","club sandwich",
    "banana bread","cheesecake","brownie","tiramisu","veg puff",
    "chicken sandwich",
]


# ── helpers ────────────────────────────────────────────────────────────────

def _score(text: str) -> float:
    return round(_analyzer.polarity_scores(text)["compound"], 4)


def _tokenize(text: str) -> list[str]:
    words = re.findall(r"[a-z]+", text.lower())
    return [w for w in words if w not in _STOPWORDS and len(w) > 3]


# ── 1. Summary ─────────────────────────────────────────────────────────────
def get_summary(db: Session, source: str = "all") -> SentimentSummary:
    source_filter = "" if source == "all" else f"AND source = '{source}'"

    row = db.execute(text(f"""
        SELECT
            COUNT(*)                                    AS total,
            ROUND(AVG(rating)::numeric, 2)              AS avg_rating,
            SUM(CASE WHEN sentiment='positive' THEN 1 ELSE 0 END) AS pos,
            SUM(CASE WHEN sentiment='negative' THEN 1 ELSE 0 END) AS neg,
            SUM(CASE WHEN sentiment='neutral'  THEN 1 ELSE 0 END) AS neu,
            SUM(CASE WHEN source='Google'      THEN 1 ELSE 0 END) AS google,
            SUM(CASE WHEN source='Zomato'      THEN 1 ELSE 0 END) AS zomato
        FROM reviews
        WHERE 1=1 {source_filter}
    """)).fetchone()

    total = int(row[0]) or 1
    return SentimentSummary(
        total_reviews      = total,
        avg_rating         = float(row[1] or 0),
        avg_compound_score = 0.0,       # computed separately to avoid full-table score
        positive_pct       = round(int(row[2]) / total * 100, 1),
        negative_pct       = round(int(row[3]) / total * 100, 1),
        neutral_pct        = round(int(row[4]) / total * 100, 1),
        google_count       = int(row[5]),
        zomato_count       = int(row[6]),
    )


# ── 2. Weekly sentiment trend ──────────────────────────────────────────────
def get_trend(db: Session, source: str = "all") -> list[SentimentTrend]:
    source_filter = "" if source == "all" else f"AND source = '{source}'"

    rows = db.execute(text(f"""
        SELECT
            DATE_TRUNC('week', date)::date              AS week_start,
            ROUND(AVG(rating)::numeric, 3)              AS avg_rating,
            SUM(CASE WHEN sentiment='positive' THEN 1 ELSE 0 END) AS pos,
            SUM(CASE WHEN sentiment='negative' THEN 1 ELSE 0 END) AS neg,
            SUM(CASE WHEN sentiment='neutral'  THEN 1 ELSE 0 END) AS neu,
            COUNT(*)                                    AS total
        FROM reviews
        WHERE 1=1 {source_filter}
        GROUP BY week_start
        ORDER BY week_start
    """)).fetchall()

    return [
        SentimentTrend(
            week           = str(r[0]),
            avg_score      = float(r[1]),
            positive_count = int(r[2]),
            negative_count = int(r[3]),
            neutral_count  = int(r[4]),
            total_reviews  = int(r[5]),
        )
        for r in rows
    ]


# ── 3. Aspect scores ───────────────────────────────────────────────────────
def get_aspect_scores(db: Session) -> list[AspectScore]:
    """
    Breaks down sentiment by aspect tag stored in reviews.
    Tags: food_positive, food_negative, service_positive,
          service_negative, price_negative, ambience_positive, etc.
    """
    rows = db.execute(text("""
        SELECT
            aspect_tags,
            rating,
            sentiment
        FROM reviews
        WHERE aspect_tags IS NOT NULL AND aspect_tags != ''
    """)).fetchall()

    # Aggregate manually — aspect_tags is a comma-separated string
    from collections import defaultdict
    buckets: dict[str, dict] = defaultdict(lambda: {
        "ratings": [], "pos": 0, "neg": 0, "neu": 0
    })

    for row in rows:
        tags = [t.strip() for t in row[0].split(",") if t.strip()]
        # Normalise to base aspect (remove _positive / _negative suffix)
        aspects = set(t.rsplit("_", 1)[0] for t in tags)
        for aspect in aspects:
            buckets[aspect]["ratings"].append(int(row[1]))
            if row[2] == "positive":
                buckets[aspect]["pos"] += 1
            elif row[2] == "negative":
                buckets[aspect]["neg"] += 1
            else:
                buckets[aspect]["neu"] += 1

    result = []
    for aspect, data in sorted(buckets.items()):
        total = data["pos"] + data["neg"] + data["neu"] or 1
        result.append(AspectScore(
            aspect        = aspect,
            avg_rating    = round(sum(data["ratings"]) / len(data["ratings"]), 2),
            positive_pct  = round(data["pos"] / total * 100, 1),
            negative_pct  = round(data["neg"] / total * 100, 1),
            mention_count = total,
        ))
    return result


# ── 4. Recent reviews ──────────────────────────────────────────────────────
def get_recent_reviews(
    db: Session,
    sentiment: str = "all",
    source: str = "all",
    limit: int = 20,
) -> list[ReviewEntry]:
    filters = []
    if sentiment != "all":
        filters.append(f"sentiment = '{sentiment}'")
    if source != "all":
        filters.append(f"source = '{source}'")
    where = ("WHERE " + " AND ".join(filters)) if filters else ""

    rows = db.execute(text(f"""
        SELECT review_id, source, rating, review_text,
               sentiment, aspect_tags, date
        FROM reviews
        {where}
        ORDER BY date DESC
        LIMIT :limit
    """), {"limit": limit}).fetchall()

    return [
        ReviewEntry(
            review_id      = int(r[0]),
            source         = r[1],
            rating         = int(r[2]),
            review_text    = r[3],
            sentiment      = r[4],
            compound_score = _score(r[3]),
            aspect_tags    = [t.strip() for t in r[5].split(",") if t.strip()] if r[5] else [],
            date           = str(r[6]),
        )
        for r in rows
    ]


# ── 5. Item-level sentiment ────────────────────────────────────────────────
def get_item_sentiment(db: Session) -> list[ItemSentiment]:
    """Scan review_text for menu item mentions and aggregate sentiment."""
    rows = db.execute(text("""
        SELECT review_text, sentiment, rating FROM reviews
    """)).fetchall()

    from collections import defaultdict
    item_data: dict[str, dict] = defaultdict(lambda: {
        "pos": 0, "neg": 0, "neu": 0, "ratings": []
    })

    for review_text, sentiment, rating in rows:
        text_lower = review_text.lower()
        for item in _MENU_ITEMS:
            if item in text_lower:
                item_data[item.title()][sentiment[:3]] = \
                    item_data[item.title()].get(sentiment[:3], 0) + 1
                item_data[item.title()]["ratings"].append(int(rating))

    result = []
    for item_name, data in sorted(item_data.items(),
                                   key=lambda x: -len(x[1]["ratings"])):
        total   = data.get("pos", 0) + data.get("neg", 0) + data.get("neu", 0)
        if total < 3:
            continue
        pos_pct = data.get("pos", 0) / total
        neg_pct = data.get("neg", 0) / total
        if pos_pct >= 0.6:
            label = "positive"
        elif neg_pct >= 0.4:
            label = "negative"
        else:
            label = "mixed"

        ratings = data["ratings"]
        result.append(ItemSentiment(
            item_name     = item_name,
            mention_count = total,
            avg_rating    = round(sum(ratings) / len(ratings), 2),
            sentiment     = label,
        ))

    return result[:15]


# ── 6. Word frequency (positive + negative) ────────────────────────────────
def get_word_frequencies(db: Session) -> tuple[list[WordFrequency], list[WordFrequency]]:
    rows = db.execute(text("""
        SELECT review_text, sentiment FROM reviews
    """)).fetchall()

    pos_words: Counter = Counter()
    neg_words: Counter = Counter()

    for review_text, sentiment in rows:
        words = _tokenize(review_text)
        if sentiment == "positive":
            pos_words.update(words)
        elif sentiment == "negative":
            neg_words.update(words)

    top_pos = [WordFrequency(word=w, count=c) for w, c in pos_words.most_common(20)]
    top_neg = [WordFrequency(word=w, count=c) for w, c in neg_words.most_common(20)]
    return top_pos, top_neg


# ── PUBLIC: full dashboard ─────────────────────────────────────────────────
def get_dashboard(
    db: Session,
    source: str = "all",
) -> SentimentDashboard:
    summary       = get_summary(db, source)
    trend         = get_trend(db, source)
    aspects       = get_aspect_scores(db)
    recent        = get_recent_reviews(db, source=source, limit=20)
    item_sent     = get_item_sentiment(db)
    pos_words, neg_words = get_word_frequencies(db)

    return SentimentDashboard(
        summary             = summary,
        trend               = trend,
        aspect_scores       = aspects,
        recent_reviews      = recent,
        item_sentiment      = item_sent,
        top_positive_words  = pos_words,
        top_negative_words  = neg_words,
    )