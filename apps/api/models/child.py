from uuid import uuid4

from ..database import db
from .user import utcnow


class Child(db.Model):
    __tablename__ = 'children'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid4()))
    parent_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False, index=True)
    display_name = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    parent = db.relationship('User', back_populates='children')
    ig_accounts = db.relationship('IgAccount', back_populates='child', cascade='all, delete-orphan')
