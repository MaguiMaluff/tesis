from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import re


# Collapse multiple whitespace into a single space (stable normalization)
_ws_re = re.compile(r"\s+")

# Loose phone-like pattern (digits with optional separators; requires a minimum length)
_phone_re = re.compile(r"(\+?\d[\d\s().-]{6,}\d)")

# URL pattern (only http/https)
_url_re = re.compile(r"(https?://\S+)", re.IGNORECASE)

# Email pattern
_email_re = re.compile(r"([A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,})", re.IGNORECASE)

# WhatsApp mentions (simple keyword scan)
_wa_re = re.compile(r"\b(whatsapp|wpp|wa)\b", re.IGNORECASE)


def _ts_ms_to_iso(ts_ms: int | None) -> str:
    """
    Convert Instagram webhook millisecond timestamps to ISO-8601 UTC.

    If missing, fallback to "now"
    """
    if not ts_ms:
        return datetime.now(timezone.utc).isoformat()
    return datetime.fromtimestamp(ts_ms / 1000.0, tz=timezone.utc).isoformat()


def normalize_text(text: str) -> str:
    """
    Normalize text for stable hashing/feature extraction:
      - strip edges
      - lowercase
      - collapse repeated whitespace
    """
    t = (text or "").strip().lower()
    t = _ws_re.sub(" ", t)
    return t


def sha256_hex(s: str) -> str:
    """
    Hash a string using SHA-256 and return hex digest.
    Used to avoid storing raw text while keeping a stable fingerprint.
    """
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class CanonicalMessage:
    """
    Canonical / internal representation of a message event.

    This is what the webhook receiver uses to:
      - insert into message_events (mid, sent_at, direction, text_hash, features)
      - update conversations pending_count/pending_since
    """
    source: str
    ig_user_id: str
    peer_id: str
    mid: str
    direction: str  # 'inbound' | 'outbound'
    sent_at: str    # ISO-8601 UTC string
    text_hash: str | None
    features: dict


def extract_features(raw_text: str | None) -> dict:
    """
    Extract privacy-friendly features from message text.
    No raw text is stored in DB; only derived booleans/counters.
    """
    t = raw_text or ""
    norm = normalize_text(t)

    return {
        "len_chars": len(t),
        "len_words": (len(norm.split(" ")) if norm else 0),
        "has_phone": bool(_phone_re.search(t)),
        "has_url": bool(_url_re.search(t)),
        "has_email": bool(_email_re.search(t)),
        "mentions_whatsapp": bool(_wa_re.search(t)),
    }


def normalize_instagram_event(ig_user_id: str, evt: dict) -> CanonicalMessage | None:
    """
    Convert one Instagram webhook 'messaging' event into a CanonicalMessage.

    Returns None when:
      - event is not a message
      - required IDs or mid are missing

    Echo events are kept as outbound messages because Instagram commonly uses
    them to notify messages sent by the monitored account.
    """
    sender_id = (evt.get("sender") or {}).get("id")
    recipient_id = (evt.get("recipient") or {}).get("id")
    ts_ms = evt.get("timestamp")

    msg = evt.get("message")
    if not isinstance(msg, dict):
        return None

    mid = msg.get("mid")
    if not mid:
        return None

    # Instagram may use "text" or sometimes "message"
    text = msg.get("text") or msg.get("message") or ""

    sent_at = _ts_ms_to_iso(ts_ms)

    # Determine direction and peer_id:
    # - outbound: sender is our ig_user_id, or an echo event reflects our sent message
    # - inbound: sender is the other user
    if bool(msg.get("is_echo")) or str(sender_id) == str(ig_user_id):
        if not recipient_id:
            return None
        direction = "outbound"
        peer_id = str(recipient_id)
    else:
        if not sender_id:
            return None
        direction = "inbound"
        peer_id = str(sender_id)

    # Privacy-friendly fingerprinting + features
    norm = normalize_text(text)
    text_hash = sha256_hex(norm) if norm else None
    features = extract_features(text)

    return CanonicalMessage(
        source="instagram",
        ig_user_id=str(ig_user_id),
        peer_id=str(peer_id),
        mid=str(mid),
        direction=direction,
        sent_at=sent_at,
        text_hash=text_hash,
        features=features,
    )
