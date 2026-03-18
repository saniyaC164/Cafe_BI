from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Literal

from database import get_db
from services import kpi_service
from schemas.kpi import (
    KPIDashboard, KPISummary, RevenueByDay,
    TopItem, ChannelSplit, HourlyHeatmap,
    CustomerStats, PaymentSplit,
)

router = APIRouter(tags=["KPI"])

Period = Literal["7d", "30d", "90d", "365d", "all"]


@router.get("/dashboard", response_model=KPIDashboard)
def get_full_dashboard(
    period: Period = Query(default="30d", description="Time window: 7d | 30d | 90d | 365d | all"),
    db: Session = Depends(get_db),
):
    """
    Returns all KPI data in one call — summary tiles, revenue trend,
    top items, channel split, hourly heatmap, customer stats, payment split.
    """
    return kpi_service.get_dashboard(db, period)


@router.get("/summary", response_model=KPISummary)
def get_summary(
    period: Period = Query(default="30d"),
    db: Session = Depends(get_db),
):
    """Revenue, orders, AOV and profit margin for the selected period."""
    return kpi_service.get_summary(db, period)


@router.get("/revenue-trend", response_model=list[RevenueByDay])
def get_revenue_trend(
    period: Period = Query(default="30d"),
    db: Session = Depends(get_db),
):
    """Daily revenue and order count — feeds the line chart."""
    return kpi_service.get_revenue_trend(db, period)


@router.get("/top-items", response_model=list[TopItem])
def get_top_items(
    period: Period = Query(default="30d"),
    db: Session = Depends(get_db),
):
    """Top 10 menu items by revenue — feeds the bar chart."""
    return kpi_service.get_top_items(db, period)


@router.get("/channel-split", response_model=list[ChannelSplit])
def get_channel_split(
    period: Period = Query(default="30d"),
    db: Session = Depends(get_db),
):
    """Orders and revenue split by dine-in / takeaway / delivery."""
    return kpi_service.get_channel_split(db, period)


@router.get("/hourly-heatmap", response_model=list[HourlyHeatmap])
def get_hourly_heatmap(
    period: Period = Query(default="30d"),
    db: Session = Depends(get_db),
):
    """Order counts by hour × day-of-week — feeds the heatmap grid."""
    return kpi_service.get_hourly_heatmap(db, period)


@router.get("/customer-stats", response_model=CustomerStats)
def get_customer_stats(
    period: Period = Query(default="30d"),
    db: Session = Depends(get_db),
):
    """Total customers, repeat rate, and segment breakdown."""
    return kpi_service.get_customer_stats(db, period)


@router.get("/payment-split", response_model=list[PaymentSplit])
def get_payment_split(
    period: Period = Query(default="30d"),
    db: Session = Depends(get_db),
):
    """Payment method breakdown — cash / card / UPI."""
    return kpi_service.get_payment_split(db, period)