from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database import get_db
from services import inventory_service
from schemas.inventory import (
    InventoryDashboard, StockStatus, DepletionRate,
    ReorderSuggestion, WastageSummary, WastageByDay,
)

router = APIRouter(tags=["Inventory"])


@router.get("/dashboard", response_model=InventoryDashboard)
def get_dashboard(db: Session = Depends(get_db)):
    """
    Full inventory dashboard — stock status, depletion rates,
    reorder suggestions, wastage trend, and weekday wastage breakdown.
    """
    return inventory_service.get_dashboard(db)


@router.get("/stock-status", response_model=list[StockStatus])
def get_stock_status(db: Session = Depends(get_db)):
    """
    All ingredients with current stock, reorder level, status badge
    (ok / low / critical) and estimated days until empty.
    Sorted: critical → low → ok.
    """
    return inventory_service.get_stock_status(db)


@router.get("/depletion-rates", response_model=list[DepletionRate])
def get_depletion_rates(db: Session = Depends(get_db)):
    """
    Average daily consumption per ingredient over the last 30 days.
    Feeds the depletion rate bar chart.
    """
    return inventory_service.get_depletion_rates(db)


@router.get("/reorder-suggestions", response_model=list[ReorderSuggestion])
def get_reorder_suggestions(db: Session = Depends(get_db)):
    """
    Items at or below 1.5× reorder level with urgency classification
    (critical / low / scheduled) and suggested order quantities.
    """
    return inventory_service.get_reorder_suggestions(db)


@router.get("/wastage-trend", response_model=list[WastageSummary])
def get_wastage_trend(
    days: int = Query(default=60, ge=7, le=365,
                      description="Number of days of wastage history to return"),
    db: Session = Depends(get_db),
):
    """
    Daily wastage event count over the last N days.
    Feeds the wastage trend line chart.
    """
    return inventory_service.get_wastage_trend(db, days)


@router.get("/wastage-by-weekday", response_model=list[WastageByDay])
def get_wastage_by_weekday(db: Session = Depends(get_db)):
    """
    Total wastage grouped by day of week — confirms the Monday spike.
    Feeds the bar chart showing which days waste the most.
    """
    return inventory_service.get_wastage_by_weekday(db)