"""
API: Vendedores
CRUD completo (similar a customers)
"""
from datetime import datetime, timedelta, date
from flask import Blueprint, request, jsonify
from ..db import db
from ..models import Seller, Order, Expense, SellerPayment, SellerBonus, SellerConfig
from ..utils.shipping import calculate_shipping

bp = Blueprint("sellers", __name__, url_prefix="/api/sellers")


def get_seller_commission_percent():
    """Obtiene el porcentaje de comisión configurado (por defecto 10%)"""
    try:
        config = SellerConfig.query.first()
        if config:
            return config.commission_percent
        # Si no existe configuración, crear una por defecto
        try:
            default_config = SellerConfig(commission_percent=10.0)
            db.session.add(default_config)
            db.session.commit()
            return 10.0
        except Exception as e:
            # Si falla al crear, retornar el valor por defecto sin crear
            print(f"⚠️  Advertencia: No se pudo crear configuración de vendedores: {e}")
            return 10.0
    except Exception as e:
        # Si la tabla no existe aún, retornar valor por defecto
        print(f"⚠️  Advertencia: Tabla seller_config no disponible: {e}")
        return 10.0


def calculate_order_total_for_seller(order):
    """
    Calcula el total de un pedido usando la misma lógica que nota de cobro:
    - Usa charged_qty si existe
    - Incluye shipping
    """
    order_subtotal = 0
    
    for item in order.items:
        # Usar charged_qty siempre que exista
        if item.charged_qty is not None:
            qty_to_charge = item.charged_qty
        else:
            qty_to_charge = item.qty
        
        # Usar unit_price del item, o el sale_price del producto si no existe
        unit_price = item.unit_price
        if not unit_price and item.product:
            unit_price = item.product.sale_price or 0
        
        item_revenue = round(qty_to_charge * (unit_price or 0))
        order_subtotal += item_revenue
    
    # Calcular envío
    shipping_amount = calculate_shipping(order.shipping_type or 'normal', order_subtotal)
    order_total = order_subtotal + shipping_amount
    
    return order_total


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


@bp.route("/config", methods=["GET"])
def get_seller_config():
    """Obtiene la configuración de vendedores (porcentaje de comisión)"""
    try:
        config = SellerConfig.query.first()
        if not config:
            # Crear configuración por defecto
            try:
                config = SellerConfig(commission_percent=10.0)
                db.session.add(config)
                db.session.commit()
            except Exception as e:
                # Si falla al crear, retornar valor por defecto
                print(f"⚠️  Advertencia: No se pudo crear configuración: {e}")
                return jsonify({
                    "id": 1,
                    "commission_percent": 10.0,
                    "updated_at": None
                })
        return jsonify(config.to_dict())
    except Exception as e:
        # Si la tabla no existe, retornar valor por defecto
        print(f"⚠️  Advertencia: Error obteniendo configuración: {e}")
        return jsonify({
            "id": 1,
            "commission_percent": 10.0,
            "updated_at": None
        })


@bp.route("/config", methods=["PUT"])
def update_seller_config():
    """Actualiza la configuración de vendedores (porcentaje de comisión)"""
    try:
        data = request.json
        commission_percent = data.get('commission_percent')
        
        if commission_percent is None:
            return jsonify({"error": "commission_percent es requerido"}), 400
        
        if commission_percent < 0 or commission_percent > 100:
            return jsonify({"error": "El porcentaje debe estar entre 0 y 100"}), 400
        
        config = SellerConfig.query.first()
        if not config:
            try:
                config = SellerConfig(commission_percent=commission_percent)
                db.session.add(config)
            except Exception as e:
                return jsonify({"error": f"No se pudo crear configuración: {str(e)}"}), 500
        else:
            config.commission_percent = commission_percent
        
        db.session.commit()
        return jsonify(config.to_dict())
    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Error actualizando configuración: {str(e)}"}), 500


@bp.route("/create-costs", methods=["POST"])
def create_seller_costs():
    """
    Crea costos automáticamente para todos los pedidos completados con vendedor que no tienen costo asociado.
    Calcula el costo como porcentaje de la venta usando la misma lógica que nota de cobro.
    Solo debe haber un costo por pedido.
    """
    try:
        # Obtener porcentaje de comisión configurado
        commission_percent = get_seller_commission_percent()
        
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
            
            # Calcular total del pedido usando la misma lógica que nota de cobro
            order_total = calculate_order_total_for_seller(order)
            
            if order_total <= 0:
                skipped_orders.append({
                    'order_id': order.id,
                    'reason': 'Pedido sin monto facturado'
                })
                continue
            
            # Calcular costo como porcentaje de la venta
            cost_amount = round(order_total * (commission_percent / 100))
            
            # Crear el costo
            cost = Expense(
                order_id=order.id,
                category='Comisión Vendedor',
                amount=cost_amount,
                is_seller_cost=True,
                commission_percent=commission_percent,
                description=f'Comisión del {commission_percent}% sobre venta de ${order_total} para el pedido #{order.id}'
            )
            
            db.session.add(cost)
            created_costs.append({
                'order_id': order.id,
                'seller_id': order.seller_id,
                'order_total': order_total,
                'commission_percent': commission_percent,
                'amount': cost_amount
            })
        
        db.session.commit()
        
        return jsonify({
            'created': len(created_costs),
            'skipped': len(skipped_orders),
            'commission_percent': commission_percent,
            'created_costs': created_costs,
            'skipped_orders': skipped_orders
        }), 201
    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Error creando costos: {str(e)}"}), 500


@bp.route("/<int:id>/debt", methods=["GET"])
def get_seller_debt(id):
    """
    Calcula la deuda total del vendedor (similar a get_customer_debt)
    Considera: costos de pedidos completados vs pagos realizados
    """
    try:
        seller = Seller.query.get_or_404(id)
        
        # Obtener todos los costos de vendedor asociados a pedidos de este vendedor
        seller_orders = Order.query.filter_by(seller_id=id, status='completed').all()
        order_ids = [o.id for o in seller_orders]
        
        # Obtener costos de vendedor para estos pedidos
        seller_costs = Expense.query.filter(
            Expense.order_id.in_(order_ids),
            Expense.is_seller_cost == True
        ).all()
        
        # Calcular total de costos (lo que se le debe)
        total_costs = sum(cost.amount for cost in seller_costs)
        
        # Obtener pagos totales del vendedor
        seller_payments = SellerPayment.query.filter_by(seller_id=id).all()
        total_paid = sum(float(p.amount) if p.amount is not None else 0 for p in seller_payments)
        
        # Deuda pendiente
        pending_debt = total_costs - total_paid
        
        # Detalle de costos por pedido
        costs_detail = []
        for cost in seller_costs:
            order = Order.query.get(cost.order_id)
            if order:
                order_total = calculate_order_total_for_seller(order)
                costs_detail.append({
                    'expense_id': cost.id,
                    'order_id': order.id,
                    'order_date': order.created_at.isoformat() if order.created_at else None,
                    'order_total': order_total,
                    'commission_percent': cost.commission_percent,
                    'cost_amount': cost.amount,
                    'description': cost.description
                })
        
        # Obtener pagos del vendedor
        payments_list = [p.to_dict() for p in seller_payments]
        
        return jsonify({
            "seller": seller.to_dict(),
            "total_costs": round(total_costs),
            "total_paid": round(total_paid),
            "pending_debt": round(pending_debt),
            "costs": costs_detail,
            "costs_count": len(costs_detail),
            "payments": payments_list
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Error calculando deuda del vendedor: {str(e)}"}), 500


@bp.route("/<int:id>/payments", methods=["GET"])
def get_seller_payments(id):
    """Obtiene todos los pagos de un vendedor"""
    try:
        seller = Seller.query.get_or_404(id)
        payments = SellerPayment.query.filter_by(seller_id=id).order_by(SellerPayment.date.desc()).all()
        return jsonify([p.to_dict() for p in payments])
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"❌ Error obteniendo pagos del vendedor: {e}")
        print(error_trace)
        return jsonify({
            "error": f"Error obteniendo pagos: {str(e)}",
            "details": error_trace if request.args.get("debug") == "true" else None
        }), 500


@bp.route("/<int:id>/payments", methods=["POST"])
def create_seller_payment(id):
    """Registra un pago a un vendedor"""
    try:
        seller = Seller.query.get_or_404(id)
        data = request.json
        
        if not data:
            return jsonify({"error": "Datos no proporcionados"}), 400
        
        # Convertir amount a número antes de validar
        try:
            amount = float(data.get('amount', 0))
        except (ValueError, TypeError):
            return jsonify({"error": "El monto debe ser un número válido"}), 400
        
        if amount <= 0:
            return jsonify({"error": "El monto debe ser mayor a 0"}), 400
        
        # Parsear fecha de forma segura
        payment_date = datetime.utcnow()
        if data.get('date'):
            try:
                # Intentar parsear como ISO format
                if isinstance(data['date'], str):
                    payment_date = datetime.fromisoformat(data['date'].replace('Z', '+00:00'))
                else:
                    payment_date = datetime.utcnow()
            except (ValueError, AttributeError):
                # Si falla, usar fecha actual
                payment_date = datetime.utcnow()
        
        payment = SellerPayment(
            seller_id=id,
            amount=int(round(amount)),  # Redondear y convertir a entero
            method=data.get('method'),
            reference=data.get('reference'),
            notes=data.get('notes'),
            date=payment_date
        )
        
        db.session.add(payment)
        db.session.commit()
        
        return jsonify(payment.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        import traceback
        error_trace = traceback.format_exc()
        print(f"❌ Error creando pago a vendedor: {e}")
        print(error_trace)
        return jsonify({
            "error": f"Error registrando pago: {str(e)}",
            "details": error_trace if request.args.get("debug") == "true" else None
        }), 500


@bp.route("/summary/week", methods=["GET"])
def get_sellers_summary_week():
    """
    Obtiene resumen de vendedores de la semana actual (lunes a domingo)
    Ordenados por monto facturado (mejor a peor)
    SOLO considera pedidos de esa semana
    """
    try:
        # Obtener rango de semana actual (lunes a domingo)
        now = datetime.utcnow()
        current_week_start = get_week_start(now)
        current_week_end = current_week_start + timedelta(days=6)
        current_week_end = datetime.combine(current_week_end, datetime.max.time())
        current_week_start = datetime.combine(current_week_start, datetime.min.time())
        
        sellers = Seller.query.all()
        sellers_data = []
        
        for seller in sellers:
            # Obtener pedidos completados con este vendedor SOLO de esta semana
            completed_orders = Order.query.filter(
                Order.seller_id == seller.id,
                Order.status == 'completed',
                Order.created_at >= current_week_start,
                Order.created_at <= current_week_end
            ).all()
            
            # Calcular monto facturado y cantidad de pedidos
            total_revenue = 0
            orders_count = 0
            
            for order in completed_orders:
                order_total = calculate_order_total_for_seller(order)
                
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
            'count': len(sellers_data),
            'week_start': current_week_start.isoformat(),
            'week_end': current_week_end.isoformat()
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Error obteniendo resumen semanal: {str(e)}"}), 500


def get_week_start(dt=None):
    """Obtiene el lunes de la semana para una fecha dada"""
    if dt is None:
        dt = datetime.utcnow()
    elif isinstance(dt, str):
        dt = datetime.fromisoformat(dt)
    elif isinstance(dt, date):
        dt = datetime.combine(dt, datetime.min.time())
    
    if isinstance(dt, datetime):
        dt_date = dt.date()
    else:
        dt_date = dt
    
    days_since_monday = dt_date.weekday()
    week_start = dt_date - timedelta(days=days_since_monday)
    return week_start


@bp.route("/bonus/assign", methods=["POST"])
def assign_weekly_bonus():
    """
    Asigna bonos semanales a vendedores que alcanzaron la meta de pedidos.
    Solo considera pedidos de la semana actual.
    Si alcanzan la meta, actualiza el porcentaje de comisión para los pedidos de esa semana.
    """
    try:
        data = request.json
        orders_target = data.get('orders_target')
        bonus_percent = data.get('bonus_percent')  # Porcentaje adicional de comisión
        week_start_str = data.get('week_start')
        
        if orders_target is None or bonus_percent is None:
            return jsonify({"error": "orders_target y bonus_percent son requeridos"}), 400
        
        # Obtener semana actual si no se especifica
        if week_start_str:
            week_start = datetime.fromisoformat(week_start_str).date()
        else:
            week_start = get_week_start().date()
        
        week_end = week_start + timedelta(days=6)
        week_start_dt = datetime.combine(week_start, datetime.min.time())
        week_end_dt = datetime.combine(week_end, datetime.max.time())
        
        # Obtener porcentaje de comisión base
        base_commission_percent = get_seller_commission_percent()
        final_commission_percent = base_commission_percent + bonus_percent
        
        # Obtener resumen de vendedores de esta semana
        sellers = Seller.query.all()
        bonus_recipients = []
        
        for seller in sellers:
            # Contar pedidos completados SOLO de esta semana
            week_orders = Order.query.filter(
                Order.seller_id == seller.id,
                Order.status == 'completed',
                Order.created_at >= week_start_dt,
                Order.created_at <= week_end_dt
            ).all()
            
            orders_count = len(week_orders)
            
            # Si alcanzó la meta
            if orders_count >= orders_target:
                # Calcular monto total facturado de la semana
                week_revenue = sum(calculate_order_total_for_seller(o) for o in week_orders)
                
                # Calcular bono (diferencia entre comisión con bono y sin bono)
                base_commission = round(week_revenue * (base_commission_percent / 100))
                bonus_commission = round(week_revenue * (final_commission_percent / 100))
                bonus_amount = bonus_commission - base_commission
                
                # Actualizar porcentaje de comisión en los costos de esta semana
                updated_costs = []
                for order in week_orders:
                    cost = Expense.query.filter_by(
                        order_id=order.id,
                        is_seller_cost=True
                    ).first()
                    
                    if cost:
                        # Recalcular monto con nuevo porcentaje
                        order_total = calculate_order_total_for_seller(order)
                        old_amount = cost.amount
                        new_amount = round(order_total * (final_commission_percent / 100))
                        cost.amount = new_amount
                        cost.commission_percent = final_commission_percent
                        cost.description = f'Comisión del {final_commission_percent}% (base {base_commission_percent}% + bono {bonus_percent}%) sobre venta de ${order_total} para el pedido #{order.id}'
                        updated_costs.append({
                            'order_id': order.id,
                            'old_amount': old_amount,
                            'new_amount': new_amount
                        })
                    else:
                        # Si no existe costo, crearlo con el porcentaje de bono
                        order_total = calculate_order_total_for_seller(order)
                        new_amount = round(order_total * (final_commission_percent / 100))
                        new_cost = Expense(
                            order_id=order.id,
                            category='Comisión Vendedor',
                            amount=new_amount,
                            is_seller_cost=True,
                            commission_percent=final_commission_percent,
                            description=f'Comisión del {final_commission_percent}% (base {base_commission_percent}% + bono {bonus_percent}%) sobre venta de ${order_total} para el pedido #{order.id}'
                        )
                        db.session.add(new_cost)
                        updated_costs.append({
                            'order_id': order.id,
                            'old_amount': 0,
                            'new_amount': new_amount
                        })
                
                # Crear registro de bono
                bonus = SellerBonus(
                    seller_id=seller.id,
                    week_start=week_start,
                    orders_target=orders_target,
                    orders_achieved=orders_count,
                    commission_percent=final_commission_percent,
                    bonus_amount=bonus_amount,
                    notes=f'Bono por alcanzar meta de {orders_target} pedidos en la semana'
                )
                db.session.add(bonus)
                
                bonus_recipients.append({
                    'seller': seller.to_dict(),
                    'orders_achieved': orders_count,
                    'orders_target': orders_target,
                    'week_revenue': week_revenue,
                    'base_commission': base_commission,
                    'bonus_amount': bonus_amount,
                    'final_commission': bonus_commission,
                    'commission_percent': final_commission_percent,
                    'updated_costs': updated_costs,
                    'orders': [{
                        'order_id': o.id,
                        'order_date': o.created_at.isoformat() if o.created_at else None,
                        'order_total': calculate_order_total_for_seller(o)
                    } for o in week_orders]
                })
        
        db.session.commit()
        
        return jsonify({
            'week_start': week_start.isoformat(),
            'orders_target': orders_target,
            'bonus_percent': bonus_percent,
            'base_commission_percent': base_commission_percent,
            'final_commission_percent': final_commission_percent,
            'recipients': bonus_recipients,
            'count': len(bonus_recipients)
        }), 201
    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Error asignando bonos: {str(e)}"}), 500


@bp.route("/bonus", methods=["GET"])
def get_seller_bonuses():
    """Obtiene todos los bonos asignados"""
    week_start = request.args.get('week_start')
    
    query = SellerBonus.query
    
    if week_start:
        week_start_date = datetime.fromisoformat(week_start).date()
        query = query.filter_by(week_start=week_start_date)
    
    bonuses = query.order_by(SellerBonus.week_start.desc(), SellerBonus.created_at.desc()).all()
    return jsonify([b.to_dict() for b in bonuses])
