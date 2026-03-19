from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database import get_db
from services import mba_service
from schemas.mba import MBAResult, AssociationRule, ProductPairCount, BundleSuggestion

router = APIRouter(tags=["Market Basket Analysis"])


@router.get("/results", response_model=MBAResult)
def get_mba_results(
    min_support:    float = Query(default=0.01,  ge=0.001, le=1.0,
                                  description="Minimum support threshold (0.01 = 1% of orders)"),
    min_confidence: float = Query(default=0.20,  ge=0.01,  le=1.0,
                                  description="Minimum confidence threshold (0.20 = 20%)"),
    min_lift:       float = Query(default=1.0,   ge=0.1,
                                  description="Minimum lift — 1.0 means better than random"),
    db: Session = Depends(get_db),
):
    """
    Full MBA pipeline — returns association rules, product pair
    co-occurrence counts, and bundle suggestions.

    Tune the thresholds to surface stronger or weaker rules:
    - Lower min_support  → more rules (including rare pairs)
    - Higher min_confidence → only high-probability rules
    - Higher min_lift    → only rules stronger than random chance
    """
    return mba_service.get_mba_results(db, min_support, min_confidence, min_lift)


@router.get("/rules", response_model=list[AssociationRule])
def get_rules(
    min_support:    float = Query(default=0.01, ge=0.001, le=1.0),
    min_confidence: float = Query(default=0.20, ge=0.01,  le=1.0),
    min_lift:       float = Query(default=1.0,  ge=0.1),
    db: Session = Depends(get_db),
):
    """Association rules only — for the rules table on the frontend."""
    result = mba_service.get_mba_results(db, min_support, min_confidence, min_lift)
    return result.rules


@router.get("/product-pairs", response_model=list[ProductPairCount])
def get_product_pairs(
    db: Session = Depends(get_db),
):
    """
    Top 40 item pairs by raw co-occurrence count.
    Feeds the product pair heatmap — no threshold filtering needed.
    """
    return mba_service._get_product_pairs(db)


@router.get("/bundle-suggestions", response_model=list[BundleSuggestion])
def get_bundle_suggestions(
    min_support:    float = Query(default=0.01, ge=0.001, le=1.0),
    min_confidence: float = Query(default=0.20, ge=0.01,  le=1.0),
    min_lift:       float = Query(default=1.0,  ge=0.1),
    db: Session = Depends(get_db),
):
    """
    Top 10 bundle suggestions with human-readable insight text.
    Ready to render as cards on the frontend.
    """
    result = mba_service.get_mba_results(db, min_support, min_confidence, min_lift)
    return result.bundle_suggestions