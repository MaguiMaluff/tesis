import os
from flask import Flask, request
from dotenv import load_dotenv

from .config import load_config
from .signature import verify_x_hub_signature_256
from .normalize import normalize_instagram_event
from .supabase_db import (
    make_supabase,
    get_ig_account_by_ig_user_id,
    get_or_create_conversation,
    mark_conversation_pending,
    insert_message_event,
)

load_dotenv()

app = Flask(__name__)

CFG = load_config()
SB = make_supabase(CFG.supabase_url, CFG.supabase_service_role_key)


@app.get("/webhook")
def webhook_verify():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == CFG.verify_token and challenge:
        return challenge, 200
    return "Verification failed", 403


@app.post("/webhook")
def webhook_receive():
    raw_body = request.get_data()
    sig = request.headers.get("X-Hub-Signature-256")

    if not verify_x_hub_signature_256(CFG.meta_app_secret, raw_body, sig):
        return "Invalid signature", 403

    payload = request.get_json(silent=True) or {}

    if payload.get("object") != "instagram":
        return "OK", 200

    for entry in payload.get("entry", []):
        entry_id = str(entry.get("id", "")).strip()
        if not entry_id:
            continue

        # Route this webhook entry.id to our DB ig_account
        ig_account = get_ig_account_by_ig_user_id(SB, entry_id)
        if not ig_account:
            # Unknown or disabled account => ignore safely
            continue

        ig_account_id = ig_account["id"]

        for evt in entry.get("messaging", []):
            if "message_edit" in evt:
                continue

            # Keep using entry_id (external ig_user_id) to compute direction/outbound
            cm = normalize_instagram_event(entry_id, evt)
            if cm is None:
                continue

            # Ensure conversation exists for (ig_account_id, peer_id)
            conv = get_or_create_conversation(SB, ig_account_id, cm.peer_id, cm.sent_at)

            inserted = insert_message_event(
                SB,
                conversation_id=conv["id"],
                mid=cm.mid,
                sent_at_iso=cm.sent_at,
                direction=cm.direction,
                text_hash=cm.text_hash,
                features=cm.features,
            )

            if inserted:
                mark_conversation_pending(SB, conv["id"], cm.sent_at)
                print(f"[message] ig_account_id={ig_account_id} mid={cm.mid} peer_id={cm.peer_id} direction={cm.direction}")
            else:
                print(f"[duplicate] ig_account_id={ig_account_id} mid={cm.mid}")

    return "OK", 200


@app.get("/")
def health():
    return "up", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=CFG.port, debug=True)