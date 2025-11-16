"""
API: Clientes
CRUD completo
"""
from flask import Blueprint, request, jsonify
from ..db import db
from ..models import Customer, OrderItem, Payment

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


@bp.route("/<int:id>/debt", methods=["GET"])
def get_customer_debt(id):
    """
    Calcula la deuda total del cliente
    Considera: pedidos finalizados con conversiones, ofertas y envío
    """
    from ..models import Order
    from ..utils.shipping import calculate_shipping
    
    customer = Customer.query.get_or_404(id)
    
    # Obtener todos los pedidos finalizados del cliente (completed o emitted)
    finalized_orders = Order.query.filter(
        Order.status.in_(['completed', 'emitted'])
    ).all()
    
    total_debt = 0
    orders_detail = []
    
    for order in finalized_orders:
        # Obtener items del cliente en este pedido
        customer_items = [item for item in order.items if item.customer_id == id]
        
        if not customer_items:
            continue
        
        # Calcular subtotal del pedido para este cliente
        order_subtotal = 0
        items_detail = []
        
        for item in customer_items:
            # Usar charged_qty si existe (conversión aplicada), sino qty
            qty_to_charge = item.charged_qty if item.charged_qty is not None else item.qty
            
            # Usar unit_price (ya incluye ofertas si se aplicaron), sino precio del producto
            unit_price = item.unit_price
            if not unit_price and item.product:
                unit_price = item.product.sale_price or 0
            
            item_total = round(qty_to_charge * (unit_price or 0))
            order_subtotal += item_total
            
            items_detail.append({
                "item_id": item.id,
                "product_name": item.product.name if item.product else "Producto desconocido",
                "qty": item.qty,
                "unit": item.unit,
                "charged_qty": item.charged_qty,
                "charged_unit": item.charged_unit,
                "unit_price": unit_price,
                "total": item_total
            })
        
        # Calcular envío para este pedido
        shipping_amount = calculate_shipping(order.shipping_type, order_subtotal)
        order_total = order_subtotal + shipping_amount
        
        total_debt += order_total
        
        orders_detail.append({
            "order_id": order.id,
            "order_date": order.created_at.isoformat() if order.created_at else None,
            "shipping_type": order.shipping_type,
            "subtotal": order_subtotal,
            "shipping_amount": shipping_amount,
            "total": order_total,
            "items": items_detail
        })
    
    # Obtener pagos totales del cliente
    payments = Payment.query.filter_by(customer_id=id).all()
    total_paid = sum(p.amount for p in payments)
    
    # Deuda pendiente
    pending_debt = total_debt - total_paid
    
    return jsonify({
        "customer": customer.to_dict(),
        "total_debt": round(total_debt),
        "total_paid": round(total_paid),
        "pending_debt": round(pending_debt),
        "orders": orders_detail,
        "orders_count": len(orders_detail)
    })


@bp.route("/<int:id>/balance", methods=["GET"])
def get_customer_balance(id):
    """Obtiene el balance del cliente (compatibilidad con código antiguo)"""
    return get_customer_debt(id)

