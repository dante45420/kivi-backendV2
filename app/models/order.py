"""
Modelo: Pedido
Contenedor de items de múltiples clientes
"""
from datetime import datetime
from ..db import db


class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.String(20), nullable=False, default="draft")
    # draft | emitted | completed | cancelled
    
    source = db.Column(db.String(20), nullable=False, default="manual")
    # manual | whatsapp | web
    
    shipping_type = db.Column(db.String(20), nullable=False, default="fast")
    # fast (más rápido) | cheap (más barato)
    
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    emitted_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "status": self.status,
            "source": self.source,
            "shipping_type": self.shipping_type,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "emitted_at": self.emitted_at.isoformat() if self.emitted_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }

