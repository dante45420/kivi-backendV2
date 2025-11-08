"""
Modelo: Tips de Kivi el perro
Mensajes que Kivi muestra a los usuarios
"""
from datetime import datetime
from ..db import db


class KiviTip(db.Model):
    __tablename__ = "kivi_tips"

    id = db.Column(db.Integer, primary_key=True)
    
    # Categoría: platform_usage | product_info | promotion | brand_info
    category = db.Column(db.String(50), nullable=False)
    
    # Mensaje que Kivi dirá
    message = db.Column(db.Text, nullable=False)
    
    # Emoji opcional
    emoji = db.Column(db.String(10), nullable=True)
    
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "category": self.category,
            "message": self.message,
            "emoji": self.emoji,
            "active": self.active,
        }

