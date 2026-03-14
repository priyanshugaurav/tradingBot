"""
Event Log — Centralized event bus for the trading bot.
Records every action, signal, trade, and error to both memory and SQLite.
"""
import datetime
import threading
import queue as queue_module
import logging
import os
from typing import Optional, List, Dict, Any
from enum import Enum
from database import SessionLocal

# Setup file logging for hiring task
LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

logging.basicConfig(
    filename=os.path.join(LOG_DIR, "tradebot.log"),
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("TradeBot")


class EventType(str, Enum):
    SYSTEM     = "SYSTEM"
    SCANNER    = "SCANNER"
    SIGNAL     = "SIGNAL"
    PATTERN    = "PATTERN"
    PREDICTION = "PREDICTION"
    TRADE      = "TRADE"
    RISK       = "RISK"
    LEARNING   = "LEARNING"
    ERROR      = "ERROR"


class EventSeverity(str, Enum):
    INFO    = "INFO"
    SUCCESS = "SUCCESS"
    WARNING = "WARNING"
    DANGER  = "DANGER"


# In-memory ring buffer for WebSocket streaming (keeps last 500 events)
_lock = threading.Lock()
_subscribers: List[Any] = []   # Queue objects
_buffer: List[Dict] = []
_BUFFER_MAX = 500


def _broadcast(event: Dict):
    for q in list(_subscribers):
        try:
            q.put_nowait(event)
        except Exception:
            pass


def subscribe(q: queue_module.SimpleQueue):
    with _lock:
        _subscribers.append(q)


def unsubscribe(q: queue_module.SimpleQueue):
    with _lock:
        if q in _subscribers:
            _subscribers.remove(q)


def log(
    title: str,
    event_type: EventType = EventType.SYSTEM,
    severity: EventSeverity = EventSeverity.INFO,
    symbol: Optional[str] = None,
    detail: Optional[str] = None,
) -> Dict:
    now = datetime.datetime.utcnow()
    entry = {
        "id":         None,
        "timestamp":  now.isoformat() + "Z",
        "event_type": event_type.value,
        "severity":   severity.value,
        "symbol":     symbol,
        "title":      title,
        "detail":     detail,
    }
    # Persist to DB (import here to avoid circular import at module load)
    try:
        from models import EventRecord
        db = SessionLocal()
        record = EventRecord(
            timestamp  = now,
            event_type = event_type.value,
            severity   = severity.value,
            symbol     = symbol,
            title      = title,
            detail     = detail,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        entry["id"] = record.id
        db.close()
    except Exception as e:
        print(f"[EventLog] DB error: {e}")

    # Write to file
    log_msg = f"[{event_type.value}] {title} | {detail if detail else ''}"
    if severity == EventSeverity.DANGER or event_type == EventType.ERROR:
        logger.error(log_msg)
    else:
        logger.info(log_msg)

    with _lock:
        _buffer.append(entry)
        if len(_buffer) > _BUFFER_MAX:
            _buffer.pop(0)

    _broadcast(entry)
    return entry


def get_recent(limit: int = 200) -> List[Dict]:
    with _lock:
        return list(reversed(_buffer[-limit:]))
