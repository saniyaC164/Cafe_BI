from pydantic import BaseModel
from typing import List, Optional


class ReviewEntry(BaseModel):
    review_id:     int
    source:        str          # Google | Zomato
    rating:        int          # 1–5
    review_text:   str
    sentiment:     str          # positive | negative | neutral
    compound_score: float       # VADER compound -1.0 to +1.0
    aspect_tags:   List[str]
    date:          str


class SentimentTrend(BaseModel):
    week:              str      # ISO week start date
    avg_score:         float    # avg VADER compound score
    positive_count:    int
    negative_count:    int
    neutral_count:     int
    total_reviews:     int


class AspectScore(BaseModel):
    aspect:        str          # food | service | price | ambience
    avg_rating:    float        # avg star rating for reviews tagged with this aspect
    positive_pct:  float
    negative_pct:  float
    mention_count: int


class ItemSentiment(BaseModel):
    item_name:     str
    mention_count: int
    avg_rating:    float
    sentiment:     str          # positive | mixed | negative


class SentimentSummary(BaseModel):
    total_reviews:      int
    avg_rating:         float
    avg_compound_score: float
    positive_pct:       float
    negative_pct:       float
    neutral_pct:        float
    google_count:       int
    zomato_count:       int


class WordFrequency(BaseModel):
    word:  str
    count: int


class SentimentDashboard(BaseModel):
    summary:         SentimentSummary
    trend:           List[SentimentTrend]
    aspect_scores:   List[AspectScore]
    recent_reviews:  List[ReviewEntry]
    item_sentiment:  List[ItemSentiment]
    top_negative_words: List[WordFrequency]
    top_positive_words: List[WordFrequency]