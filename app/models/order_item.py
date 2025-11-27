"""
Modelo: Item de pedido
Un item = un producto para un cliente en un pedido
"""
from datetime import datetime
from ..db import db


class OrderItem(db.Model):
    __tablename__ = "order_items"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    
    qty = db.Column(db.Float, nullable=False)
    unit = db.Column(db.String(16), nullable=False, default="kg")
    unit_price = db.Column(db.Float, nullable=True)
    
    # Conversión de unidades (para cobro)
    charged_qty = db.Column(db.Float, nullable=True)
    charged_unit = db.Column(db.String(16), nullable=True)
    
    # Costo del producto (en unidad de cobro, registrado al momento de la compra)
    cost = db.Column(db.Float, nullable=True)
    
    # Estado de pago
    paid = db.Column(db.Boolean, default=False)
    
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relaciones
    order = db.relationship("Order", backref="items")
    customer = db.relationship("Customer", backref="order_items")
    product = db.relationship("Product", backref="order_items")

    def to_dict(self):
        # Usar unit_price del item, o el sale_price del producto si no existe
        effective_price = self.unit_price
        if not effective_price and self.product:
            effective_price = self.product.sale_price or 0
        
        # Usar charged_qty si está disponible, sino usar qty original
        qty_to_charge = self.charged_qty if self.charged_qty is not None else self.qty
        unit_to_charge = self.charged_unit if self.charged_unit else self.unit
        
        # En el nuevo sistema simplificado, paid_amount ya no se calcula aquí
        # Se calcula a nivel de cliente (total de pagos vs total de pedidos)
        
        return {
            "id": self.id,
            "order_id": self.order_id,
            "customer_id": self.customer_id,
            "customer": self.customer.to_dict() if self.customer else None,
            "customer_name": self.customer.name if self.customer else None,
            "product_id": self.product_id,
            "product": self.product.to_dict() if self.product else None,
            "product_name": self.product.name if self.product else None,
            "qty": self.qty,
            "unit": self.unit,
            "charged_qty": self.charged_qty,
            "charged_unit": self.charged_unit,
            "cost": self.cost,
            "unit_price": self.unit_price or effective_price,
            "paid": self.paid,  # Deprecated, pero se mantiene por compatibilidad
            "notes": self.notes,
            "total": round(qty_to_charge * effective_price) if effective_price else 0,
        }

