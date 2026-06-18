from __future__ import annotations

from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_migrate import Migrate
from dotenv import load_dotenv

from .config import load_config
from .database import db
from .models import Conversation, IgAccount, MessageEvent
from .normalize import normalize_instagram_event
from .routes.auth import auth_bp
from .routes.children import children_bp
from .routes.conversations import conversations_bp
from .routes.dashboard import dashboard_bp
from .routes.risk_cases import risk_bp
from .routes.stats import stats_bp
from .service_modules.utils import parse_dt, utcnow
from .signature import verify_x_hub_signature_256

load_dotenv()

app = Flask(__name__)
CORS(app)

CFG = load_config()
app.config["SQLALCHEMY_DATABASE_URI"] = CFG.database_uri
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"connect_args": {"check_same_thread": False}}
app.config["SECRET_KEY"] = CFG.secret_key
app.config["JWT_EXPIRATION_HOURS"] = CFG.jwt_expiration_hours


db.init_app(app)
Migrate(app, db)

app.register_blueprint(auth_bp, url_prefix="/auth")
app.register_blueprint(children_bp)
app.register_blueprint(conversations_bp)
app.register_blueprint(risk_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(stats_bp, url_prefix="/stats")


def _get_or_create_conversation(account: IgAccount, peer_id: str, sent_at: str | None) -> Conversation:
    conversation = Conversation.query.filter_by(ig_account_id=account.id, peer_id=peer_id).first()
    if conversation:
        return conversation

    timestamp = parse_dt(sent_at) or utcnow()
    conversation = Conversation(
        ig_account_id=account.id,
        peer_id=peer_id,
        conversation_ext_id=None,
        created_at=timestamp,
        last_message_at=timestamp,
        last_preprocessed_at=None,
        pending_count=0,
        pending_since=timestamp,
        rolling_summary={
            "current_stage_max": 0,
            "trend": "stable",
            "key_points_safe": [],
            "signals_observed": [],
        },
        status="active",
    )
    db.session.add(conversation)
    db.session.flush()
    return conversation


def _store_message(conversation: Conversation, cm) -> bool:
    if MessageEvent.query.filter_by(mid=cm.mid).first():
        return False

    sent_at = parse_dt(cm.sent_at) or utcnow()
    db.session.add(
        MessageEvent(
            conversation_id=conversation.id,
            mid=cm.mid,
            sent_at=sent_at,
            direction=cm.direction,
            text_hash=cm.text_hash,
            features=cm.features or {},
            created_at=utcnow(),
        )
    )
    conversation.last_message_at = sent_at
    conversation.pending_count = (conversation.pending_count or 0) + 1
    conversation.pending_since = conversation.pending_since or sent_at
    return True


with app.app_context():
    db.create_all()


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
        try:
            entry_id = str(entry.get("id", "")).strip()
            if not entry_id:
                continue

            ig_account = IgAccount.query.filter_by(ig_user_id=entry_id).first()
            if not ig_account:
                continue

            for evt in entry.get("messaging", []):
                if "message_edit" in evt:
                    continue

                cm = normalize_instagram_event(entry_id, evt)
                if cm is None:
                    continue

                conversation = _get_or_create_conversation(ig_account, cm.peer_id, cm.sent_at)
                if _store_message(conversation, cm):
                    db.session.commit()
                else:
                    db.session.rollback()
        except Exception as error:
            db.session.rollback()
            print(f"[webhook] error: {error}")
            continue

    return "OK", 200


@app.get("/")
def health():
    return "up", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=CFG.port, debug=True, use_reloader=False)
