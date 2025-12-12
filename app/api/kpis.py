"""
API: KPIs Simplificados
Métricas básicas del negocio
"""
from datetime import datetime, timedelta, date
from flask import Blueprint, jsonify, request
from ..db import db
from ..models import Order, OrderItem, Customer, WeeklyCost
from ..utils.shipping import calculate_shipping


def get_week_start(dt=None):
    """Obtiene el lunes de la semana para una fecha dada. Siempre devuelve un date."""
    if dt is None:
        dt = datetime.utcnow()
    elif isinstance(dt, str):
        dt = datetime.fromisoformat(dt)
    elif isinstance(dt, date):
        dt = datetime.combine(dt, datetime.min.time())
    
    # Si dt es datetime, convertir a date para el cálculo
    if isinstance(dt, datetime):
        dt_date = dt.date()
    else:
        dt_date = dt
    
    # Calcular días desde el lunes (0 = lunes, 6 = domingo)
    days_since_monday = dt_date.weekday()
    week_start = dt_date - timedelta(days=days_since_monday)
    return week_start

bp = Blueprint("kpis", __name__, url_prefix="/api/kpis")


@bp.route("", methods=["GET"])
def get_kpis():
    """
    Obtiene KPIs simplificados:
    - Promedio de tamaño de pedido en plata (usando conversiones)
    - Número total de clientes
    - Número de pedidos totales (con monto facturado > 0)
    - Utilidad promedio por pedido (en porcentaje y en plata, usando cost en order_items)
    - Número de pedidos promedio por semana (últimos 30 días / 4)
    """
    try:
        # 1. Número total de clientes
        total_customers = Customer.query.count()
        
        # 2. Pedidos con monto facturado > 0 (completed o emitted)
        # Calcular el total de cada pedido usando la misma lógica que get_customer_debt
        orders_with_total = []
        all_orders = Order.query.filter(
            Order.status.in_(['completed', 'emitted'])
        ).all()
        
        total_orders_count = 0
        total_revenue = 0
        orders_with_utility = []
        
        for order in all_orders:
            # Calcular subtotal usando charged_qty si existe (para conversiones)
            order_subtotal = 0
            order_cost = 0
            has_cost_data = False  # Cambiar a False inicialmente
            items_with_cost = 0
            
            for item in order.items:
                # Usar charged_qty siempre que exista (independientemente del estado del pedido)
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
                
                # Calcular costo si está registrado (manejar caso donde columna no existe)
                # Cambio: permitir que algunos items tengan costo y otros no (costo parcial)
                try:
                    item_cost_value = getattr(item, 'cost', None)
                    if item_cost_value is not None:
                        item_cost = qty_to_charge * item_cost_value
                        order_cost += item_cost
                        items_with_cost += 1
                except Exception:
                    # Si la columna no existe aún, no tiene datos de costo
                    pass  # No marcar has_cost_data = False aquí
            
            # Solo marcar has_cost_data como True si al menos un item tiene costo
            if items_with_cost > 0:
                has_cost_data = True
            
            # Calcular envío
            shipping_amount = calculate_shipping(order.shipping_type or 'normal', order_subtotal)
            order_total = order_subtotal + shipping_amount
            
            # Solo contar pedidos con monto > 0
            if order_total > 0:
                total_orders_count += 1
                total_revenue += order_total
                
                # Si tiene datos de costo (aunque sea parcial), calcular utilidad
                # Cambio: incluir pedidos con costo parcial para no perderlos de las estadísticas
                if has_cost_data and order_cost >= 0:  # Permitir costo 0 también
                    utility_amount = order_total - order_cost
                    utility_percent = (utility_amount / order_total) * 100 if order_total > 0 else 0
                    orders_with_utility.append({
                        'utility_amount': utility_amount,
                        'utility_percent': utility_percent
                    })
        
        # 3. Promedio de tamaño de pedido en plata
        avg_order_value = total_revenue / total_orders_count if total_orders_count > 0 else 0
        
        # 4. Utilidad promedio por pedido (solo pedidos con costo registrado)
        avg_utility_percent = 0
        avg_utility_amount = 0
        if orders_with_utility:
            avg_utility_percent = sum(o['utility_percent'] for o in orders_with_utility) / len(orders_with_utility)
            avg_utility_amount = sum(o['utility_amount'] for o in orders_with_utility) / len(orders_with_utility)
        
        # 5. Número de pedidos promedio por semana (últimos 30 días)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        recent_orders = Order.query.filter(
            Order.created_at >= thirty_days_ago,
            Order.status.in_(['completed', 'emitted'])
        ).all()
        
        # Calcular total de pedidos con monto > 0 en los últimos 30 días
        recent_orders_count = 0
        for order in recent_orders:
            order_subtotal = 0
            for item in order.items:
                # Usar charged_qty siempre que exista (independientemente del estado del pedido)
                if item.charged_qty is not None:
                    qty_to_charge = item.charged_qty
                else:
                    qty_to_charge = item.qty
                
                unit_price = item.unit_price
                if not unit_price and item.product:
                    unit_price = item.product.sale_price or 0
                
                item_revenue = round(qty_to_charge * (unit_price or 0))
                order_subtotal += item_revenue
            
            shipping_amount = calculate_shipping(order.shipping_type or 'normal', order_subtotal)
            order_total = order_subtotal + shipping_amount
            
            if order_total > 0:
                recent_orders_count += 1
        
        # Promedio por semana = pedidos últimos 30 días / 4
        avg_orders_per_week = recent_orders_count / 4 if recent_orders_count > 0 else 0
        
        return jsonify({
            "avg_order_value": round(avg_order_value),
            "total_customers": total_customers,
            "total_orders": total_orders_count,
            "avg_utility_percent": round(avg_utility_percent, 2),
            "avg_utility_amount": round(avg_utility_amount),
            "avg_orders_per_week": round(avg_orders_per_week, 2)
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Error calculando KPIs: {str(e)}"}), 500


@bp.route("/utility-details", methods=["GET"])
def get_utility_details():
    """
    Obtiene detalles de utilidad de todos los pedidos con costo registrado
    Para verificar cálculos en el frontend
    """
    try:
        all_orders = Order.query.filter(
            Order.status.in_(['completed', 'emitted'])
        ).all()
        
        orders_details = []
        
        for order in all_orders:
            order_subtotal = 0
            order_cost = 0
            has_cost_data = False  # Cambiar a False inicialmente
            items_with_cost = 0
            items_detail = []
            
            for item in order.items:
                # Usar charged_qty siempre que exista
                if item.charged_qty is not None:
                    qty_to_charge = item.charged_qty
                else:
                    qty_to_charge = item.qty
                
                # Precio de venta
                unit_price = item.unit_price
                if not unit_price and item.product:
                    unit_price = item.product.sale_price or 0
                
                item_revenue = round(qty_to_charge * (unit_price or 0))
                order_subtotal += item_revenue
                
                # Costo
                try:
                    item_cost_value = getattr(item, 'cost', None)
                    if item_cost_value is not None:
                        item_cost = qty_to_charge * item_cost_value
                        order_cost += item_cost
                        items_with_cost += 1
                        
                        items_detail.append({
                            'item_id': item.id,  # ID del item para poder editarlo
                            'product_name': item.product.name if item.product else 'Producto desconocido',
                            'qty': item.qty,
                            'unit': item.unit,
                            'charged_qty': item.charged_qty,
                            'charged_unit': item.charged_unit,
                            'unit_price': unit_price,
                            'cost': item_cost_value,
                            'item_revenue': item_revenue,
                            'item_cost': item_cost,
                            'item_utility': item_revenue - item_cost,
                            'item_utility_percent': ((item_revenue - item_cost) / item_revenue * 100) if item_revenue > 0 else 0
                        })
                except Exception:
                    pass  # No marcar has_cost_data = False aquí
            
            # Solo marcar has_cost_data como True si al menos un item tiene costo
            if items_with_cost > 0:
                has_cost_data = True
            
            # Calcular envío
            shipping_amount = calculate_shipping(order.shipping_type or 'normal', order_subtotal)
            order_total = order_subtotal + shipping_amount
            
            # Incluir pedidos con costo registrado (aunque sea parcial) y monto > 0
            # Cambio: permitir costo 0 para no perder pedidos editados
            if has_cost_data and order_cost >= 0 and order_total > 0:
                utility_amount = order_total - order_cost
                utility_percent = (utility_amount / order_total) * 100 if order_total > 0 else 0
                
                orders_details.append({
                    'order_id': order.id,
                    'order_date': order.created_at.isoformat() if order.created_at else None,
                    'status': order.status,
                    'items': items_detail,
                    'subtotal': order_subtotal,
                    'shipping_amount': shipping_amount,
                    'order_total': order_total,
                    'order_cost': order_cost,
                    'utility_amount': utility_amount,
                    'utility_percent': utility_percent
                })
        
        # Ordenar por fecha más reciente primero
        orders_details.sort(key=lambda x: x['order_date'] or '', reverse=True)
        
        return jsonify({
            'total_orders': len(orders_details),
            'orders': orders_details
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Error obteniendo detalles de utilidad: {str(e)}"}), 500


@bp.route("/utility-by-week", methods=["GET"])
def get_utility_by_week():
    """
    Obtiene la utilidad por semana ordenada desde la más antigua hasta la actual.
    Incluye:
    - Utilidad total por pedidos de esa semana
    - Costos de esa semana (agrupados por categoría)
    - Resultado final de la semana (utilidad - costos)
    """
    try:
        # Obtener todos los pedidos completados o emitidos
        all_orders = Order.query.filter(
            Order.status.in_(['completed', 'emitted'])
        ).all()
        
        # Agrupar pedidos por semana
        weeks_data = {}
        
        for order in all_orders:
            if not order.created_at:
                continue
            
            # Obtener el lunes de la semana del pedido
            try:
                week_start = get_week_start(order.created_at)
                week_key = week_start.isoformat() if week_start else None
                if not week_key:
                    continue
            except Exception as e:
                print(f"⚠️  Error calculando semana para pedido {order.id}: {e}")
                continue
            
            if week_key not in weeks_data:
                weeks_data[week_key] = {
                    'week_start': week_key,
                    'orders': [],
                    'orders_utility': 0,
                    'orders_revenue': 0,
                    'orders_cost': 0
                }
            
            # Calcular utilidad del pedido
            order_subtotal = 0
            order_cost = 0
            has_cost_data = False  # Cambiar a False inicialmente
            items_with_cost = 0
            
            for item in order.items:
                # Usar charged_qty siempre que exista
                if item.charged_qty is not None:
                    qty_to_charge = item.charged_qty
                else:
                    qty_to_charge = item.qty
                
                # Precio de venta
                unit_price = item.unit_price
                if not unit_price and item.product:
                    unit_price = item.product.sale_price or 0
                
                item_revenue = round(qty_to_charge * (unit_price or 0))
                order_subtotal += item_revenue
                
                # Costo
                try:
                    item_cost_value = getattr(item, 'cost', None)
                    if item_cost_value is not None:
                        item_cost = qty_to_charge * item_cost_value
                        order_cost += item_cost
                        items_with_cost += 1
                except Exception:
                    pass  # No marcar has_cost_data = False aquí
            
            # Solo marcar has_cost_data como True si al menos un item tiene costo
            if items_with_cost > 0:
                has_cost_data = True
            
            # Calcular envío
            shipping_amount = calculate_shipping(order.shipping_type or 'normal', order_subtotal)
            order_total = order_subtotal + shipping_amount
            
            # Solo incluir pedidos con monto > 0
            if order_total > 0:
                weeks_data[week_key]['orders'].append({
                    'order_id': order.id,
                    'order_date': order.created_at.isoformat() if order.created_at else None,
                    'total': order_total
                })
                weeks_data[week_key]['orders_revenue'] += order_total
                
                # Si tiene datos de costo (aunque sea parcial), calcular utilidad
                # Cambio: permitir costo 0 para no perder pedidos editados
                if has_cost_data and order_cost >= 0:
                    utility_amount = order_total - order_cost
                    weeks_data[week_key]['orders_utility'] += utility_amount
                    weeks_data[week_key]['orders_cost'] += order_cost
        
        # Obtener costos semanales (manejar caso donde la tabla no existe aún)
        costs_by_week = {}
        try:
            all_weekly_costs = WeeklyCost.query.all()
            
            for cost in all_weekly_costs:
                week_key = cost.week_start.isoformat() if cost.week_start else None
                if not week_key:
                    continue
                    
                if week_key not in costs_by_week:
                    costs_by_week[week_key] = {
                        'categories': {},
                        'total': 0
                    }
                
                if cost.category not in costs_by_week[week_key]['categories']:
                    costs_by_week[week_key]['categories'][cost.category] = {
                        'amount': 0,
                        'count': 0
                    }
                
                costs_by_week[week_key]['categories'][cost.category]['amount'] += cost.amount
                costs_by_week[week_key]['categories'][cost.category]['count'] += cost.count
                costs_by_week[week_key]['total'] += cost.amount
        except Exception as cost_error:
            # Si la tabla no existe o hay un error, simplemente no incluir costos
            print(f"⚠️  Advertencia: No se pudieron cargar costos semanales: {cost_error}")
            # Continuar sin costos
        
        # Combinar datos de semanas
        result = []
        for week_key, week_data in weeks_data.items():
            week_costs = costs_by_week.get(week_key, {'categories': {}, 'total': 0})
            
            # Calcular resultado final
            final_result = week_data['orders_utility'] - week_costs['total']
            
            result.append({
                'week_start': week_data['week_start'],
                'orders_count': len(week_data['orders']),
                'orders_revenue': round(week_data['orders_revenue']),
                'orders_utility': round(week_data['orders_utility']),
                'orders_cost': round(week_data['orders_cost']),
                'weekly_costs': week_costs['categories'],
                'weekly_costs_total': round(week_costs['total']),
                'final_result': round(final_result)
            })
        
        # Ordenar por semana (más antigua primero)
        result.sort(key=lambda x: x['week_start'])
        
        # Obtener la última semana registrada
        last_week = result[-1] if result else None
        
        return jsonify({
            'weeks': result,
            'last_week': last_week
        })
    
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"❌ Error obteniendo utilidad por semana: {e}")
        print(error_trace)
        return jsonify({
            "error": f"Error obteniendo utilidad por semana: {str(e)}",
            "details": error_trace if request.args.get("debug") == "true" else None
        }), 500

