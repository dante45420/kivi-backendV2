"""
API: Purchases / Compras
Gestión de compras de productos
"""
from datetime import datetime
from flask import Blueprint, request, jsonify
from ..db import db
from ..models import Purchase, Product, PriceHistory, Order, OrderItem

bp = Blueprint("purchases", __name__, url_prefix="/api/purchases")


@bp.route("", methods=["POST"])
def create_purchase():
    """
    Registrar una compra de producto
    - Registra la conversión cuando corresponda
    - Registra el precio del producto (en unidad correspondiente o monto total pagado)
    - Actualiza el costo en OrderItems relacionados
    """
    data = request.json
    
    product_id = data.get("product_id")
    if not product_id:
        return jsonify({"error": "product_id es requerido"}), 400
    
    product = Product.query.get(product_id)
    if not product:
        return jsonify({"error": "Producto no encontrado"}), 404
    
    # Datos básicos de la compra
    qty = float(data.get("qty", 0))
    unit = data.get("unit", "kg")
    price_total = float(data.get("price_total", 0))
    
    if not qty or not price_total:
        return jsonify({"error": "qty y price_total son requeridos"}), 400
    
    # Precio por unidad (opcional, se puede calcular)
    price_per_unit = data.get("price_per_unit")
    if price_per_unit:
        price_per_unit = float(price_per_unit)
    else:
        price_per_unit = price_total / qty
    
    # Conversión (opcional)
    conversion_qty = data.get("conversion_qty")
    conversion_unit = data.get("conversion_unit")
    if conversion_qty:
        conversion_qty = float(conversion_qty)
    
    # Precio por unidad de cobro (opcional, si se proporciona directamente)
    price_per_charged_unit = data.get("price_per_charged_unit")
    if price_per_charged_unit:
        price_per_charged_unit = float(price_per_charged_unit)
    
    # Crear registro de compra
    purchase = Purchase(
        product_id=product_id,
        qty=qty,
        unit=unit,
        price_total=price_total,
        price_per_unit=price_per_unit,
        price_per_charged_unit=price_per_charged_unit,
        conversion_qty=conversion_qty,
        conversion_unit=conversion_unit,
        notes=data.get("notes")
    )
    db.session.add(purchase)
    
    # Calcular precio en unidad de cobro (unidad del producto)
    # Si se proporcionó price_per_charged_unit, usarlo directamente
    if price_per_charged_unit:
        cost_per_charged_unit = price_per_charged_unit
    elif conversion_qty and conversion_unit:
        # Hay conversión: precio_total / cantidad en unidad de cobro
        cost_per_charged_unit = price_total / conversion_qty
    else:
        # Sin conversión: usar precio por unidad
        cost_per_charged_unit = price_per_unit
    
    # Actualizar precio de compra del producto
    product.purchase_price = cost_per_charged_unit
    
    # Si hay conversión, actualizar avg_units_per_kg y aplicar conversión a OrderItems
    if conversion_qty and conversion_unit:
        # Calcular conversión para el producto
        if unit == "unit" and conversion_unit == "kg":
            # X unidades = Y kg → avg_units_per_kg = X / Y
            product.avg_units_per_kg = qty / conversion_qty
        elif unit == "kg" and conversion_unit == "unit":
            # X kg = Y unidades → avg_units_per_kg = Y / X
            product.avg_units_per_kg = conversion_qty / qty
        
        # Actualizar OrderItems existentes: aplicar conversión y registrar costo
        order_items = OrderItem.query.filter_by(product_id=product_id).all()
        charged_unit = conversion_unit
        
        for item in order_items:
            # Aplicar conversión si es necesario
            if item.unit == charged_unit:
                # No hay conversión necesaria
                item.charged_qty = item.qty
                item.charged_unit = charged_unit
            elif item.unit == "unit" and charged_unit == "kg":
                # Item en unidades, se cobra en kg
                if product.avg_units_per_kg and product.avg_units_per_kg > 0:
                    item.charged_qty = item.qty / product.avg_units_per_kg
                    item.charged_unit = charged_unit
            elif item.unit == "kg" and charged_unit == "unit":
                # Item en kg, se cobra en unidades
                if product.avg_units_per_kg and product.avg_units_per_kg > 0:
                    item.charged_qty = item.qty * product.avg_units_per_kg
                    item.charged_unit = charged_unit
            
            # Registrar el costo en la unidad de cobro (solo si no tiene costo ya)
            # Manejar caso donde la columna puede no existir aún
            try:
                current_cost = getattr(item, 'cost', None)
                if current_cost is None:
                    item.cost = cost_per_charged_unit
            except Exception:
                # Si la columna no existe, intentar asignarla (puede fallar si la migración no se ejecutó)
                try:
                    item.cost = cost_per_charged_unit
                except Exception as e:
                    print(f"⚠️  No se pudo asignar costo al item {item.id}: {e}")
        
        print(f"✅ Actualizado {len(order_items)} items con conversión y costo para producto #{product_id}")
    
    # Crear historial de precio
    price_history = PriceHistory(
        product_id=product_id,
        purchase_price=cost_per_charged_unit,
        notes=f"Compra registrada: {qty} {unit} por ${price_total} (precio en {product.unit}: ${cost_per_charged_unit:.2f})"
    )
    db.session.add(price_history)
    
    # Buscar pedidos emitidos con este producto y cambiar status a finalized
    emitted_orders = Order.query.filter_by(status="emitted").all()
    for order in emitted_orders:
        # Verificar si tiene items con este producto
        has_product = any(
            item.product_id == product_id and item.unit == unit
            for item in order.items
        )
        if has_product:
            # Verificar si todos los productos del pedido tienen compra registrada
            all_purchased = True
            for item in order.items:
                item_product = Product.query.get(item.product_id)
                if not item_product or not item_product.purchase_price:
                    all_purchased = False
                    break
            
            # Si todos tienen precio, marcar el pedido como completado
            if all_purchased:
                order.status = "completed"
                order.completed_at = datetime.utcnow()
    
    db.session.commit()
    
    return jsonify({
        "message": "Compra registrada exitosamente",
        "purchase": purchase.to_dict()
    }), 201


@bp.route("", methods=["GET"])
def get_purchases():
    """
    Obtener todas las compras
    Si se pasa ?with_customers=true, incluye información de clientes asociados
    """
    include_customers = request.args.get("with_customers", "false").lower() == "true"
    
    purchases = Purchase.query.order_by(Purchase.created_at.desc()).all()
    
    if not include_customers:
        return jsonify([p.to_dict() for p in purchases])
    
    # Incluir información de clientes asociados
    from ..models import OrderItem, Customer, Order
    
    purchases_with_customers = []
    for purchase in purchases:
        purchase_dict = purchase.to_dict()
        
        # Buscar pedidos que usaron este producto alrededor de la fecha de compra
        # Buscar items de pedidos completados que usan este producto
        # y que fueron creados cerca de la fecha de compra (dentro de 7 días antes o después)
        purchase_date = purchase.created_at
        if purchase_date:
            from datetime import timedelta
            date_start = purchase_date - timedelta(days=7)
            date_end = purchase_date + timedelta(days=7)
            
            # Buscar items de pedidos completados en ese rango de fechas
            related_items = OrderItem.query.join(Order).filter(
                OrderItem.product_id == purchase.product_id,
                Order.status.in_(["completed", "finalized"]),
                Order.created_at >= date_start,
                Order.created_at <= date_end
            ).all()
            
            # Agrupar por cliente
            customers_info = {}
            for item in related_items:
                customer = item.customer
                if customer:
                    customer_id = customer.id
                    if customer_id not in customers_info:
                        customers_info[customer_id] = {
                            "customer": customer.to_dict(),
                            "items": [],
                            "total_qty": 0
                        }
                    
                    qty = item.charged_qty or item.qty
                    customers_info[customer_id]["items"].append({
                        "order_id": item.order_id,
                        "qty": qty,
                        "unit": item.charged_unit or item.unit,
                        "order_date": item.order.created_at.isoformat() if item.order.created_at else None
                    })
                    customers_info[customer_id]["total_qty"] += qty
            
            purchase_dict["customers"] = list(customers_info.values())
        
        purchases_with_customers.append(purchase_dict)
    
    return jsonify(purchases_with_customers)


@bp.route("/<int:purchase_id>", methods=["GET"])
def get_purchase(purchase_id):
    """
    Obtener una compra específica
    """
    purchase = Purchase.query.get(purchase_id)
    if not purchase:
        return jsonify({"error": "Compra no encontrada"}), 404
    
    return jsonify(purchase.to_dict())


@bp.route("/<int:purchase_id>", methods=["DELETE"])
def delete_purchase(purchase_id):
    """
    Eliminar una compra
    """
    purchase = Purchase.query.get(purchase_id)
    if not purchase:
        return jsonify({"error": "Compra no encontrada"}), 404
    
    db.session.delete(purchase)
    db.session.commit()
    
    return jsonify({"message": "Compra eliminada"}), 200

