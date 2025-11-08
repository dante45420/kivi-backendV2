"""
API: Pedidos
Parseo, creación, gestión de pedidos y items
"""
from flask import Blueprint, request, jsonify
from datetime import datetime
from ..db import db
from ..models import Order, OrderItem, Customer, Product, Expense
from ..services.order_parser_simple import parse_order_text
from ..services.whatsapp import send_new_order_notification

bp = Blueprint("orders", __name__)


@bp.route("", methods=["GET"])
def get_orders():
    """Lista todos los pedidos"""
    status = request.args.get("status")
    
    query = Order.query
    
    if status:
        query = query.filter_by(status=status)
    
    orders = query.order_by(Order.created_at.desc()).all()
    
    # Incluir items y conteo
    result = []
    for order in orders:
        order_dict = order.to_dict()
        order_dict["items_count"] = len(order.items)
        order_dict["customers_count"] = len(set(item.customer_id for item in order.items))
        result.append(order_dict)
    
    return jsonify(result)


@bp.route("/<int:id>", methods=["GET"])
def get_order(id):
    """Obtiene un pedido con todos sus items"""
    order = Order.query.get_or_404(id)
    
    order_dict = order.to_dict()
    order_dict["items"] = [item.to_dict() for item in order.items]
    order_dict["expenses"] = [exp.to_dict() for exp in order.expenses]
    
    # Calcular totales
    subtotal = sum(item.qty * (item.unit_price or 0) for item in order.items)
    expenses_total = sum(exp.amount for exp in order.expenses)
    total = subtotal + expenses_total
    
    order_dict["subtotal"] = round(subtotal)
    order_dict["expenses_total"] = expenses_total
    order_dict["total"] = round(total)
    
    return jsonify(order_dict)


@bp.route("/parse", methods=["POST"])
def parse_order():
    """Parsea texto de pedido y retorna estructura con fuzzy matching de productos"""
    from ..utils.text_match import similarity_score
    
    data = request.json
    text = data.get("text", "")
    
    if not text:
        return jsonify({"error": "No se envió texto"}), 400
    
    try:
        # Parse básico
        parsed = parse_order_text(text)
        items = parsed.get("items", [])
        
        # Para cada item, buscar productos similares
        all_products = Product.query.filter_by(active=True).all()
        
        for item in items:
            product_name = item.get("product_name", "")
            suggestions = []
            exact_match = None
            
            # Buscar match exacto o similar
            for product in all_products:
                score = similarity_score(product_name, product.name)
                
                if score == 100:
                    # Match exacto
                    exact_match = product
                    item["product_id"] = product.id
                    item["product"] = product.to_dict()
                    item["match_status"] = "exact"
                    break
                elif score >= 75:
                    # Sugerencia
                    suggestions.append({
                        "id": product.id,
                        "name": product.name,
                        "score": score,
                        "category_id": product.category_id,
                        "sale_price": product.sale_price,
                        "unit": product.unit
                    })
            
            if not exact_match:
                # Ordenar sugerencias por score
                suggestions.sort(key=lambda x: x["score"], reverse=True)
                item["suggestions"] = suggestions[:5]  # Top 5
                item["match_status"] = "similar" if suggestions else "not_found"
                item["product_id"] = None
                item["product"] = None
        
        return jsonify(parsed)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("", methods=["POST"])
def create_order():
    """Crea un pedido en borrador (desde web o admin)"""
    data = request.json
    
    # Crear o buscar cliente
    customer = None
    customer_data = data.get("customer", {})
    
    if customer_data:
        # Buscar por teléfono
        if customer_data.get("phone"):
            customer = Customer.query.filter_by(phone=customer_data["phone"]).first()
        
        # Si no existe, crear
        if not customer and customer_data.get("name"):
            customer = Customer(
                name=customer_data["name"],
                phone=customer_data.get("phone", ""),
                address=customer_data.get("address", "")
            )
            db.session.add(customer)
            db.session.flush()  # Para obtener el ID
    
    # Crear orden
    order = Order(
        status="draft",
        source=data.get("source", "manual"),
        shipping_type=data.get("shipping_type", "fast"),
        notes=data.get("notes"),
    )
    
    db.session.add(order)
    db.session.flush()
    
    # Agregar items
    if "items" in data and len(data["items"]) > 0:
        for item_data in data["items"]:
            product_id = item_data.get("product_id")
            
            # Si necesita crear producto nuevo
            if item_data.get("create_if_missing") and not product_id:
                new_product = Product(
                    name=item_data.get("product_name", "Producto sin nombre"),
                    category_id=1,  # Categoría por defecto (Fruta)
                    sale_price=item_data.get("sale_unit_price", 0),
                    unit=item_data.get("default_unit", "kg"),
                    active=True
                )
                db.session.add(new_product)
                db.session.flush()
                product_id = new_product.id
            
            # Buscar o crear cliente por nombre
            customer_name = item_data.get("customer_name", "").strip()
            item_customer = customer
            
            if customer_name and not customer:
                # Buscar cliente por nombre
                item_customer = Customer.query.filter_by(name=customer_name).first()
                if not item_customer:
                    # Crear cliente nuevo
                    item_customer = Customer(
                        name=customer_name,
                        phone="",
                        address=""
                    )
                    db.session.add(item_customer)
                    db.session.flush()
            
            item = OrderItem(
                order_id=order.id,
                customer_id=item_customer.id if item_customer else None,
                product_id=product_id,
                qty=item_data["qty"],
                unit=item_data.get("unit", "kg"),
                unit_price=item_data.get("sale_unit_price", 0),
                notes=item_data.get("notes"),
            )
            db.session.add(item)
    
    db.session.commit()
    
    # Notificar si es de web (sin hacer fallar si no funciona)
    if order.source == "web":
        try:
            send_new_order_notification(order.id)
        except Exception as e:
            print(f"Error enviando notificación: {e}")
    
    return jsonify({
        "order_id": order.id,
        "customer_id": customer.id if customer else None,
        "message": "Pedido creado exitosamente"
    }), 201


@bp.route("/<int:id>/emit", methods=["PUT"])
def emit_order(id):
    """Emite un pedido (lo saca de borrador)"""
    order = Order.query.get_or_404(id)
    
    if order.status != "draft":
        return jsonify({"error": "Solo se pueden emitir pedidos en borrador"}), 400
    
    order.status = "emitted"
    order.emitted_at = datetime.utcnow()
    
    db.session.commit()
    
    return jsonify(order.to_dict())


@bp.route("/<int:id>/complete", methods=["PUT"])
def complete_order(id):
    """Marca un pedido como completado"""
    order = Order.query.get_or_404(id)
    
    order.status = "completed"
    order.completed_at = datetime.utcnow()
    
    db.session.commit()
    
    return jsonify(order.to_dict())


@bp.route("/<int:id>/items", methods=["POST"])
def add_order_item(id):
    """Agrega un item a un pedido existente"""
    order = Order.query.get_or_404(id)
    data = request.json
    
    item = OrderItem(
        order_id=order.id,
        customer_id=data["customer_id"],
        product_id=data["product_id"],
        qty=data["qty"],
        unit=data.get("unit", "kg"),
        unit_price=data.get("unit_price"),
        notes=data.get("notes"),
    )
    
    db.session.add(item)
    db.session.commit()
    
    return jsonify(item.to_dict()), 201


@bp.route("/items/<int:item_id>", methods=["PUT"])
def update_order_item(item_id):
    """Actualiza un item de pedido"""
    item = OrderItem.query.get_or_404(item_id)
    data = request.json
    
    item.qty = data.get("qty", item.qty)
    item.unit_price = data.get("unit_price", item.unit_price)
    item.notes = data.get("notes", item.notes)
    
    db.session.commit()
    
    return jsonify(item.to_dict())


@bp.route("/items/<int:item_id>", methods=["DELETE"])
def delete_order_item(item_id):
    """Elimina un item de pedido"""
    item = OrderItem.query.get_or_404(item_id)
    
    db.session.delete(item)
    db.session.commit()
    
    return jsonify({"message": "Item eliminado"})


@bp.route("/<int:id>/expenses", methods=["POST"])
def add_expense(id):
    """Agrega un gasto al pedido"""
    order = Order.query.get_or_404(id)
    data = request.json
    
    expense = Expense(
        order_id=order.id,
        category=data["category"],
        amount=round(data["amount"]),
        description=data.get("description"),
    )
    
    db.session.add(expense)
    db.session.commit()
    
    return jsonify(expense.to_dict()), 201

