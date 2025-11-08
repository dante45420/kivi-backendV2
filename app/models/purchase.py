"""
Modelo: Compra/Purchase
Registro de compras de productos con conversiones
"""
from datetime import datetime
from ..db import db


class Purchase(db.Model):
    __tablename__ = "purchases"

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    
    # Cantidad comprada
    qty = db.Column(db.Float, nullable=False)
    unit = db.Column(db.String(16), nullable=False, default="kg")
    
    # Precios
    price_total = db.Column(db.Float, nullable=False)
    price_per_unit = db.Column(db.Float, nullable=False)
    
    # Conversión (opcional, cuando se compra en unidad diferente)
    conversion_qty = db.Column(db.Float, nullable=True)
    conversion_unit = db.Column(db.String(16), nullable=True)
    
    # Notas
    notes = db.Column(db.Text, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relación
    product = db.relationship("Product", backref="purchases")

    def to_dict(self):
        return {
            "id": self.id,
            "product_id": self.product_id,
            "product": self.product.to_dict() if self.product else None,
            "qty": self.qty,
            "unit": self.unit,
            "price_total": self.price_total,
            "price_per_unit": self.price_per_unit,
            "conversion_qty": self.conversion_qty,
            "conversion_unit": self.conversion_unit,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

