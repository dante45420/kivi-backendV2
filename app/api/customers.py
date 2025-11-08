"""
API: Clientes
CRUD completo
"""
from flask import Blueprint, request, jsonify
from ..db import db
from ..models import Customer, OrderItem, Payment, PaymentAllocation

bp = Blueprint("customers", __name__)


@bp.route("", methods=["GET"])
def get_customers():
    """Lista todos los clientes"""
    search = request.args.get("search", "").strip()
    
    query = Customer.query
    
    if search:
        query = query.filter(
            db.or_(
                Customer.name.ilike(f"%{search}%"),
                Customer.phone.ilike(f"%{search}%")
            )
        )
    
    customers = query.order_by(Customer.name).all()
    return jsonify([c.to_dict() for c in customers])


@bp.route("/<int:id>", methods=["GET"])
def get_customer(id):
    """Obtiene un cliente por ID"""
    customer = Customer.query.get_or_404(id)
    return jsonify(customer.to_dict())


@bp.route("", methods=["POST"])
def create_customer():
    """Crea un nuevo cliente"""
    data = request.json
    
    # Verificar si ya existe por teléfono
    if data.get("phone"):
        existing = Customer.query.filter_by(phone=data["phone"]).first()
        if existing:
            return jsonify({"error": "Ya existe un cliente con ese teléfono"}), 400
    
    customer = Customer(
        name=data["name"],
        phone=data.get("phone"),
        email=data.get("email"),
        address=data.get("address"),
        preferences=data.get("preferences"),
        notes=data.get("notes"),
    )
    
    db.session.add(customer)
    db.session.commit()
    
    return jsonify(customer.to_dict()), 201


@bp.route("/<int:id>", methods=["PUT"])
def update_customer(id):
    """Actualiza un cliente"""
    customer = Customer.query.get_or_404(id)
    data = request.json
    
    customer.name = data.get("name", customer.name)
    customer.phone = data.get("phone", customer.phone)
    customer.email = data.get("email", customer.email)
    customer.address = data.get("address", customer.address)
    customer.preferences = data.get("preferences", customer.preferences)
    customer.notes = data.get("notes", customer.notes)
    
    db.session.commit()
    
    return jsonify(customer.to_dict())


@bp.route("/<int:id>", methods=["DELETE"])
def delete_customer(id):
    """Elimina un cliente"""
    customer = Customer.query.get_or_404(id)
    
    # Verificar que no tenga pedidos pendientes
    pending_items = OrderItem.query.filter_by(customer_id=id, paid=False).count()
    if pending_items > 0:
        return jsonify({"error": "No se puede eliminar, tiene pedidos pendientes"}), 400
    
    db.session.delete(customer)
    db.session.commit()
    
    return jsonify({"message": "Cliente eliminado"})


@bp.route("/<int:id>/balance", methods=["GET"])
def get_customer_balance(id):
    """Obtiene el balance del cliente (deuda pendiente)"""
    customer = Customer.query.get_or_404(id)
    
    # Items no pagados
    unpaid_items = OrderItem.query.filter_by(customer_id=id, paid=False).all()
    
    total_debt = sum(item.qty * (item.unit_price or 0) for item in unpaid_items)
    
    # Pagos totales
    payments = Payment.query.filter_by(customer_id=id).all()
    total_paid = sum(p.amount for p in payments)
    
    # Asignaciones
    allocations = PaymentAllocation.query.join(Payment).filter(Payment.customer_id == id).all()
    total_allocated = sum(a.amount for a in allocations)
    
    return jsonify({
        "customer": customer.to_dict(),
        "total_debt": round(total_debt),
        "unpaid_items_count": len(unpaid_items),
        "total_paid": total_paid,
        "total_allocated": total_allocated,
        "balance": round(total_debt - total_allocated),
    })

