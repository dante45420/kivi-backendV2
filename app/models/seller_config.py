"""
Modelo: Configuración de Vendedores
Almacena configuración global para vendedores (porcentaje de comisión)
"""
from datetime import datetime
from ..db import db


class SellerConfig(db.Model):
    __tablename__ = "seller_config"

    id = db.Column(db.Integer, primary_key=True)
    
    # Porcentaje de comisión por defecto (editable pero igual para todos)
    commission_percent = db.Column(db.Float, nullable=False, default=10.0)
    
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "commission_percent": self.commission_percent,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

