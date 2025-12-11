"""
Modelo: Costo Semanal
Costos adicionales organizados por semana y categoría
"""
from datetime import datetime
from ..db import db


class WeeklyCost(db.Model):
    __tablename__ = "weekly_costs"

    id = db.Column(db.Integer, primary_key=True)
    
    # Semana (fecha de inicio - lunes)
    week_start = db.Column(db.Date, nullable=False, index=True)
    
    # Categoría de costo
    category = db.Column(db.String(50), nullable=False, index=True)
    
    # Monto total (redondeado al peso)
    amount = db.Column(db.Integer, nullable=False)
    
    # Cantidad de veces que se sumó este costo
    count = db.Column(db.Integer, default=1, nullable=False)
    
    # Descripción opcional
    description = db.Column(db.Text, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "week_start": self.week_start.isoformat() if self.week_start else None,
            "category": self.category,
            "amount": self.amount,
            "count": self.count,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
