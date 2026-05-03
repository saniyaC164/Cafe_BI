# evaluate_forecast.py
import pandas as pd
import numpy as np
from prophet import Prophet
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

load_dotenv()
engine = create_engine(os.getenv("DATABASE_URL"))

# Load full time series
rows = engine.connect().execute(text(
    "SELECT date, total_revenue FROM daily_sales_summary ORDER BY date"
)).fetchall()

df = pd.DataFrame(rows, columns=["ds", "y"])
df["ds"] = pd.to_datetime(df["ds"])
df["y"]  = df["y"].astype(float)

# Train/test split — last 30 days as holdout
train = df[:-30]
test  = df[-30:]

# Build holidays
holidays = pd.DataFrame({
    "holiday": ["diwali","diwali_eve","christmas","new_year_eve",
                "republic_day","independence_day","dussehra"],
    "ds": pd.to_datetime(["2024-11-01","2024-10-31","2024-12-25",
                           "2024-12-31","2024-01-26","2024-08-15","2024-10-12"]),
    "lower_window": [0, 0, 0, 0, 0, 0, 0],
    "upper_window": [1, 1, 1, 1, 0, 0, 1],
})

# Train model
m = Prophet(
    holidays=holidays,
    yearly_seasonality=True,
    weekly_seasonality=True,
    seasonality_mode="multiplicative",
    changepoint_prior_scale=0.05,
    interval_width=0.90,
)
m.fit(train)

# Forecast over test period
future   = m.make_future_dataframe(periods=30)
forecast = m.predict(future)
forecast_test = forecast[forecast["ds"].isin(test["ds"])].copy()
forecast_test = forecast_test.reset_index(drop=True)
test = test.reset_index(drop=True)

actual    = test["y"].values
predicted = forecast_test["yhat"].values
lower     = forecast_test["yhat_lower"].values
upper     = forecast_test["yhat_upper"].values

# Calculate metrics
mae  = np.mean(np.abs(actual - predicted))
mape = np.mean(np.abs((actual - predicted) / actual)) * 100
rmse = np.sqrt(np.mean((actual - predicted) ** 2))

# CI coverage — what % of actuals fall within the 90% band
coverage = np.mean((actual >= lower) & (actual <= upper)) * 100

print(f"\n===== PROPHET EVALUATION METRICS =====")
print(f"MAE:              {mae:.2f}")
print(f"MAPE:             {mape:.2f}%")
print(f"RMSE:             {rmse:.2f}")
print(f"CI Coverage (90%): {coverage:.1f}%")
print(f"Test period:      {test['ds'].min().date()} to {test['ds'].max().date()}")
print(f"Training rows:    {len(train)}")
print(f"Test rows:        {len(test)}")