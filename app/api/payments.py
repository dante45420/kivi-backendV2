"""
API: Pagos
Registro de pagos y asignación a items
"""
from flask import Blueprint, request, jsonify
from datetime import datetime
from ..db import db
from ..models import Payment, PaymentAllocation, OrderItem, Customer

bp = Blueprint("payments", __name__)


@bp.route("", methods=["GET"])
def get_payments():
    """Lista todos los pagos"""
    customer_id = request.args.get("customer_id")
    
    query = Payment.query
    
    if customer_id:
        query = query.filter_by(customer_id=int(customer_id))
    
    payments = query.order_by(Payment.date.desc()).all()
    
    return jsonify([p.to_dict() for p in payments])


@bp.route("/<int:id>", methods=["GET"])
def get_payment(id):
    """Obtiene un pago"""
    payment = Payment.query.get_or_404(id)
    return jsonify(payment.to_dict())


@bp.route("", methods=["POST"])
def create_payment():
    """
    Registra un nuevo pago
    Sistema simplificado: los pagos solo se asocian al cliente
    """
    data = request.json
    
    # Parsear fecha (manejar formato ISO con Z)
    payment_date = datetime.utcnow()
    if "date" in data and data["date"]:
        date_str = data["date"].replace('Z', '+00:00')  # Convertir Z a +00:00
        payment_date = datetime.fromisoformat(date_str)
    
    payment = Payment(
        customer_id=data["customer_id"],
        amount=round(data["amount"]),
        method=data.get("method"),
        reference=data.get("reference"),
        notes=data.get("notes"),
        date=payment_date,
    )
    
    db.session.add(payment)
    db.session.commit()
    
    # Refrescar el pago para obtener datos actualizados
    db.session.refresh(payment)
    
    return jsonify(payment.to_dict()), 201


@bp.route("/<int:id>", methods=["PUT"])
def update_payment(id):
    """Actualiza un pago (monto, método, referencia, notas)"""
    payment = Payment.query.get_or_404(id)
    data = request.json or {}
    
    if "amount" in data:
        payment.amount = round(data["amount"])
    if "method" in data:
        payment.method = data["method"]
    if "reference" in data:
        payment.reference = data["reference"]
    if "notes" in data:
        payment.notes = data["notes"]
    if "date" in data and data["date"]:
        date_str = data["date"].replace('Z', '+00:00')
        payment.date = datetime.fromisoformat(date_str)
    
    db.session.commit()
    
    return jsonify(payment.to_dict())


@bp.route("/<int:id>", methods=["DELETE"])
def delete_payment(id):
    """Elimina un pago"""
    payment = Payment.query.get_or_404(id)
    
    db.session.delete(payment)
    db.session.commit()
    
    return jsonify({"message": "Pago eliminado"})


# Función allocate_payment_auto eliminada - ya no se usa en el sistema simplificado


@bp.route("/customer/<int:customer_id>/invoice", methods=["GET"])
def generate_invoice(customer_id):
    """Genera nota de cobro para un cliente"""
    customer = Customer.query.get_or_404(customer_id)
    
    # Items no pagados
    unpaid_items = OrderItem.query.filter_by(
        customer_id=customer_id,
        paid=False
    ).all()
    
    # Agrupar por pedido
    by_order = {}
    for item in unpaid_items:
        if item.order_id not in by_order:
            by_order[item.order_id] = []
        by_order[item.order_id].append(item.to_dict())
    
    total = sum(item.qty * (item.unit_price or 0) for item in unpaid_items)
    
    return jsonify({
        "customer": customer.to_dict(),
        "orders": by_order,
        "items": [item.to_dict() for item in unpaid_items],
        "total": round(total),
        "generated_at": datetime.utcnow().isoformat(),
    })

