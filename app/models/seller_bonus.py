"""
Modelo: Bono Semanal de Vendedor
Registro de bonos asignados a vendedores por semana
"""
from datetime import datetime, date
from ..db import db


class SellerBonus(db.Model):
    __tablename__ = "seller_bonuses"

    id = db.Column(db.Integer, primary_key=True)
    seller_id = db.Column(db.Integer, db.ForeignKey("sellers.id"), nullable=False)
    
    # Semana del bono (lunes de la semana)
    week_start = db.Column(db.Date, nullable=False)
    
    # Meta de pedidos para esa semana
    orders_target = db.Column(db.Integer, nullable=False)
    
    # Pedidos alcanzados en esa semana
    orders_achieved = db.Column(db.Integer, nullable=False)
    
    # Porcentaje de comisión aplicado (puede ser mayor al porcentaje base)
    commission_percent = db.Column(db.Float, nullable=False)
    
    # Monto total del bono calculado
    bonus_amount = db.Column(db.Integer, nullable=False)
    
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relación
    seller = db.relationship("Seller", backref="bonuses")

    def to_dict(self):
        return {
            "id": self.id,
            "seller_id": self.seller_id,
            "seller": self.seller.to_dict() if self.seller else None,
            "week_start": self.week_start.isoformat() if self.week_start else None,
            "orders_target": self.orders_target,
            "orders_achieved": self.orders_achieved,
            "commission_percent": self.commission_percent,
            "bonus_amount": self.bonus_amount,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
