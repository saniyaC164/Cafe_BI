from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database import get_db
from services import forecasting_service
from schemas.forecasting import (
    ForecastDashboard, ForecastPoint, ForecastSummary,
    SeasonalComponent, HolidayEffect, WeatherCorrelation,
)

router = APIRouter(tags=["Forecasting"])


@router.get("/dashboard", response_model=ForecastDashboard)
def get_dashboard(
    horizon: int = Query(
        default=30, ge=7, le=90,
        description="Forecast horizon in days (7–90)"
    ),
    db: Session = Depends(get_db),
):
    """
    Full forecasting dashboard — Prophet-generated forecast with
    confidence bands, seasonal components, holiday effects, and
    weather correlation.

    Note: Takes ~3–5 seconds on first call (model training).
    """
    return forecasting_service.get_dashboard(db, horizon)


@router.get("/forecast", response_model=list[ForecastPoint])
def get_forecast(
    horizon: int = Query(default=30, ge=7, le=90),
    db: Session = Depends(get_db),
):
    """
    Forecast points only — last 90 days of actuals + next N days predicted.
    Each point includes yhat, lower and upper confidence bounds, and
    a flag indicating whether it is actual or predicted.
    Feeds the main forecast line chart.
    """
    return forecasting_service.get_forecast_only(db, horizon)


@router.get("/summary", response_model=ForecastSummary)
def get_summary(
    horizon: int = Query(default=30, ge=7, le=90),
    db: Session = Depends(get_db),
):
    """
    Summary tiles — predicted revenue for next 7 and 30 days,
    trend direction, and strongest/weakest trading day.
    """
    result = forecasting_service.get_dashboard(db, horizon)
    return result.summary


@router.get("/weather-correlation", response_model=list[WeatherCorrelation])
def get_weather_correlation(db: Session = Depends(get_db)):
    """
    Average daily revenue and order count grouped by weather condition.
    Shows rainy-day vs sunny-day revenue difference.
    No model training needed — pure SQL.
    """
    return forecasting_service.get_weather_correlation(db)


@router.get("/holiday-effects", response_model=list[HolidayEffect])
def get_holiday_effects(
    horizon: int = Query(default=30, ge=7, le=90),
    db: Session = Depends(get_db),
):
    """
    Estimated revenue impact of each Mumbai public holiday
    as detected by Prophet's holiday component.
    """
    result = forecasting_service.get_dashboard(db, horizon)
    return result.holiday_effects