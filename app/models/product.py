"""
Modelo: Producto
Simplificado: foto, precio compra actual, precio venta actual, categoría
"""
from datetime import datetime
from ..db import db


class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, unique=True)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False)
    photo_url = db.Column(db.Text, nullable=True)
    
    # Precio de compra (último registrado)
    purchase_price = db.Column(db.Float, nullable=True)
    
    # Precio de venta (sin historial, solo valor actual)
    sale_price = db.Column(db.Float, nullable=True)
    
    # Unidad por defecto
    unit = db.Column(db.String(16), nullable=False, default="kg")
    
    # Promedio de conversión unidades/kg (para estimar costos)
    avg_units_per_kg = db.Column(db.Float, nullable=True)
    
    # Notas generales
    notes = db.Column(db.Text, nullable=True)
    
    # Estado
    active = db.Column(db.Boolean, default=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relación con categoría
    category = db.relationship("Category", backref="products")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "category_id": self.category_id,
            "category": self.category.to_dict() if self.category else None,
            "photo_url": self.photo_url,
            "purchase_price": self.purchase_price,
            "sale_price": self.sale_price,
            "unit": self.unit,
            "avg_units_per_kg": self.avg_units_per_kg,
            "notes": self.notes,
            "active": self.active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

