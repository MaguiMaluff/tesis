from uuid import uuid4

from ..database import db
from .user import utcnow


class Conversation(db.Model):
    __tablename__ = 'conversations'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid4()))
    ig_account_id = db.Column(db.String(36), db.ForeignKey('ig_accounts.id'), nullable=False, index=True)
    peer_id = db.Column(db.String(128), nullable=False, index=True)
    conversation_ext_id = db.Column(db.String(255), unique=True, nullable=True, index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    last_message_at = db.Column(db.DateTime(timezone=True), nullable=True)
    last_preprocessed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    pending_count = db.Column(db.Integer, nullable=False, default=0)
    pending_since = db.Column(db.DateTime(timezone=True), nullable=True)
    processing_lock_until = db.Column(db.DateTime(timezone=True), nullable=True)
    processing_lock_by = db.Column(db.String(128), nullable=True)
    rolling_summary = db.Column(db.JSON, nullable=False, default=dict)
    status = db.Column(db.String(32), nullable=False, default='active')

    ig_account = db.relationship('IgAccount', back_populates='conversations')
    message_events = db.relationship('MessageEvent', back_populates='conversation', cascade='all, delete-orphan')
    risk_cases = db.relationship('RiskCase', back_populates='conversation', cascade='all, delete-orphan')
