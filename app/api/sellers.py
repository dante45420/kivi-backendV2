"""
API: Vendedores
CRUD completo (similar a customers)
"""
from datetime import datetime
from flask import Blueprint, request, jsonify
from ..db import db
from ..models import Seller, Order, Expense
from ..utils.shipping import calculate_shipping

bp = Blueprint("sellers", __name__, url_prefix="/api/sellers")


@bp.route("", methods=["GET"])
def get_sellers():
    """Lista todos los vendedores"""
    search = request.args.get("search", "").strip()
    
    query = Seller.query
    
    if search:
        query = query.filter(
            db.or_(
                Seller.name.ilike(f"%{search}%"),
                Seller.phone.ilike(f"%{search}%")
            )
        )
    
    sellers = query.order_by(Seller.name).all()
    return jsonify([s.to_dict() for s in sellers])


@bp.route("/<int:id>", methods=["GET"])
def get_seller(id):
    """Obtiene un vendedor por ID"""
    seller = Seller.query.get_or_404(id)
    return jsonify(seller.to_dict())


@bp.route("", methods=["POST"])
def create_seller():
    """Crea un nuevo vendedor"""
    data = request.json
    
    # Verificar si ya existe por teléfono
    if data.get("phone"):
        existing = Seller.query.filter_by(phone=data["phone"]).first()
        if existing:
            return jsonify({"error": "Ya existe un vendedor con ese teléfono"}), 400
    
    seller = Seller(
        name=data.get("name", "").strip(),
        phone=data.get("phone", "").strip() or None,
        email=data.get("email", "").strip() or None,
        address=data.get("address", "").strip() or None,
        preferences=data.get("preferences") or None,
        notes=data.get("notes") or None
    )
    
    if not seller.name:
        return jsonify({"error": "El nombre es requerido"}), 400
    
    db.session.add(seller)
    db.session.commit()
    
    return jsonify(seller.to_dict()), 201


@bp.route("/<int:id>", methods=["PUT"])
def update_seller(id):
    """Actualiza un vendedor"""
    seller = Seller.query.get_or_404(id)
    data = request.json
    
    # Verificar si el teléfono ya existe en otro vendedor
    if data.get("phone") and data["phone"] != seller.phone:
        existing = Seller.query.filter(
            Seller.phone == data["phone"],
            Seller.id != id
        ).first()
        if existing:
            return jsonify({"error": "Ya existe otro vendedor con ese teléfono"}), 400
    
    seller.name = data.get("name", seller.name).strip()
    seller.phone = data.get("phone", seller.phone).strip() or None if data.get("phone") else seller.phone
    seller.email = data.get("email", seller.email).strip() or None if data.get("email") else seller.email
    seller.address = data.get("address", seller.address).strip() or None if data.get("address") else seller.address
    seller.preferences = data.get("preferences", seller.preferences) or None
    seller.notes = data.get("notes", seller.notes) or None
    seller.updated_at = datetime.utcnow()
    
    if not seller.name:
        return jsonify({"error": "El nombre es requerido"}), 400
    
    db.session.commit()
    return jsonify(seller.to_dict())


@bp.route("/<int:id>", methods=["DELETE"])
def delete_seller(id):
    """Elimina un vendedor"""
    seller = Seller.query.get_or_404(id)
    
    # Verificar si tiene pedidos asociados
    orders_count = Order.query.filter_by(seller_id=id).count()
    if orders_count > 0:
        return jsonify({
            "error": f"No se puede eliminar el vendedor porque tiene {orders_count} pedido(s) asociado(s)"
        }), 400
    
    db.session.delete(seller)
    db.session.commit()
    return jsonify({"message": "Vendedor eliminado"}), 200


@bp.route("/summary", methods=["GET"])
def get_sellers_summary():
    """
    Obtiene resumen de vendedores ordenados por monto facturado (mejor a peor)
    Muestra monto facturado y cantidad de pedidos completados
    """
    try:
        sellers = Seller.query.all()
        sellers_data = []
        
        for seller in sellers:
            # Obtener pedidos completados con este vendedor
            completed_orders = Order.query.filter(
                Order.seller_id == seller.id,
                Order.status == 'completed'
            ).all()
            
            # Calcular monto facturado y cantidad de pedidos
            total_revenue = 0
            orders_count = 0
            
            for order in completed_orders:
                # Calcular subtotal usando charged_qty si existe
                order_subtotal = 0
                for item in order.items:
                    if item.charged_qty is not None:
                        qty_to_charge = item.charged_qty
                    else:
                        qty_to_charge = item.qty
                    
                    unit_price = item.unit_price
                    if not unit_price and item.product:
                        unit_price = item.product.sale_price or 0
                    
                    item_revenue = round(qty_to_charge * (unit_price or 0))
                    order_subtotal += item_revenue
                
                # Calcular envío
                shipping_amount = calculate_shipping(order.shipping_type or 'normal', order_subtotal)
                order_total = order_subtotal + shipping_amount
                
                if order_total > 0:
                    total_revenue += order_total
                    orders_count += 1
            
            sellers_data.append({
                'seller': seller.to_dict(),
                'total_revenue': total_revenue,
                'completed_orders_count': orders_count
            })
        
        # Ordenar por monto facturado (mayor a menor)
        sellers_data.sort(key=lambda x: x['total_revenue'], reverse=True)
        
        return jsonify({
            'sellers': sellers_data,
            'count': len(sellers_data)
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Error obteniendo resumen de vendedores: {str(e)}"}), 500


@bp.route("/create-costs", methods=["POST"])
def create_seller_costs():
    """
    Crea costos para todos los pedidos completados con vendedor que no tienen costo asociado.
    Solo debe haber un costo por pedido.
    """
    try:
        # Obtener pedidos completados con vendedor que no tienen costo de vendedor
        completed_orders_with_seller = Order.query.filter(
            Order.status == 'completed',
            Order.seller_id.isnot(None)
        ).all()
        
        created_costs = []
        skipped_orders = []
        
        for order in completed_orders_with_seller:
            # Verificar si ya tiene un costo de vendedor
            existing_cost = Expense.query.filter_by(
                order_id=order.id,
                is_seller_cost=True
            ).first()
            
            if existing_cost:
                skipped_orders.append({
                    'order_id': order.id,
                    'reason': 'Ya tiene costo asociado'
                })
                continue
            
            # Crear costo (el monto debe ser proporcionado en el request o calculado)
            # Por ahora, requerimos que se proporcione el monto en el body
            data = request.json or {}
            default_amount = data.get('default_amount', 0)
            
            if default_amount <= 0:
                # Si no se proporciona monto, saltar este pedido
                skipped_orders.append({
                    'order_id': order.id,
                    'reason': 'No se proporcionó monto por defecto'
                })
                continue
            
            # Crear el costo
            cost = Expense(
                order_id=order.id,
                category='Comisión Vendedor',
                amount=int(default_amount),
                is_seller_cost=True,
                description=f'Costo asociado al vendedor para el pedido #{order.id}'
            )
            
            db.session.add(cost)
            created_costs.append({
                'order_id': order.id,
                'seller_id': order.seller_id,
                'amount': cost.amount
            })
        
        db.session.commit()
        
        return jsonify({
            'created': len(created_costs),
            'skipped': len(skipped_orders),
            'created_costs': created_costs,
            'skipped_orders': skipped_orders
        }), 201
    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Error creando costos: {str(e)}"}), 500
