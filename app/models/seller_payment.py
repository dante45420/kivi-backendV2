"""
Modelo: Pago a Vendedor
Registro de pagos a vendedores (similar a Payment pero para vendedores)
"""
from datetime import datetime
from ..db import db


class SellerPayment(db.Model):
    __tablename__ = "seller_payments"

    id = db.Column(db.Integer, primary_key=True)
    seller_id = db.Column(db.Integer, db.ForeignKey("sellers.id"), nullable=False)
    
    # Monto total del pago (redondeado al peso)
    amount = db.Column(db.Integer, nullable=False)
    
    # Método de pago (transferencia, efectivo, etc)
    method = db.Column(db.String(32), nullable=True)
    
    # Referencia (número de transferencia, etc)
    reference = db.Column(db.String(120), nullable=True)
    
    notes = db.Column(db.Text, nullable=True)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relación
    seller = db.relationship("Seller", backref="payments")

    def to_dict(self):
        return {
            "id": self.id,
            "seller_id": self.seller_id,
            "seller": self.seller.to_dict() if self.seller else None,
            "amount": self.amount,
            "method": self.method,
            "reference": self.reference,
            "notes": self.notes,
            "date": self.date.isoformat() if self.date else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
