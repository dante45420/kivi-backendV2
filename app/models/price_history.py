"""
Modelo: Historial de precios de compra
Solo para compras, se registra automáticamente al actualizar purchase_price
"""
from datetime import datetime
from ..db import db


class PriceHistory(db.Model):
    __tablename__ = "price_history"

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    purchase_price = db.Column(db.Float, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text, nullable=True)

    # Relación
    product = db.relationship("Product", backref="price_history")

    def to_dict(self):
        return {
            "id": self.id,
            "product_id": self.product_id,
            "purchase_price": self.purchase_price,
            "date": self.date.isoformat() if self.date else None,
            "notes": self.notes,
        }

