from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_uuid() -> str:
    return str(uuid4())


def parse_dt(value):
    if not value:
        return None
    if isinstance(value, datetime):
        parsed = value
    else:
        raw = str(value).strip()
        if raw.endswith('Z'):
            raw = raw[:-1] + '+00:00'
        try:
            parsed = datetime.fromisoformat(raw)
        except Exception:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def to_iso(value):
    parsed = parse_dt(value)
    return parsed.isoformat().replace('+00:00', 'Z') if parsed else None


def safe_int(value, default=0):
    try:
        return default if value is None else int(value)
    except Exception:
        return default


def safe_float(value, default=0.0):
    try:
        return default if value is None else float(value)
    except Exception:
        return default
