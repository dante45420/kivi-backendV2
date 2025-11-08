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
    """Obtiene un pago con sus asignaciones"""
    payment = Payment.query.get_or_404(id)
    
    payment_dict = payment.to_dict()
    payment_dict["allocations"] = [a.to_dict() for a in payment.allocations]
    
    return jsonify(payment_dict)


@bp.route("", methods=["POST"])
def create_payment():
    """Registra un nuevo pago"""
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
    
    # Asignar automáticamente a items no pagados del cliente
    if "order_item_ids" in data:
        allocate_payment_auto(payment.id, data["order_item_ids"])
    else:
        # Si no se especificaron items, asignar automáticamente a todos los items no pagados
        unpaid_items = OrderItem.query.filter_by(
            customer_id=data["customer_id"],
            paid=False
        ).order_by(OrderItem.created_at).all()
        
        if unpaid_items:
            allocate_payment_auto(payment.id, [item.id for item in unpaid_items])
    
    # Refrescar el pago para obtener datos actualizados después de las allocations
    db.session.refresh(payment)
    
    return jsonify(payment.to_dict()), 201


@bp.route("/<int:id>/allocate", methods=["POST"])
def allocate_payment(id):
    """Asigna un pago a items específicos"""
    payment = Payment.query.get_or_404(id)
    data = request.json
    
    # data = {"allocations": [{"order_item_id": 1, "amount": 5000}, ...]}
    for alloc in data.get("allocations", []):
        allocation = PaymentAllocation(
            payment_id=payment.id,
            order_item_id=alloc["order_item_id"],
            amount=round(alloc["amount"]),
        )
        db.session.add(allocation)
        
        # Marcar item como pagado si se cubrió completo
        item = OrderItem.query.get(alloc["order_item_id"])
        if item:
            # Usar charged_qty si está disponible
            qty_to_charge = item.charged_qty if item.charged_qty is not None else item.qty
            unit_price = item.unit_price or (item.product.sale_price if item.product else 0)
            item_total = round(qty_to_charge * unit_price)
            allocated_total = sum(a.amount for a in item.payment_allocations) + round(alloc["amount"])
            
            if allocated_total >= item_total:
                item.paid = True
    
    db.session.commit()
    
    return jsonify({"message": "Pago asignado"})


def allocate_payment_auto(payment_id, order_item_ids):
    """Asigna un pago automáticamente a los items especificados"""
    from ..models import Product
    
    payment = Payment.query.get(payment_id)
    remaining_amount = payment.amount
    
    print(f"\n🔵 ALLOCATE AUTO: Payment #{payment_id}, Amount: ${remaining_amount}")
    print(f"🔵 Items a procesar: {order_item_ids}")
    
    for item_id in order_item_ids:
        if remaining_amount <= 0:
            print(f"❌ No queda monto por asignar")
            break
        
        item = OrderItem.query.get(item_id)
        if not item:
            print(f"❌ Item #{item_id} no encontrado")
            continue
        
        # Calcular total del item, usando precio del producto si no hay unit_price
        unit_price = item.unit_price
        if not unit_price and item.product:
            # Usar el precio de venta del producto
            product = Product.query.get(item.product_id)
            if product:
                unit_price = product.sale_price or 0
                print(f"📦 Item #{item_id}: usando precio producto ${unit_price}")
        else:
            print(f"💰 Item #{item_id}: usando unit_price ${unit_price}")
        
        # Usar charged_qty si está disponible (conversión de unidades), sino usar qty
        qty_to_charge = item.charged_qty if item.charged_qty is not None else item.qty
        unit_to_charge = item.charged_unit if item.charged_unit else item.unit
        
        item_total = round(qty_to_charge * (unit_price or 0))
        print(f"📊 Item #{item_id}: qty={item.qty} {item.unit}, charged_qty={qty_to_charge} {unit_to_charge}, unit_price=${unit_price}, total=${item_total}")
        
        if item_total <= 0:
            print(f"❌ Item #{item_id}: total es 0, skip")
            continue
        
        already_paid = sum(a.amount for a in item.payment_allocations)
        item_pending = item_total - already_paid
        
        print(f"💵 Item #{item_id}: ya pagado=${already_paid}, pendiente=${item_pending}")
        
        if item_pending <= 0:
            print(f"✅ Item #{item_id}: ya está completamente pagado")
            continue
        
        # Asignar lo que se pueda
        to_allocate = min(remaining_amount, item_pending)
        
        allocation = PaymentAllocation(
            payment_id=payment.id,
            order_item_id=item.id,
            amount=to_allocate,
        )
        db.session.add(allocation)
        
        print(f"✅ Asignando ${to_allocate} al item #{item_id}")
        
        remaining_amount -= to_allocate
        
        # Marcar como pagado si se cubrió
        if to_allocate >= item_pending:
            item.paid = True
            print(f"🎉 Item #{item_id} marcado como PAGADO")
        else:
            print(f"⚠️  Item #{item_id} pago parcial (queda ${item_pending - to_allocate})")
    
    db.session.commit()
    print(f"💾 Commit realizado. Monto restante: ${remaining_amount}\n")


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

