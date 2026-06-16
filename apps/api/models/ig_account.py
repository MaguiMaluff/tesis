from uuid import uuid4

from ..database import db
from .user import utcnow


class IgAccount(db.Model):
    __tablename__ = 'ig_accounts'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid4()))
    child_id = db.Column(db.String(36), db.ForeignKey('children.id'), nullable=False, index=True)
    ig_user_id = db.Column(db.String(128), unique=True, nullable=False, index=True)
    ig_username = db.Column(db.String(255), nullable=False)
    access_token = db.Column(db.String(255), nullable=False)
    token_expires_at = db.Column(db.DateTime(timezone=True), nullable=True)
    webhook_enabled = db.Column(db.Boolean, nullable=False, default=True)
    status = db.Column(db.String(32), nullable=False, default='active')
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    child = db.relationship('Child', back_populates='ig_accounts')
    conversations = db.relationship('Conversation', back_populates='ig_account', cascade='all, delete-orphan')
