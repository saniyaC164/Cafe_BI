from pydantic import BaseModel
from typing import List, Optional


class ForecastPoint(BaseModel):
    date:        str
    yhat:        float          # predicted value
    yhat_lower:  float          # lower confidence bound
    yhat_upper:  float          # upper confidence bound
    is_actual:   bool           # True = historical, False = future forecast


class SeasonalComponent(BaseModel):
    date:   str
    weekly: float               # day-of-week seasonal effect
    yearly: float               # time-of-year seasonal effect
    trend:  float               # long-term trend component


class ForecastSummary(BaseModel):
    forecast_horizon_days:  int
    predicted_next_7_days:  float
    predicted_next_30_days: float
    avg_daily_forecast:     float
    trend_direction:        str     # "up" | "down" | "stable"
    strongest_day:          str     # day of week with highest predicted sales
    weakest_day:            str


class HolidayEffect(BaseModel):
    holiday:    str
    date:       str
    effect:     float           # estimated revenue impact vs baseline
    direction:  str             # "boost" | "dip"


class WeatherCorrelation(BaseModel):
    condition:      str         # sunny | rainy | cloudy
    avg_revenue:    float
    order_count:    int


class ForecastDashboard(BaseModel):
    summary:              ForecastSummary
    forecast:             List[ForecastPoint]
    seasonal_components:  List[SeasonalComponent]
    holiday_effects:      List[HolidayEffect]
    weather_correlation:  List[WeatherCorrelation]
    model_trained_on:     int           # number of days used to train