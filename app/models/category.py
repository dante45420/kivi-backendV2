"""
Modelo: Categoría de producto
Tabla simple con categorías predefinidas
"""
from datetime import datetime
from ..db import db


class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    emoji = db.Column(db.String(10), nullable=True)
    order = db.Column(db.Integer, default=0)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "emoji": self.emoji,
            "order": self.order,
            "active": self.active,
        }

