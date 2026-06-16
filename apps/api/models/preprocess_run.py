from uuid import uuid4

from ..database import db
from .user import utcnow


class PreprocessRun(db.Model):
    __tablename__ = 'preprocess_runs'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid4()))
    conversation_id = db.Column(db.String(36), db.ForeignKey('conversations.id'), nullable=False, index=True)
    window_start = db.Column(db.DateTime(timezone=True), nullable=False)
    window_end = db.Column(db.DateTime(timezone=True), nullable=False)
    trigger = db.Column(db.String(32), nullable=False)
    status = db.Column(db.String(32), nullable=False, default='queued', index=True)
    message_count = db.Column(db.Integer, nullable=False, default=0)
    fetch_plan = db.Column(db.JSON, nullable=False, default=dict)
    error = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, index=True)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    conversation = db.relationship('Conversation')