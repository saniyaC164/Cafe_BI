from pydantic import BaseModel
from typing import List, Optional


class KPISummary(BaseModel):
    total_revenue:      float
    total_orders:       int
    avg_order_value:    float
    gross_profit:       float
    profit_margin_pct:  float


class RevenueByDay(BaseModel):
    date:    str
    revenue: float
    orders:  int


class TopItem(BaseModel):
    name:          str
    category:      str
    total_revenue: float
    total_qty:     int


class ChannelSplit(BaseModel):
    channel:    str
    orders:     int
    revenue:    float
    percentage: float


class HourlyHeatmap(BaseModel):
    hour:       int
    day_of_week: str
    order_count: int


class CustomerStats(BaseModel):
    total_customers:   int
    repeat_customers:  int
    retention_rate_pct: float
    regular_count:     int
    occasional_count:  int
    new_count:         int


class PaymentSplit(BaseModel):
    method:     str
    count:      int
    percentage: float


class KPIDashboard(BaseModel):
    summary:        KPISummary
    revenue_trend:  List[RevenueByDay]
    top_items:      List[TopItem]
    channel_split:  List[ChannelSplit]
    hourly_heatmap: List[HourlyHeatmap]
    customer_stats: CustomerStats
    payment_split:  List[PaymentSplit]