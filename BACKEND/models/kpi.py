from sqlalchemy import Column, Integer, Float, String, DateTime, Boolean, Date
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Order(Base):
    __tablename__ = "orders"

    order_id       = Column(Integer, primary_key=True, index=True)
    timestamp      = Column(DateTime)
    customer_id    = Column(Integer)
    total_amount   = Column(Float)
    payment_method = Column(String)
    channel        = Column(String)


class OrderItem(Base):
    __tablename__ = "order_items"

    line_id          = Column(Integer, primary_key=True, index=True)
    order_id         = Column(Integer, index=True)
    item_id          = Column(Integer, index=True)
    quantity         = Column(Integer)
    unit_price       = Column(Float)
    discount_applied = Column(Float)


class MenuItem(Base):
    __tablename__ = "menu_items"

    item_id     = Column(Integer, primary_key=True, index=True)
    name        = Column(String)
    category    = Column(String)
    price       = Column(Float)
    cost_price  = Column(Float)
    is_seasonal = Column(Boolean)
    is_active   = Column(Boolean)


class Customer(Base):
    __tablename__ = "customers"

    customer_id     = Column(Integer, primary_key=True, index=True)
    name            = Column(String)
    segment         = Column(String)
    loyalty_points  = Column(Integer)
    first_visit     = Column(Date)
    last_visit      = Column(Date)