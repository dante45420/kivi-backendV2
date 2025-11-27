"""
API: Clientes
CRUD completo
"""
from datetime import datetime
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
    try:
        from ..models import Order
        from ..utils.shipping import calculate_shipping
        
        customer = Customer.query.get_or_404(id)
        
        # Obtener pedidos finalizados que tienen items de este cliente
        # Usar join para filtrar eficientemente desde la base de datos
        from sqlalchemy.orm import joinedload
        from sqlalchemy import text
        
        # Intentar ejecutar la migración si la columna no existe
        try:
            # Verificar si la columna existe
            db_url = str(db.engine.url)
            if 'postgresql' in db_url.lower():
                check_query = text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='order_items' AND column_name='cost'
                """)
                result = db.session.execute(check_query).fetchone()
                if not result:
                    # La columna no existe, agregarla
                    db.session.execute(text("ALTER TABLE order_items ADD COLUMN cost FLOAT"))
                    db.session.commit()
                    print("✅ Migración ejecutada en get_customer_debt: columna 'cost' agregada")
        except Exception as e:
            db.session.rollback()
            print(f"⚠️  Error verificando/agregando columna cost: {e}")
        
        finalized_orders = Order.query.join(
            OrderItem, Order.id == OrderItem.order_id
        ).options(
            joinedload(Order.items).joinedload(OrderItem.product)
        ).filter(
            OrderItem.customer_id == id,
            Order.status.in_(['completed', 'emitted', 'finalized'])
        ).distinct().all()
        
        # Corregir pedidos con estado 'finalized' a 'completed' automáticamente
        needs_commit = False
        for order in finalized_orders:
            if order.status == 'finalized':
                order.status = 'completed'
                if not order.completed_at:
                    order.completed_at = datetime.utcnow()
                needs_commit = True
        
        # Guardar correcciones si hubo alguna
        if needs_commit:
            try:
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                print(f"Error al corregir estados de pedidos: {e}")
        
        total_debt = 0
        orders_detail = []
        
        for order in finalized_orders:
            try:
                # Obtener items del cliente en este pedido
                customer_items = [item for item in order.items if item.customer_id == id]
                
                if not customer_items:
                    continue
                
                # Calcular subtotal del pedido para este cliente
                order_subtotal = 0
                items_detail = []
                
                for item in customer_items:
                    try:
                        # Validar que qty y charged_qty sean números válidos
                        qty = float(item.qty) if item.qty is not None else 0
                        charged_qty = float(item.charged_qty) if item.charged_qty is not None else None
                        
                        # Usar charged_qty solo si el pedido está completed y existe conversión
                        # Si está emitted, usar qty original (aún no se ha registrado la compra)
                        if order.status == 'completed' and charged_qty is not None:
                            qty_to_charge = charged_qty
                        else:
                            qty_to_charge = qty
                        
                        # Usar unit_price (ya incluye ofertas si se aplicaron), sino precio del producto
                        unit_price = item.unit_price
                        if not unit_price or unit_price == 0:
                            if item.product:
                                unit_price = item.product.sale_price or 0
                            else:
                                unit_price = 0
                        
                        # Validar que unit_price sea un número válido
                        unit_price = float(unit_price) if unit_price is not None else 0
                        
                        item_total = round(qty_to_charge * unit_price)
                        order_subtotal += item_total
                        
                        items_detail.append({
                            "item_id": item.id,
                            "product_name": item.product.name if item.product and item.product.name else "Producto desconocido",
                            "qty": qty,
                            "unit": item.unit or "kg",
                            "charged_qty": charged_qty,
                            "charged_unit": item.charged_unit,
                            "unit_price": unit_price,
                            "total": item_total
                        })
                    except Exception as e:
                        print(f"Error procesando item {item.id}: {e}")
                        # Continuar con el siguiente item
                        continue
                
                # Calcular envío para este pedido
                try:
                    shipping_amount = calculate_shipping(order.shipping_type, order_subtotal)
                except Exception as e:
                    print(f"Error calculando shipping para pedido {order.id}: {e}")
                    shipping_amount = 0
                
                order_total = order_subtotal + shipping_amount
                total_debt += order_total
                
                orders_detail.append({
                    "order_id": order.id,
                    "order_date": order.created_at.isoformat() if order.created_at else None,
                    "order_status": order.status or "unknown",
                    "shipping_type": order.shipping_type,
                    "subtotal": order_subtotal,
                    "shipping_amount": shipping_amount,
                    "total": order_total,
                    "items": items_detail
                })
            except Exception as e:
                print(f"Error procesando pedido {order.id}: {e}")
                # Continuar con el siguiente pedido
                continue
        
        # Obtener pagos totales del cliente
        try:
            payments = Payment.query.filter_by(customer_id=id).all()
            total_paid = sum(float(p.amount) if p.amount is not None else 0 for p in payments)
        except Exception as e:
            print(f"Error obteniendo pagos del cliente {id}: {e}")
            total_paid = 0
        
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
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Error en get_customer_debt para cliente {id}: {e}")
        print(error_trace)
        return jsonify({
            "error": f"Error al calcular deuda del cliente: {str(e)}",
            "customer_id": id
        }), 500


@bp.route("/<int:id>/balance", methods=["GET"])
def get_customer_balance(id):
    """Obtiene el balance del cliente (compatibilidad con código antiguo)"""
    return get_customer_debt(id)

