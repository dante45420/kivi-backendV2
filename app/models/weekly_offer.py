"""
Modelo: Oferta semanal
Productos destacados con precios especiales
"""
from datetime import datetime
from ..db import db


class WeeklyOffer(db.Model):
    __tablename__ = "weekly_offers"

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    
    # Precio especial para la oferta
    special_price = db.Column(db.Integer, nullable=False)
    
    # Vigencia
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    
    # Estado
    active = db.Column(db.Boolean, default=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relación
    product = db.relationship("Product", backref="weekly_offers")

    def to_dict(self):
        return {
            "id": self.id,
            "product_id": self.product_id,
            "product": self.product.to_dict() if self.product else None,
            "special_price": self.special_price,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "active": self.active,
        }

