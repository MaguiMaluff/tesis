from uuid import uuid4

from ..database import db
from .user import utcnow


class RiskCase(db.Model):
    __tablename__ = 'risk_cases'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid4()))
    conversation_id = db.Column(db.String(36), db.ForeignKey('conversations.id'), nullable=False, index=True)
    opened_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    status = db.Column(db.String(32), nullable=False, default='open')
    stage = db.Column(db.Integer, nullable=False, default=0)
    confidence = db.Column(db.Float, nullable=False, default=0.0)
    reason_safe = db.Column(db.Text, nullable=True)
    evidence_window_start = db.Column(db.DateTime(timezone=True), nullable=True)
    evidence_window_end = db.Column(db.DateTime(timezone=True), nullable=True)

    conversation = db.relationship('Conversation', back_populates='risk_cases')
    snapshots = db.relationship('CaseSnapshot', back_populates='risk_case', cascade='all, delete-orphan')
