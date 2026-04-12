from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Literal

from database import get_db
from services import sentiment_service
from schemas.sentiment import (
    SentimentDashboard, SentimentSummary, SentimentTrend,
    AspectScore, ReviewEntry, ItemSentiment, WordFrequency,
)

router = APIRouter(tags=["Sentiment Analysis"])

Source    = Literal["all", "Google", "Zomato"]
Sentiment = Literal["all", "positive", "negative", "neutral"]


@router.get("/dashboard", response_model=SentimentDashboard)
def get_dashboard(
    source: Source = Query(default="all", description="Filter by review source"),
    db: Session = Depends(get_db),
):
    """
    Full sentiment dashboard — summary stats, weekly trend, aspect
    breakdown, recent reviews, item-level sentiment, word frequencies.
    """
    return sentiment_service.get_dashboard(db, source)


@router.get("/summary", response_model=SentimentSummary)
def get_summary(
    source: Source = Query(default="all"),
    db: Session = Depends(get_db),
):
    """Overall sentiment summary — totals, avg rating, % breakdown."""
    return sentiment_service.get_summary(db, source)


@router.get("/trend", response_model=list[SentimentTrend])
def get_trend(
    source: Source = Query(default="all"),
    db: Session = Depends(get_db),
):
    """
    Weekly sentiment trend — avg score + positive/negative/neutral counts.
    Feeds the trend line chart.
    """
    return sentiment_service.get_trend(db, source)


@router.get("/aspects", response_model=list[AspectScore])
def get_aspect_scores(db: Session = Depends(get_db)):
    """
    Sentiment broken down by aspect — food, service, price, ambience.
    Feeds the aspect radar/bar chart.
    """
    return sentiment_service.get_aspect_scores(db)


@router.get("/reviews", response_model=list[ReviewEntry])
def get_reviews(
    sentiment: Sentiment = Query(default="all",   description="Filter by sentiment label"),
    source:    Source    = Query(default="all",   description="Filter by review source"),
    limit:     int       = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    Recent reviews with VADER compound score and aspect tags.
    Supports filtering by sentiment and source.
    """
    return sentiment_service.get_recent_reviews(db, sentiment, source, limit)


@router.get("/items", response_model=list[ItemSentiment])
def get_item_sentiment(db: Session = Depends(get_db)):
    """
    Sentiment per menu item detected from review text.
    Shows which items are praised or complained about most.
    """
    return sentiment_service.get_item_sentiment(db)


@router.get("/words/positive", response_model=list[WordFrequency])
def get_positive_words(db: Session = Depends(get_db)):
    """Top 20 words in positive reviews — feeds the positive word cloud."""
    pos, _ = sentiment_service.get_word_frequencies(db)
    return pos


@router.get("/words/negative", response_model=list[WordFrequency])
def get_negative_words(db: Session = Depends(get_db)):
    """Top 20 words in negative reviews — feeds the negative word cloud."""
    _, neg = sentiment_service.get_word_frequencies(db)
    return neg