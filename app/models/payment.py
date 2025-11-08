"""
Modelo: Pago
Registro de pagos de clientes
"""
from datetime import datetime
from ..db import db


class Payment(db.Model):
    __tablename__ = "payments"

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id"), nullable=False)
    
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
    customer = db.relationship("Customer", backref="payments")

    def to_dict(self):
        return {
            "id": self.id,
            "customer_id": self.customer_id,
            "customer": self.customer.to_dict() if self.customer else None,
            "amount": self.amount,
            "method": self.method,
            "reference": self.reference,
            "notes": self.notes,
            "date": self.date.isoformat() if self.date else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

