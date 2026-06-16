from uuid import uuid4

from ..database import db
from .user import utcnow


class CaseSnapshot(db.Model):
    __tablename__ = 'case_snapshots'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid4()))
    risk_case_id = db.Column(db.String(36), db.ForeignKey('risk_cases.id'), nullable=False, index=True)
    snapshot_json = db.Column(db.JSON, nullable=False, default=dict)
    encrypted = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    risk_case = db.relationship('RiskCase', back_populates='snapshots')
