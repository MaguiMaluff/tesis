from uuid import uuid4

from ..database import db
from .user import utcnow


class MessageEvent(db.Model):
    __tablename__ = 'message_events'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid4()))
    conversation_id = db.Column(db.String(36), db.ForeignKey('conversations.id'), nullable=False, index=True)
    mid = db.Column(db.String(255), unique=True, nullable=False, index=True)
    sent_at = db.Column(db.DateTime(timezone=True), nullable=False, index=True)
    direction = db.Column(db.String(16), nullable=False)
    text_hash = db.Column(db.String(255), nullable=True)
    features = db.Column(db.JSON, nullable=False, default=dict)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    conversation = db.relationship('Conversation', back_populates='message_events')
