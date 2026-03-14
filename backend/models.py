from sqlalchemy import Boolean, Column, Float, Integer, String, DateTime, Text
from database import Base
import datetime

class Trade(Base):
    __tablename__ = "trades"

    id             = Column(Integer, primary_key=True, index=True)
    symbol         = Column(String, index=True)
    side           = Column(String)
    entry_price    = Column(Float)
    exit_price     = Column(Float, nullable=True)
    quantity       = Column(Float)
    stop_loss      = Column(Float, nullable=True)
    take_profit    = Column(Float, nullable=True)
    pnl            = Column(Float, nullable=True)
    status         = Column(String, default="OPEN")
    entry_time     = Column(DateTime, default=datetime.datetime.utcnow)
    exit_time      = Column(DateTime, nullable=True)
    reason         = Column(String, nullable=True)
    signals_json   = Column(Text, nullable=True)
    ml_confidence  = Column(Float, nullable=True)
    ml_direction   = Column(String, nullable=True)
    
    # Trailing Stop Loss fields
    highest_price      = Column(Float, nullable=True)
    is_trailing_active = Column(Boolean, default=False)


class Portfolio(Base):
    __tablename__ = "portfolio"

    id         = Column(Integer, primary_key=True, index=True)
    balance    = Column(Float, default=10000.0)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow)


class EventRecord(Base):
    __tablename__ = "events"

    id         = Column(Integer, primary_key=True, index=True)
    timestamp  = Column(DateTime, default=datetime.datetime.utcnow)
    event_type = Column(String)
    severity   = Column(String)
    symbol     = Column(String, nullable=True)
    title      = Column(String)
    detail     = Column(Text, nullable=True)
