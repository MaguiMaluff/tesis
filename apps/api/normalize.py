from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import re

_ws_re = re.compile(r"\s+")
_phone_re = re.compile(r"(\+?\d[\d\s().-]{6,}\d)")
_url_re = re.compile(r"(https?://\S+)", re.IGNORECASE)
_email_re = re.compile(r"([A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,})", re.IGNORECASE)
_wa_re = re.compile(r"\b(whatsapp|wpp|wa)\b", re.IGNORECASE)

def _ts_ms_to_iso(ts_ms: int | None) -> str:
    if not ts_ms:
        # fallback now
        return datetime.now(timezone.utc).isoformat()
    return datetime.fromtimestamp(ts_ms / 1000.0, tz=timezone.utc).isoformat()

def normalize_text(text: str) -> str:
    t = (text or "").strip().lower()
    t = _ws_re.sub(" ", t)
    return t

def sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

@dataclass(frozen=True)
class CanonicalMessage:
    source: str
    ig_user_id: str
    peer_id: str
    mid: str
    direction: str  # inbound|outbound
    sent_at: str    # ISO-8601 UTC
    text_hash: str | None
    features: dict

def extract_features(raw_text: str | None) -> dict:
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
    Handles only 'message' events; caller should ignore message_edit elsewhere.
    """
    sender_id = (evt.get("sender") or {}).get("id")
    recipient_id = (evt.get("recipient") or {}).get("id")
    ts_ms = evt.get("timestamp")

    msg = evt.get("message")
    if not isinstance(msg, dict):
        return None

    # ignore echos
    if bool(msg.get("is_echo")):
        return None

    mid = msg.get("mid")
    if not mid:
        return None

    text = msg.get("text") or msg.get("message") or ""
    sent_at = _ts_ms_to_iso(ts_ms)

    # Determine direction and peer_id
    if str(sender_id) == str(ig_user_id):
        direction = "outbound"
        peer_id = str(recipient_id)
    else:
        direction = "inbound"
        peer_id = str(sender_id)

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