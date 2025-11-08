"""
Modelo: Asignación de pago
Relaciona pagos con items de pedido específicos
"""
from datetime import datetime
from ..db import db


class PaymentAllocation(db.Model):
    __tablename__ = "payment_allocations"

    id = db.Column(db.Integer, primary_key=True)
    payment_id = db.Column(db.Integer, db.ForeignKey("payments.id"), nullable=False)
    order_item_id = db.Column(db.Integer, db.ForeignKey("order_items.id"), nullable=False)
    
    # Monto asignado (puede ser parcial)
    amount = db.Column(db.Integer, nullable=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relaciones
    payment = db.relationship("Payment", backref="allocations")
    order_item = db.relationship("OrderItem", backref="payment_allocations")

    def to_dict(self):
        return {
            "id": self.id,
            "payment_id": self.payment_id,
            "order_item_id": self.order_item_id,
            "amount": self.amount,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

