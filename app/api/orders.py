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
        shipping_type=data.get("shipping_type", "normal"),
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
            
            # Aplicar oferta semanal si existe y no se especificó unit_price
            unit_price = item_data.get("sale_unit_price") or item_data.get("unit_price")
            if not unit_price:
                from ..models import WeeklyOffer
                # Buscar oferta activa para este producto en la fecha del pedido
                order_date = order.created_at or datetime.utcnow()
                active_offer = WeeklyOffer.query.filter(
                    WeeklyOffer.product_id == product_id,
                    WeeklyOffer.start_date <= order_date,
                    WeeklyOffer.end_date >= order_date,
                    WeeklyOffer.active == True
                ).first()
                
                if active_offer:
                    unit_price = active_offer.special_price
                else:
                    # Si no hay oferta, usar precio de venta del producto
                    product = Product.query.get(product_id)
                    unit_price = product.sale_price if product else 0
            
            item = OrderItem(
                order_id=order.id,
                customer_id=item_customer.id if item_customer else None,
                product_id=product_id,
                qty=item_data["qty"],
                unit=item_data.get("unit", "kg"),
                unit_price=unit_price,
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


@bp.route("/<int:id>", methods=["PUT"])
def update_order(id):
    """Actualiza un pedido (solo shipping_type y notes)"""
    try:
        order = Order.query.get_or_404(id)
        
        # Validar que el pedido no esté completado
        if order.status == "completed":
            return jsonify({
                "error": "No se puede modificar un pedido completado"
            }), 400
        
        data = request.json or {}
        
        # Permitir actualizar shipping_type incluso si está emitido (para correcciones)
        if "shipping_type" in data:
            shipping_type = data["shipping_type"]
            if shipping_type in ["fast", "normal", "cheap"]:
                order.shipping_type = shipping_type
            else:
                return jsonify({"error": "shipping_type debe ser 'fast', 'normal' o 'cheap'"}), 400
        
        if "notes" in data:
            order.notes = data["notes"]
        
        db.session.commit()
        
        return jsonify(order.to_dict())
    
    except Exception as e:
        db.session.rollback()
        print(f"Error actualizando pedido: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Error al actualizar pedido: {str(e)}"}), 500


@bp.route("/<int:id>/items", methods=["POST"])
def add_order_item(id):
    """Agrega un item a un pedido existente"""
    try:
        order = Order.query.get_or_404(id)
        
        # Permitir agregar items a pedidos finalized (para remates después de compra)
        # Solo bloquear si está completed
        if order.status == "completed":
            return jsonify({
                "error": "No se pueden agregar items a un pedido completado"
            }), 400
        
        data = request.json
        
        # Validar campos requeridos
        if not data:
            return jsonify({"error": "No se enviaron datos"}), 400
        
        if "customer_id" not in data:
            return jsonify({"error": "customer_id es requerido"}), 400
        
        if "product_id" not in data:
            return jsonify({"error": "product_id es requerido"}), 400
        
        if "qty" not in data:
            return jsonify({"error": "qty es requerido"}), 400
        
        # Validar que el producto existe
        product = Product.query.get(data["product_id"])
        if not product:
            return jsonify({"error": f"Producto con id {data['product_id']} no encontrado"}), 404
        
        # Validar que el cliente existe
        customer = Customer.query.get(data["customer_id"])
        if not customer:
            return jsonify({"error": f"Cliente con id {data['customer_id']} no encontrado"}), 404
        
        # Aplicar oferta semanal si no se especificó unit_price
        unit_price = data.get("unit_price")
        if not unit_price:
            from ..models import WeeklyOffer
            # Buscar oferta activa para este producto
            order_date = order.created_at or datetime.utcnow()
            active_offer = WeeklyOffer.query.filter(
                WeeklyOffer.product_id == data["product_id"],
                WeeklyOffer.start_date <= order_date,
                WeeklyOffer.end_date >= order_date,
                WeeklyOffer.active == True
            ).first()
            
            if active_offer:
                unit_price = active_offer.special_price
            else:
                # Si no hay oferta, usar precio de venta del producto
                unit_price = product.sale_price if product else 0
        
        item = OrderItem(
            order_id=order.id,
            customer_id=data["customer_id"],
            product_id=data["product_id"],
            qty=data["qty"],
            unit=data.get("unit", "kg"),
            unit_price=unit_price,
            notes=data.get("notes"),
        )
        
        db.session.add(item)
        db.session.commit()
        
        return jsonify(item.to_dict()), 201
    
    except Exception as e:
        db.session.rollback()
        print(f"Error agregando item a pedido: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Error al agregar item: {str(e)}"}), 500


@bp.route("/items/<int:item_id>", methods=["PUT"])
def update_order_item(item_id):
    """Actualiza un item de pedido"""
    try:
        item = OrderItem.query.get_or_404(item_id)
        
        # Permitir editar items de pedidos completados (para ajustes después de registrar compra)
        # Solo bloquear si el pedido está en draft (aún no emitido)
        if item.order.status == "draft":
            return jsonify({
                "error": "No se pueden modificar items de un pedido en borrador. Emite el pedido primero."
            }), 400
        
        data = request.json or {}
        
        if "qty" in data:
            item.qty = data["qty"]
        if "unit_price" in data:
            item.unit_price = data["unit_price"]
        elif "unit_price" not in data and item.product:
            # Si no se especificó unit_price, verificar si hay oferta activa
            from ..models import WeeklyOffer
            order_date = item.order.created_at or datetime.utcnow()
            active_offer = WeeklyOffer.query.filter(
                WeeklyOffer.product_id == item.product_id,
                WeeklyOffer.start_date <= order_date,
                WeeklyOffer.end_date >= order_date,
                WeeklyOffer.active == True
            ).first()
            
            if active_offer:
                item.unit_price = active_offer.special_price
            elif not item.unit_price:
                # Si no hay oferta y no hay unit_price, usar precio del producto
                item.unit_price = item.product.sale_price if item.product else None
        if "notes" in data:
            item.notes = data["notes"]
        
        db.session.commit()
        
        return jsonify(item.to_dict())
    
    except Exception as e:
        db.session.rollback()
        print(f"Error actualizando item: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Error al actualizar item: {str(e)}"}), 500


@bp.route("/items/<int:item_id>", methods=["DELETE"])
def delete_order_item(item_id):
    """Elimina un item de pedido"""
    try:
        item = OrderItem.query.get_or_404(item_id)
        
        # Validar que el pedido no esté completado
        if item.order.status == "completed":
            return jsonify({
                "error": "No se pueden eliminar items de un pedido completado"
            }), 400
        
        db.session.delete(item)
        db.session.commit()
        
        return jsonify({"message": "Item eliminado"})
    
    except Exception as e:
        db.session.rollback()
        print(f"Error eliminando item: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Error al eliminar item: {str(e)}"}), 500


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


@bp.route("/fix-finalized", methods=["POST"])
def fix_finalized_orders():
    """
    Endpoint temporal para corregir pedidos con estado 'finalized' (incorrecto)
    y cambiarlos a 'completed' (correcto)
    
    También busca pedidos emitidos que tienen todos sus productos con precio de compra
    y los marca como completados.
    """
    try:
        from sqlalchemy import text
        
        # Método 1: Buscar pedidos con status 'finalized' directamente en la BD
        # (por si acaso se guardó como string en la base de datos)
        result = db.session.execute(text("SELECT id, status FROM orders WHERE status = 'finalized'"))
        finalized_in_db = result.fetchall()
        
        # Método 2: Buscar en el modelo (por si SQLAlchemy los encuentra)
        all_orders = Order.query.all()
        finalized_orders = [o for o in all_orders if o.status == 'finalized']
        
        # Combinar ambos métodos
        all_finalized_ids = set()
        for row in finalized_in_db:
            all_finalized_ids.add(row[0])
        for order in finalized_orders:
            all_finalized_ids.add(order.id)
        
        fixed_count = 0
        fixed_order_ids = []
        
        # Corregir pedidos encontrados
        for order_id in all_finalized_ids:
            order = Order.query.get(order_id)
            if order and order.status == 'finalized':
                order.status = "completed"
                if not order.completed_at:
                    order.completed_at = datetime.utcnow()
                fixed_count += 1
                fixed_order_ids.append(order_id)
        
        # Método 3: Buscar pedidos emitidos que deberían estar completados
        # (tienen todos sus productos con precio de compra)
        emitted_orders = Order.query.filter_by(status="emitted").all()
        for order in emitted_orders:
            # Verificar si todos los productos del pedido tienen compra registrada
            all_purchased = True
            for item in order.items:
                item_product = Product.query.get(item.product_id)
                if not item_product or not item_product.purchase_price:
                    all_purchased = False
                    break
            
            # Si todos tienen precio, marcar como completado
            if all_purchased:
                order.status = "completed"
                if not order.completed_at:
                    order.completed_at = datetime.utcnow()
                fixed_count += 1
                fixed_order_ids.append(order.id)
        
        db.session.commit()
        
        return jsonify({
            "message": f"Se corrigieron {fixed_count} pedido(s)",
            "fixed": fixed_count,
            "order_ids": fixed_order_ids,
            "details": {
                "finalized_found": len(all_finalized_ids),
                "emitted_to_completed": fixed_count - len(all_finalized_ids)
            }
        }), 200
    
    except Exception as e:
        db.session.rollback()
        print(f"Error corrigiendo pedidos finalized: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Error al corregir pedidos: {str(e)}"}), 500

