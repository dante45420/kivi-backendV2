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
    Crear una compra de producto y actualizar precio base + conversión
    """
    data = request.json
    
    product_id = data.get("product_id")
    if not product_id:
        return jsonify({"error": "product_id es requerido"}), 400
    
    product = Product.query.get(product_id)
    if not product:
        return jsonify({"error": "Producto no encontrado"}), 404
    
    qty = data.get("qty")
    unit = data.get("unit")
    price_total = data.get("price_total")
    price_per_unit = data.get("price_per_unit")
    
    if not all([qty, unit, price_total, price_per_unit]):
        return jsonify({"error": "Faltan datos requeridos"}), 400
    
    # Obtener price_per_charged_unit si está disponible
    price_per_charged_unit = data.get("price_per_charged_unit")
    if price_per_charged_unit:
        price_per_charged_unit = float(price_per_charged_unit)
    else:
        price_per_charged_unit = None
    
    # Crear registro de compra
    purchase = Purchase(
        product_id=product_id,
        qty=float(qty),
        unit=unit,
        price_total=float(price_total),
        price_per_unit=float(price_per_unit),
        price_per_charged_unit=price_per_charged_unit,
        conversion_qty=float(data.get("conversion_qty")) if data.get("conversion_qty") else None,
        conversion_unit=data.get("conversion_unit"),
        notes=data.get("notes")
    )
    db.session.add(purchase)
    
    # Calcular el precio de compra en la unidad del producto (unidad de cobro)
    # Si se proporcionó price_per_charged_unit, usarlo directamente
    if price_per_charged_unit:
        price_in_product_unit = price_per_charged_unit
    elif purchase.conversion_qty and purchase.conversion_unit:
        # Si hay conversión, convertir el precio a la unidad del producto
        if unit != product.unit:
            # El precio debe estar en la unidad del producto
            if unit == "unit" and product.unit == "kg":
                # Se compró en unidades, pero el producto es en kg
                # Precio por kg = precio_total / conversion_qty (kg cobrados)
                price_in_product_unit = float(price_total) / purchase.conversion_qty
            elif unit == "kg" and product.unit == "unit":
                # Se compró en kg, pero el producto es en unidades
                # Precio por unidad = precio_total / conversion_qty (unidades cobradas)
                price_in_product_unit = float(price_total) / purchase.conversion_qty
            else:
                # Misma unidad, usar precio_per_unit directamente
                price_in_product_unit = float(price_per_unit)
        else:
            # Misma unidad, usar precio_per_unit directamente
            price_in_product_unit = float(price_per_unit)
    else:
        # No hay conversión, usar precio_per_unit directamente
        price_in_product_unit = float(price_per_unit)
    
    # Actualizar precio de compra del producto en su unidad
    product.purchase_price = price_in_product_unit
    
    # Si hay conversión, actualizar avg_units_per_kg
    if purchase.conversion_qty and purchase.conversion_unit:
        # Calcular conversión
        if unit == "unit" and purchase.conversion_unit == "kg":
            # X unidades = Y kg → avg_units_per_kg = X / Y
            product.avg_units_per_kg = qty / purchase.conversion_qty
        elif unit == "kg" and purchase.conversion_unit == "unit":
            # X kg = Y unidades → avg_units_per_kg = Y / X
            product.avg_units_per_kg = purchase.conversion_qty / qty
        
        # Actualizar todos los OrderItems existentes con este producto
        # para aplicar la conversión
        order_items = OrderItem.query.filter_by(product_id=product_id).all()
        for item in order_items:
            # Determinar la unidad de cobro (usar la de la compra o el default del producto)
            charged_unit = purchase.conversion_unit
            
            # Calcular charged_qty basado en la conversión
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
        
        print(f"✅ Actualizado {len(order_items)} items con conversión para producto #{product_id}")
    
    # Crear historial de precio (usar el precio en la unidad del producto)
    price_history = PriceHistory(
        product_id=product_id,
        purchase_price=price_in_product_unit,
        notes=f"Compra registrada: {qty} {unit} por ${price_total} (precio en {product.unit}: ${price_in_product_unit:.2f})"
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

