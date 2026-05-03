import pandas as pd
from prophet import Prophet
from sqlalchemy import create_engine
import numpy as np

from BACKEND.database import DATABASE_URL  # for metrics

engine = create_engine(DATABASE_URL)  
df = pd.read_sql("SELECT date, totalrevenue AS y FROM dailysalessummary ORDER BY date", engine)

train = df.iloc[:-30]  # ~336 days train
test = df.iloc[-30:]   # 30-day test

m = Prophet(yearly_seasonality=True, weekly_seasonality=True, daily_seasonality=False)
m.fit(train)
future = m.make_future_dataframe(periods=30)
forecast = m.predict(future)
test_pred = forecast['yhat'].tail(30).values  # align to test

mae = np.mean(np.abs(test['y'] - test_pred))
mape = np.mean(np.abs((test['y'] - test_pred) / test['y'])) * 100
rmse = np.sqrt(np.mean((test['y'] - test_pred)**2))

print(f'MAE: ₹{mae:.0f}, MAPE: {mape:.1f}%, RMSE: ₹{rmse:.0f}')