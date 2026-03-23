from pydantic import BaseModel
from typing import List, Optional


class StockStatus(BaseModel):
    ingredient_id:   int
    name:            str
    unit:            str
    current_stock:   float
    reorder_level:   float
    supplier:        str
    last_restocked:  str
    status:          str    # "ok" | "low" | "critical"
    days_until_empty: Optional[float]   # estimated based on depletion rate


class DepletionRate(BaseModel):
    ingredient_id: int
    name:          str
    unit:          str
    avg_daily_usage: float   # average units consumed per day
    current_stock:   float
    days_remaining:  Optional[float]


class WastageEntry(BaseModel):
    date:            str
    ingredient_name: str
    quantity_wasted: float
    unit:            str
    note:            str


class WastageSummary(BaseModel):
    date:          str
    total_wastage_events: int
    ingredients_wasted:   int


class ReorderSuggestion(BaseModel):
    ingredient_id:     int
    name:              str
    unit:              str
    current_stock:     float
    reorder_level:     float
    suggested_order:   float
    supplier:          str
    urgency:           str   # "critical" | "low" | "scheduled"


class WastageByDay(BaseModel):
    day_of_week:    str
    total_wastage:  float
    event_count:    int


class InventoryDashboard(BaseModel):
    stock_status:        List[StockStatus]
    depletion_rates:     List[DepletionRate]
    reorder_suggestions: List[ReorderSuggestion]
    wastage_trend:       List[WastageSummary]
    wastage_by_weekday:  List[WastageByDay]
    alert_count:         int    # total items needing attention