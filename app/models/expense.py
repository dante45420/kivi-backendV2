"""
Modelo: Gasto
Gastos adicionales asociados a un pedido (envío, bolsas, etc)
"""
from datetime import datetime
from ..db import db


class Expense(db.Model):
    __tablename__ = "expenses"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    
    # Categoría de gasto (envío, bolsas, comisión, otros)
    category = db.Column(db.String(50), nullable=False)
    
    # Monto (redondeado al peso)
    amount = db.Column(db.Integer, nullable=False)
    
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relación
    order = db.relationship("Order", backref="expenses")

    def to_dict(self):
        return {
            "id": self.id,
            "order_id": self.order_id,
            "category": self.category,
            "amount": self.amount,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

