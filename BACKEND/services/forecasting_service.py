"""
Sales Forecasting service
===========================
Uses Facebook Prophet to forecast daily revenue 30 days ahead.

Pipeline:
  1. Load daily_sales_summary from Postgres as time series
  2. Build Mumbai holidays dataframe for Prophet
  3. Train Prophet with multiplicative seasonality
     (better for data where seasonal swings are % of trend)
  4. Forecast 30 days forward with confidence intervals
  5. Extract seasonal components (weekly + yearly patterns)
  6. Compute holiday effects and weather correlation
  7. Return full dashboard payload

Model is trained on every request (fast enough at 366 rows).
For production, cache the trained model in Redis or retrain nightly.
"""

import warnings
warnings.filterwarnings("ignore")

import pandas as pd
import numpy as np
from prophet import Prophet
from sqlalchemy.orm import Session
from sqlalchemy import text

from schemas.forecasting import (
    ForecastPoint, SeasonalComponent, ForecastSummary,
    HolidayEffect, WeatherCorrelation, ForecastDashboard,
)

# ── Mumbai public holidays (used as Prophet regressors) ───────────────────
MUMBAI_HOLIDAYS = pd.DataFrame({
    "holiday": [
        "republic_day", "holi", "ram_navami",
        "independence_day", "janmashtami", "gandhi_jayanti",
        "dussehra",
        "diwali_eve", "diwali", "diwali_2", "diwali_3",
        "christmas", "new_year_eve",
    ],
    "ds": pd.to_datetime([
        "2024-01-26", "2024-03-25", "2024-04-17",
        "2024-08-15", "2024-08-26", "2024-10-02",
        "2024-10-12",
        "2024-10-31", "2024-11-01", "2024-11-02", "2024-11-03",
        "2024-12-25", "2024-12-31",
    ]),
    "lower_window": [-1, 0, 0, 0, 0, 0, 0, 0, -1, 0, 0, -1, 0],
    "upper_window": [ 1, 1, 0, 0, 0, 0, 1, 1,  1, 1, 0,  1, 1],
})


# ── 1. Load time-series from DB ────────────────────────────────────────────
def _load_timeseries(db: Session) -> pd.DataFrame:
    rows = db.execute(text("""
        SELECT date, total_revenue
        FROM daily_sales_summary
        ORDER BY date
    """)).fetchall()

    df = pd.DataFrame(rows, columns=["ds", "y"])
    df["ds"] = pd.to_datetime(df["ds"])
    df["y"]  = df["y"].astype(float)
    return df


# ── 2. Train Prophet ───────────────────────────────────────────────────────
def _train_model(df: pd.DataFrame) -> Prophet:
    m = Prophet(
        holidays               = MUMBAI_HOLIDAYS,
        yearly_seasonality     = True,
        weekly_seasonality     = True,
        daily_seasonality      = False,
        seasonality_mode       = "multiplicative",
        changepoint_prior_scale= 0.05,
        holidays_prior_scale   = 10.0,
        interval_width         = 0.90,          # 90% confidence interval
    )
    m.fit(df)
    return m


# ── 3. Build forecast points (historical + future) ─────────────────────────
def _build_forecast_points(
    df: pd.DataFrame,
    forecast: pd.DataFrame,
    horizon: int,
) -> list[ForecastPoint]:
    actual_dates = set(df["ds"].dt.date)
    result = []

    # Include last 90 days of actuals + full forecast
    cutoff = df["ds"].max() - pd.Timedelta(days=90)
    combined = forecast[forecast["ds"] >= cutoff].copy()

    for _, row in combined.iterrows():
        d = row["ds"].date()
        is_actual = d in actual_dates
        # For actuals use the real value for yhat
        if is_actual:
            actual_row = df[df["ds"].dt.date == d]
            yhat = float(actual_row["y"].iloc[0]) if not actual_row.empty else float(row["yhat"])
        else:
            yhat = float(row["yhat"])

        result.append(ForecastPoint(
            date       = str(d),
            yhat       = round(yhat, 2),
            yhat_lower = round(float(row["yhat_lower"]), 2),
            yhat_upper = round(float(row["yhat_upper"]), 2),
            is_actual  = is_actual,
        ))

    return result


# ── 4. Seasonal components ─────────────────────────────────────────────────
def _build_seasonal_components(forecast: pd.DataFrame) -> list[SeasonalComponent]:
    future_only = forecast[forecast["ds"] > forecast["ds"].max() - pd.Timedelta(days=30)]
    result = []
    for _, row in future_only.iterrows():
        result.append(SeasonalComponent(
            date   = str(row["ds"].date()),
            weekly = round(float(row.get("weekly", 0)), 4),
            yearly = round(float(row.get("yearly", 0)), 4),
            trend  = round(float(row.get("trend",  0)), 2),
        ))
    return result


# ── 5. Forecast summary ────────────────────────────────────────────────────
def _build_summary(
    df: pd.DataFrame,
    forecast: pd.DataFrame,
    horizon: int,
) -> ForecastSummary:
    future = forecast[forecast["ds"] > df["ds"].max()]

    next_7  = future.head(7)["yhat"].sum()
    next_30 = future.head(30)["yhat"].sum()
    avg_day = future.head(30)["yhat"].mean()

    # Trend direction — compare first 15 days vs last 15 days of forecast
    first_half = future.head(15)["yhat"].mean()
    last_half  = future.tail(15)["yhat"].mean()
    if last_half > first_half * 1.03:
        trend = "up"
    elif last_half < first_half * 0.97:
        trend = "down"
    else:
        trend = "stable"

    # Strongest / weakest day of week from historical
    df["dow"] = df["ds"].dt.day_name()
    dow_avg = df.groupby("dow")["y"].mean()
    strongest = dow_avg.idxmax()
    weakest   = dow_avg.idxmin()

    return ForecastSummary(
        forecast_horizon_days  = horizon,
        predicted_next_7_days  = round(next_7,  2),
        predicted_next_30_days = round(next_30, 2),
        avg_daily_forecast     = round(avg_day, 2),
        trend_direction        = trend,
        strongest_day          = strongest,
        weakest_day            = weakest,
    )


# ── 6. Holiday effects ─────────────────────────────────────────────────────
def _build_holiday_effects(
    df: pd.DataFrame,
    forecast: pd.DataFrame,
) -> list[HolidayEffect]:
    holiday_cols = [c for c in forecast.columns
                    if c not in ("ds","yhat","yhat_lower","yhat_upper",
                                 "trend","weekly","yearly","multiplicative_terms",
                                 "additive_terms","additive_terms_lower",
                                 "additive_terms_upper","multiplicative_terms_lower",
                                 "multiplicative_terms_upper","trend_lower","trend_upper",
                                 "weekly_lower","weekly_upper","yearly_lower","yearly_upper",
                                 "yhat_lower","yhat_upper")]

    result = []
    for holiday in MUMBAI_HOLIDAYS["holiday"].unique():
        col = holiday
        if col not in forecast.columns:
            continue
        holiday_rows = MUMBAI_HOLIDAYS[MUMBAI_HOLIDAYS["holiday"] == holiday]
        for _, hrow in holiday_rows.iterrows():
            frow = forecast[forecast["ds"] == hrow["ds"]]
            if frow.empty:
                continue
            effect = float(frow[col].iloc[0])
            if abs(effect) < 0.001:
                continue
            result.append(HolidayEffect(
                holiday   = holiday.replace("_", " ").title(),
                date      = str(hrow["ds"].date()),
                effect    = round(effect, 4),
                direction = "boost" if effect > 0 else "dip",
            ))

    return sorted(result, key=lambda x: abs(x.effect), reverse=True)[:10]


# ── 7. Weather correlation ─────────────────────────────────────────────────
def _build_weather_correlation(db: Session) -> list[WeatherCorrelation]:
    rows = db.execute(text("""
        SELECT
            w.condition,
            ROUND(AVG(d.total_revenue)::numeric, 2) AS avg_revenue,
            SUM(d.total_orders)                      AS order_count
        FROM daily_sales_summary d
        JOIN weather_daily w ON d.date = w.date
        GROUP BY w.condition
        ORDER BY avg_revenue DESC
    """)).fetchall()

    return [
        WeatherCorrelation(
            condition   = r[0],
            avg_revenue = float(r[1]),
            order_count = int(r[2]),
        )
        for r in rows
    ]


# ── PUBLIC: full dashboard ─────────────────────────────────────────────────
def get_dashboard(db: Session, horizon: int = 30) -> ForecastDashboard:
    df      = _load_timeseries(db)
    model   = _train_model(df)

    future   = model.make_future_dataframe(periods=horizon)
    forecast = model.predict(future)

    return ForecastDashboard(
        summary             = _build_summary(df, forecast, horizon),
        forecast            = _build_forecast_points(df, forecast, horizon),
        seasonal_components = _build_seasonal_components(forecast),
        holiday_effects     = _build_holiday_effects(df, forecast),
        weather_correlation = _build_weather_correlation(db),
        model_trained_on    = len(df),
    )


# ── Individual endpoints ───────────────────────────────────────────────────
def get_forecast_only(db: Session, horizon: int = 30) -> list[ForecastPoint]:
    df       = _load_timeseries(db)
    model    = _train_model(df)
    future   = model.make_future_dataframe(periods=horizon)
    forecast = model.predict(future)
    return _build_forecast_points(df, forecast, horizon)


def get_weather_correlation(db: Session) -> list[WeatherCorrelation]:
    return _build_weather_correlation(db)