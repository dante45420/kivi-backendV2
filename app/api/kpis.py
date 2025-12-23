"""
API: KPIs Simplificados
Métricas básicas del negocio
"""
from datetime import datetime, timedelta, date
from flask import Blueprint, jsonify, request
from ..db import db
from ..models import Order, OrderItem, Customer, WeeklyCost, Product, Expense, Seller
from ..utils.shipping import calculate_shipping
from sqlalchemy import func


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


def get_last_completed_week():
    """
    Obtiene el rango de la última semana completada (lunes a domingo).
    Si hoy es lunes, devuelve la semana pasada completa.
    Si hoy es cualquier otro día, devuelve la semana que terminó el domingo pasado.
    """
    now = datetime.utcnow()
    today = now.date()
    
    # Calcular días desde el lunes (0 = lunes, 6 = domingo)
    days_since_monday = today.weekday()
    
    # Si hoy es lunes (días desde lunes = 0), la última semana completada terminó ayer (domingo)
    # Si hoy es cualquier otro día, la última semana completada terminó el domingo pasado
    if days_since_monday == 0:
        # Hoy es lunes, la última semana completada terminó ayer (domingo)
        last_sunday = today - timedelta(days=1)
    else:
        # Hoy es martes-domingo, la última semana completada terminó el domingo pasado
        last_sunday = today - timedelta(days=days_since_monday + 1)
    
    # El lunes de la última semana completada es 6 días antes del domingo
    last_week_start = last_sunday - timedelta(days=6)
    last_week_end = last_sunday
    
    return last_week_start, last_week_end

bp = Blueprint("kpis", __name__, url_prefix="/api/kpis")

# Fecha de inicio para todas las estadísticas de KPIs (1 de marzo)
KPI_START_DATE = datetime(2024, 3, 1, 0, 0, 0)  # 1 de marzo de 2024


def calculate_order_total(order):
    """Calcula el total de un pedido usando la misma lógica que get_customer_debt"""
    order_subtotal = 0
    order_cost = 0
    has_cost_data = False
    items_with_cost = 0
    
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
        
        # Calcular costo si está registrado
        try:
            item_cost_value = getattr(item, 'cost', None)
            if item_cost_value is not None:
                item_cost = qty_to_charge * item_cost_value
                order_cost += item_cost
                items_with_cost += 1
        except Exception:
            pass
    
    if items_with_cost > 0:
        has_cost_data = True
    
    # Calcular envío
    shipping_amount = calculate_shipping(order.shipping_type or 'normal', order_subtotal)
    order_total = order_subtotal + shipping_amount
    
    return {
        'order_total': order_total,
        'order_subtotal': order_subtotal,
        'shipping_amount': shipping_amount,
        'order_cost': order_cost,
        'has_cost_data': has_cost_data,
        'utility_amount': (order_total - order_cost) if has_cost_data and order_cost >= 0 else None,
        'utility_percent': ((order_total - order_cost) / order_total * 100) if has_cost_data and order_cost >= 0 and order_total > 0 else None
    }


@bp.route("", methods=["GET"])
def get_kpis():
    """
    Obtiene KPIs con datos de última semana (lunes-domingo) e históricos:
    - Promedio de tamaño de pedido (última semana e histórico)
    - Nuevos clientes esta semana e histórico
    - Número de pedidos (última semana e histórico)
    - Utilidad promedio por pedido (última semana e histórico)
    - Monto total facturado (última semana e histórico)
    - Pedidos completados por vendedores (última semana e histórico)
    """
    try:
        # Calcular rango de última semana completada (lunes a domingo)
        last_week_start_date, last_week_end_date = get_last_completed_week()
        # Ajustar para incluir todo el día (desde inicio del lunes hasta fin del domingo)
        last_week_start = datetime.combine(last_week_start_date, datetime.min.time())
        last_week_end = datetime.combine(last_week_end_date, datetime.max.time())
        
        # Obtener todos los pedidos completados o emitidos con items cargados (desde el 1 de marzo)
        from sqlalchemy.orm import joinedload
        all_orders = Order.query.options(
            joinedload(Order.items)
        ).filter(
            Order.status.in_(['completed', 'emitted']),
            Order.created_at >= KPI_START_DATE
        ).all()
        
        # Separar pedidos de última semana e históricos
        last_week_orders = []
        historical_orders = []
        
        for order in all_orders:
            if order.created_at:
                order_date = order.created_at
                if isinstance(order_date, date) and not isinstance(order_date, datetime):
                    order_date = datetime.combine(order_date, datetime.min.time())
                
                if last_week_start <= order_date <= last_week_end:
                    last_week_orders.append(order)
                else:
                    historical_orders.append(order)
        
        # Calcular KPIs para última semana
        last_week_stats = calculate_kpis_for_orders(last_week_orders)
        
        # Calcular KPIs históricos (todos los pedidos desde el 1 de marzo)
        historical_stats = calculate_kpis_for_orders(all_orders)
        
        # Nuevos clientes en la última semana completada
        new_customers_this_week = Customer.query.filter(
            Customer.created_at >= last_week_start,
            Customer.created_at <= last_week_end
        ).count()
        
        # Total de clientes históricos (desde el 1 de marzo)
        total_customers_historical = Customer.query.filter(
            Customer.created_at >= KPI_START_DATE
        ).count()
        
        # Calcular clientes que retornaron (última semana)
        customer_return_rate_last_week = 0.0
        seller_return_rate_last_week = 0.0
        try:
            last_week_key = last_week_start_date.isoformat()
            customer_rate = calculate_customer_return_rate_for_week(last_week_key, all_orders)
            seller_rate = calculate_seller_return_rate_for_week(last_week_key, all_orders)
            # Si es None (primera o segunda semana), usar 0 para mostrar pero no afecta el promedio histórico
            customer_return_rate_last_week = customer_rate if customer_rate is not None else 0.0
            seller_return_rate_last_week = seller_rate if seller_rate is not None else 0.0
        except Exception as e:
            print(f"⚠️  Error calculando retornos para última semana: {e}")
            import traceback
            traceback.print_exc()
        
        # Calcular monto facturado por vendedores (última semana)
        last_week_orders_with_seller = [o for o in last_week_orders if o.seller_id]
        last_week_revenue_by_seller = calculate_kpis_for_orders(last_week_orders_with_seller)['total_revenue']
        
        # Calcular monto facturado por vendedores (histórico)
        all_orders_with_seller = [o for o in all_orders if o.seller_id]
        historical_revenue_by_seller = calculate_kpis_for_orders(all_orders_with_seller)['total_revenue']
        
        # Para históricos, calcular promedio de todas las semanas (desde la semana 3 en adelante)
        historical_customer_return_rate = 0.0
        historical_seller_return_rate = 0.0
        try:
            # Agrupar pedidos por semana
            orders_by_week = {}
            for order in all_orders:
                if not order.created_at:
                    continue
                # Filtrar pedidos anteriores al 1 de marzo
                if order.created_at < KPI_START_DATE:
                    continue
                order_week_start = get_week_start(order.created_at)
                if not order_week_start:
                    continue
                # Asegurar que la semana no sea anterior al 1 de marzo
                week_start_dt = datetime.combine(order_week_start, datetime.min.time())
                if week_start_dt < KPI_START_DATE:
                    continue
                week_key_order = order_week_start.isoformat() if hasattr(order_week_start, 'isoformat') else str(order_week_start)
                if not week_key_order:
                    continue
                if week_key_order not in orders_by_week:
                    orders_by_week[week_key_order] = []
                orders_by_week[week_key_order].append(order)
            
            sorted_weeks = sorted(orders_by_week.keys())
            # Calcular para cada semana desde la 3 en adelante
            return_rates_customer = []
            return_rates_seller = []
            for i, week_key in enumerate(sorted_weeks):
                if i >= 2:  # Desde la semana 3 (índice 2)
                    try:
                        # Verificar que la semana no sea anterior al 1 de marzo
                        week_start_dt = datetime.fromisoformat(week_key)
                        week_start_dt = datetime.combine(week_start_dt.date(), datetime.min.time())
                        if week_start_dt < KPI_START_DATE:
                            continue
                        
                        customer_rate = calculate_customer_return_rate_for_week(week_key, all_orders)
                        seller_rate = calculate_seller_return_rate_for_week(week_key, all_orders)
                        
                        # Solo incluir semanas con valores válidos (no None)
                        # None significa que es una de las primeras dos semanas y no debe contarse
                        if customer_rate is not None:
                            return_rates_customer.append(customer_rate)
                        if seller_rate is not None:
                            return_rates_seller.append(seller_rate)
                    except Exception as e:
                        print(f"⚠️  Error calculando retorno para semana {week_key}: {e}")
                        import traceback
                        traceback.print_exc()
                        continue
            
            if return_rates_customer:
                historical_customer_return_rate = sum(return_rates_customer) / len(return_rates_customer)
                print(f"📊 Promedio histórico clientes que retornaron: {historical_customer_return_rate:.2f}% (de {len(return_rates_customer)} semanas)")
                print(f"   - Valores por semana: {return_rates_customer}")
            if return_rates_seller:
                historical_seller_return_rate = sum(return_rates_seller) / len(return_rates_seller)
                print(f"📊 Promedio histórico vendedores que retornaron: {historical_seller_return_rate:.2f}% (de {len(return_rates_seller)} semanas)")
                print(f"   - Valores por semana: {return_rates_seller}")
        except Exception as e:
            print(f"⚠️  Error calculando promedios históricos de retorno: {e}")
            import traceback
            traceback.print_exc()
        
        return jsonify({
            "last_week": {
                "avg_order_value": last_week_stats['avg_order_value'],
                "new_customers": new_customers_this_week,
                "total_orders": last_week_stats['total_orders'],
                "avg_utility_percent": last_week_stats['avg_utility_percent'],
                "avg_utility_amount": last_week_stats['avg_utility_amount'],
                "total_revenue": last_week_stats['total_revenue'],
                "completed_orders_by_seller": last_week_stats['completed_orders_by_seller'],
                "customer_return_rate": round(customer_return_rate_last_week, 2),
                "seller_return_rate": round(seller_return_rate_last_week, 2),
                "revenue_by_seller": round(last_week_revenue_by_seller)
            },
            "historical": {
                "avg_order_value": historical_stats['avg_order_value'],
                "total_customers": total_customers_historical,
                "total_orders": historical_stats['total_orders'],
                "avg_utility_percent": historical_stats['avg_utility_percent'],
                "avg_utility_amount": historical_stats['avg_utility_amount'],
                "total_revenue": historical_stats['total_revenue'],
                "completed_orders_by_seller": historical_stats['completed_orders_by_seller'],
                "customer_return_rate": round(historical_customer_return_rate, 2),
                "seller_return_rate": round(historical_seller_return_rate, 2),
                "revenue_by_seller": round(historical_revenue_by_seller)
            },
            "week_range": {
                "start": last_week_start.isoformat(),
                "end": last_week_end.isoformat()
            }
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Error calculando KPIs: {str(e)}"}), 500


def calculate_kpis_for_orders(orders):
    """Calcula KPIs para una lista de pedidos"""
    total_orders_count = 0
    total_revenue = 0
    orders_with_utility = []
    completed_orders_by_seller = {}  # {seller_id: count}
    
    for order in orders:
        order_data = calculate_order_total(order)
        order_total = order_data['order_total']
        
        # Solo contar pedidos con monto > 0
        if order_total > 0:
            total_orders_count += 1
            total_revenue += order_total
            
            # Si tiene datos de costo, calcular utilidad
            if order_data['has_cost_data'] and order_data['order_cost'] >= 0:
                if order_data['utility_amount'] is not None:
                    orders_with_utility.append({
                        'utility_amount': order_data['utility_amount'],
                        'utility_percent': order_data['utility_percent'] or 0
                    })
            
            # Contar pedidos completados por vendedor (si existe seller_id)
            if order.status == 'completed':
                try:
                    seller_id = getattr(order, 'seller_id', None)
                    if seller_id:
                        if seller_id not in completed_orders_by_seller:
                            completed_orders_by_seller[seller_id] = 0
                        completed_orders_by_seller[seller_id] += 1
                except Exception:
                    pass
    
    # Promedio de tamaño de pedido
    avg_order_value = total_revenue / total_orders_count if total_orders_count > 0 else 0
    
    # Utilidad promedio por pedido
    avg_utility_percent = 0
    avg_utility_amount = 0
    if orders_with_utility:
        avg_utility_percent = sum(o['utility_percent'] for o in orders_with_utility) / len(orders_with_utility)
        avg_utility_amount = sum(o['utility_amount'] for o in orders_with_utility) / len(orders_with_utility)
    
    return {
        'avg_order_value': round(avg_order_value),
        'total_orders': total_orders_count,
        'avg_utility_percent': round(avg_utility_percent, 2),
        'avg_utility_amount': round(avg_utility_amount),
        'total_revenue': round(total_revenue),
        'completed_orders_by_seller': completed_orders_by_seller
    }


@bp.route("/utility-details", methods=["GET"])
def get_utility_details():
    """
    Obtiene detalles de utilidad de todos los pedidos con costo registrado
    Para verificar cálculos en el frontend
    """
    try:
        all_orders = Order.query.filter(
            Order.status.in_(['completed', 'emitted']),
            Order.created_at >= KPI_START_DATE
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
        # Obtener todos los pedidos completados o emitidos (desde el 1 de marzo)
        all_orders = Order.query.filter(
            Order.status.in_(['completed', 'emitted']),
            Order.created_at >= KPI_START_DATE
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
            # Costos semanales (WeeklyCost)
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
        
        # Agregar costos de vendedores (Expense con is_seller_cost=True)
        try:
            # Obtener todos los expenses que son costos de vendedores
            seller_expenses = Expense.query.filter_by(is_seller_cost=True).all()
            
            for expense in seller_expenses:
                # Obtener el pedido asociado para determinar la semana
                order = Order.query.get(expense.order_id)
                if not order or not order.created_at:
                    continue
                
                # Obtener el lunes de la semana del pedido
                try:
                    week_start = get_week_start(order.created_at)
                    week_key = week_start.isoformat() if week_start else None
                    if not week_key:
                        continue
                except Exception as e:
                    print(f"⚠️  Error calculando semana para expense {expense.id}: {e}")
                    continue
                
                if week_key not in costs_by_week:
                    costs_by_week[week_key] = {
                        'categories': {},
                        'total': 0
                    }
                
                # Usar la categoría del expense o "Comisión Vendedor" por defecto
                category = expense.category if expense.category else 'Comisión Vendedor'
                
                if category not in costs_by_week[week_key]['categories']:
                    costs_by_week[week_key]['categories'][category] = {
                        'amount': 0,
                        'count': 0
                    }
                
                costs_by_week[week_key]['categories'][category]['amount'] += expense.amount
                costs_by_week[week_key]['categories'][category]['count'] += 1
                costs_by_week[week_key]['total'] += expense.amount
        except Exception as expense_error:
            # Si hay un error, simplemente no incluir costos de vendedores
            print(f"⚠️  Advertencia: No se pudieron cargar costos de vendedores: {expense_error}")
            import traceback
            traceback.print_exc()
        
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


@bp.route("/by-week/<metric>", methods=["GET"])
def get_kpi_by_week(metric):
    """
    Obtiene datos históricos de un KPI específico por semana
    
    Métricas disponibles:
    - avg_order_value: Promedio de tamaño de pedido
    - new_customers: Nuevos clientes
    - total_orders: Total de pedidos
    - total_revenue: Monto total facturado
    - avg_utility_percent: Porcentaje de utilidad promedio
    - avg_utility_amount: Utilidad promedio por pedido
    - completed_orders_by_seller: Pedidos completados por vendedores
    """
    try:
        # Obtener todos los pedidos completados o emitidos con items cargados (desde el 1 de marzo)
        from sqlalchemy.orm import joinedload
        all_orders = Order.query.options(
            joinedload(Order.items)
        ).filter(
            Order.status.in_(['completed', 'emitted']),
            Order.created_at >= KPI_START_DATE
        ).all()
        
        # Agrupar por semana
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
                    'orders': []
                }
            
            weeks_data[week_key]['orders'].append(order)
        
        # Calcular métrica para cada semana
        result = []
        for week_key, week_data in weeks_data.items():
            week_orders = week_data['orders']
            
            # Calcular según la métrica solicitada
            if metric == 'avg_order_value':
                stats = calculate_kpis_for_orders(week_orders)
                value = stats['avg_order_value']
            elif metric == 'new_customers':
                # Contar clientes nuevos en esta semana (desde el 1 de marzo)
                week_start_dt = datetime.fromisoformat(week_key)
                week_end_dt = week_start_dt + timedelta(days=6)
                week_end_dt = datetime.combine(week_end_dt.date(), datetime.max.time())
                week_start_dt = datetime.combine(week_start_dt.date(), datetime.min.time())
                
                # Asegurar que la semana no sea anterior al 1 de marzo
                if week_start_dt < KPI_START_DATE:
                    value = 0
                else:
                    value = Customer.query.filter(
                        Customer.created_at >= max(week_start_dt, KPI_START_DATE),
                        Customer.created_at <= week_end_dt
                    ).count()
            elif metric == 'total_orders':
                stats = calculate_kpis_for_orders(week_orders)
                value = stats['total_orders']
            elif metric == 'total_revenue':
                stats = calculate_kpis_for_orders(week_orders)
                value = stats['total_revenue']
            elif metric == 'avg_utility_percent':
                stats = calculate_kpis_for_orders(week_orders)
                value = stats['avg_utility_percent']
            elif metric == 'avg_utility_amount':
                stats = calculate_kpis_for_orders(week_orders)
                value = stats['avg_utility_amount']
            elif metric == 'completed_orders_by_seller':
                stats = calculate_kpis_for_orders(week_orders)
                value = sum(stats['completed_orders_by_seller'].values())
            elif metric == 'customer_return_rate':
                # Calcular porcentaje de clientes que retornaron
                # Usar todos los pedidos ya cargados con items
                try:
                    value = calculate_customer_return_rate_for_week(week_key, all_orders)
                    # Si es None (primera o segunda semana), usar 0 para el gráfico
                    if value is None:
                        value = 0.0
                except Exception as e:
                    print(f"⚠️  Error calculando customer_return_rate para semana {week_key}: {e}")
                    import traceback
                    traceback.print_exc()
                    value = 0.0
            elif metric == 'seller_return_rate':
                # Calcular porcentaje de vendedores que retornaron
                try:
                    value = calculate_seller_return_rate_for_week(week_key, all_orders)
                    # Si es None (primera o segunda semana), usar 0 para el gráfico
                    if value is None:
                        value = 0.0
                except Exception as e:
                    print(f"⚠️  Error calculando seller_return_rate para semana {week_key}: {e}")
                    import traceback
                    traceback.print_exc()
                    value = 0.0
            elif metric == 'revenue_by_seller':
                # Para este KPI, retornar el total facturado por vendedores en esta semana
                week_orders_with_seller = [o for o in week_orders if o.seller_id]
                stats = calculate_kpis_for_orders(week_orders_with_seller)
                value = stats['total_revenue']
            else:
                return jsonify({"error": f"Métrica '{metric}' no reconocida"}), 400
            
            result.append({
                'week_start': week_key,
                'value': round(value, 2) if isinstance(value, float) else value
            })
        
        # Ordenar por semana (más antigua primero)
        result.sort(key=lambda x: x['week_start'])
        
        return jsonify({
            'metric': metric,
            'weeks': result
        })
    
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"❌ Error obteniendo KPI por semana: {e}")
        print(error_trace)
        return jsonify({
            "error": f"Error obteniendo KPI por semana: {str(e)}",
            "details": error_trace if request.args.get("debug") == "true" else None
        }), 500


@bp.route("/best-products", methods=["GET"])
def get_best_products():
    """
    Obtiene los mejores productos ordenados por monto facturado.
    Puede filtrarse por última semana o histórico.
    """
    try:
        # Obtener parámetro de filtro (last_week o historical)
        filter_type = request.args.get("filter", "historical")  # Por defecto histórico
        
        # Calcular rango de última semana si es necesario (desde el 1 de marzo)
        orders_query = Order.query.filter(
            Order.status.in_(['completed', 'emitted']),
            Order.created_at >= KPI_START_DATE
        )
        
        if filter_type == "last_week":
            # Usar la última semana completada
            last_week_start_date, last_week_end_date = get_last_completed_week()
            last_week_start = datetime.combine(last_week_start_date, datetime.min.time())
            last_week_end = datetime.combine(last_week_end_date, datetime.max.time())
            
            # Asegurar que el inicio no sea anterior al 1 de marzo
            effective_start = max(last_week_start, KPI_START_DATE)
            orders_query = orders_query.filter(
                Order.created_at >= effective_start,
                Order.created_at <= last_week_end
            )
        
        orders = orders_query.all()
        
        # Agrupar productos por monto facturado
        products_revenue = {}  # {product_id: {'name': ..., 'revenue': ..., 'qty': ..., 'orders': set()}}
        
        for order in orders:
            order_data = calculate_order_total(order)
            if order_data['order_total'] <= 0:
                continue
            
            for item in order.items:
                product_id = item.product_id
                if not product_id:
                    continue
                
                # Usar charged_qty si existe
                if item.charged_qty is not None:
                    qty_to_charge = item.charged_qty
                else:
                    qty_to_charge = item.qty
                
                # Precio unitario
                unit_price = item.unit_price
                if not unit_price and item.product:
                    unit_price = item.product.sale_price or 0
                
                # Monto facturado de este item
                item_revenue = round(qty_to_charge * (unit_price or 0))
                
                if product_id not in products_revenue:
                    product = item.product
                    # Determinar unidad: usar charged_unit si existe, sino unit, sino la del producto
                    unit_to_use = item.charged_unit if item.charged_unit else (item.unit if item.unit else (product.unit if product else 'kg'))
                    products_revenue[product_id] = {
                        'product_id': product_id,
                        'product_name': product.name if product else 'Producto desconocido',
                        'unit': unit_to_use,
                        'revenue': 0,
                        'qty': 0,
                        'orders': set()
                    }
                
                products_revenue[product_id]['revenue'] += item_revenue
                products_revenue[product_id]['qty'] += qty_to_charge
                products_revenue[product_id]['orders'].add(order.id)
                # Actualizar unidad si es necesario (usar la más común o la del producto base)
                if item.product:
                    products_revenue[product_id]['unit'] = item.product.unit
        
        # Convertir a lista y ordenar por monto facturado
        products_list = []
        for product_id, data in products_revenue.items():
            products_list.append({
                'product_id': data['product_id'],
                'product_name': data['product_name'],
                'unit': data.get('unit', 'kg'),  # Unidad del producto
                'revenue': data['revenue'],
                'qty': round(data['qty'], 2),
                'orders_count': len(data['orders'])
            })
        
        # Ordenar por monto facturado (mayor a menor)
        products_list.sort(key=lambda x: x['revenue'], reverse=True)
        
        return jsonify({
            'products': products_list,
            'filter': filter_type,
            'count': len(products_list)
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Error obteniendo mejores productos: {str(e)}"}), 500


def calculate_customer_return_rate_for_week(week_key, all_orders):
    """
    Calcula el porcentaje de clientes que retornaron para una semana específica.
    
    FÓRMULA:
    - Clientes de referencia: Clientes únicos que pidieron hace 1 o 2 semanas (semana N-1 o N-2)
    - Clientes que retornaron: Clientes de referencia que volvieron a pedir en esta semana (N) o la anterior (N-1)
    - Porcentaje = (Clientes que retornaron / Clientes de referencia) * 100
    
    Las primeras dos semanas se ignoran (retornan 0).
    """
    try:
        if not week_key or not all_orders:
            return 0.0
            
        # Convertir week_key a datetime
        try:
            week_start_dt = datetime.fromisoformat(week_key)
            week_start_date = week_start_dt.date()
        except (ValueError, AttributeError):
            return 0.0
        
        # Agrupar todos los pedidos por semana
        orders_by_week = {}
        for order in all_orders:
            if not order.created_at:
                continue
            try:
                order_week_start = get_week_start(order.created_at)
                if not order_week_start:
                    continue
                week_key_order = order_week_start.isoformat() if hasattr(order_week_start, 'isoformat') else str(order_week_start)
                if not week_key_order:
                    continue
                if week_key_order not in orders_by_week:
                    orders_by_week[week_key_order] = []
                orders_by_week[week_key_order].append(order)
            except Exception as e:
                print(f"⚠️  Error procesando pedido {order.id} para customer_return_rate: {e}")
                continue
        
        # Obtener todas las semanas ordenadas
        sorted_weeks = sorted(orders_by_week.keys())
        if week_key not in sorted_weeks:
            return None  # Retornar None en lugar de 0 para que no se incluya en el promedio
        
        current_week_index = sorted_weeks.index(week_key)
        
        # Las primeras dos semanas se ignoran (índices 0 y 1) - retornar None
        if current_week_index < 2:
            return None  # Retornar None para que no se incluya en el promedio
        
        # Semana actual
        current_week_start = week_start_date
        
        # Semanas de referencia: clientes que pidieron hace 1 o 2 semanas (N-1 o N-2)
        week_minus_1_start = current_week_start - timedelta(days=7)
        week_minus_2_start = current_week_start - timedelta(days=14)
        week_minus_1_key = week_minus_1_start.isoformat()
        week_minus_2_key = week_minus_2_start.isoformat()
        
        # Semanas de retorno: esta semana (N) o la anterior (N-1)
        previous_week_start = current_week_start - timedelta(days=7)
        previous_week_key = previous_week_start.isoformat()
        
        # Obtener clientes únicos que pidieron en las semanas de referencia (N-1 o N-2)
        customers_in_reference = set()
        for ref_week_key in [week_minus_1_key, week_minus_2_key]:
            if ref_week_key in orders_by_week:
                for order in orders_by_week[ref_week_key]:
                    try:
                        if hasattr(order, 'items') and order.items:
                            for item in order.items:
                                if hasattr(item, 'customer_id') and item.customer_id:
                                    customers_in_reference.add(item.customer_id)
                    except Exception as e:
                        print(f"⚠️  Error procesando items del pedido {order.id}: {e}")
                        continue
        
        if not customers_in_reference:
            print(f"📊 Semana {week_key}: No hay clientes de referencia (buscó en {week_minus_1_key} y {week_minus_2_key})")
            return 0.0
        
        # Obtener clientes que pidieron en la semana actual (N) o anterior (N-1)
        customers_returned = set()
        for ret_week_key in [week_key, previous_week_key]:
            if ret_week_key in orders_by_week:
                for order in orders_by_week[ret_week_key]:
                    try:
                        if hasattr(order, 'items') and order.items:
                            for item in order.items:
                                if hasattr(item, 'customer_id') and item.customer_id and item.customer_id in customers_in_reference:
                                    customers_returned.add(item.customer_id)
                    except Exception as e:
                        print(f"⚠️  Error procesando items del pedido {order.id}: {e}")
                        continue
        
        # Calcular porcentaje
        if len(customers_in_reference) == 0:
            return 0.0
        
        percentage = (len(customers_returned) / len(customers_in_reference)) * 100
        
        # Debug: imprimir información útil
        print(f"📊 Semana {week_key}:")
        print(f"   - Clientes de referencia (pidieron en {week_minus_1_key} o {week_minus_2_key}): {len(customers_in_reference)}")
        print(f"   - Clientes que retornaron (pidieron en {week_key} o {previous_week_key}): {len(customers_returned)}")
        print(f"   - Porcentaje: {percentage:.2f}%")
        
        return percentage
        
    except Exception as e:
        print(f"⚠️  Error calculando customer_return_rate para semana {week_key}: {e}")
        import traceback
        traceback.print_exc()
        return 0.0


def calculate_seller_return_rate_for_week(week_key, all_orders):
    """
    Calcula el porcentaje de vendedores que retornaron para una semana específica.
    Un vendedor retorna si:
    - Tuvo pedidos hace 1 o 2 semanas
    - Y volvió a tener al menos un pedido en esta semana o la anterior
    Las primeras dos semanas se ignoran (retornan 0).
    """
    try:
        if not week_key or not all_orders:
            return 0.0
            
        # Convertir week_key a datetime
        try:
            week_start_dt = datetime.fromisoformat(week_key)
            week_start_date = week_start_dt.date()
        except (ValueError, AttributeError):
            return 0.0
        
        # Agrupar todos los pedidos por semana
        orders_by_week = {}
        for order in all_orders:
            if not order.created_at:
                continue
            try:
                order_week_start = get_week_start(order.created_at)
                if not order_week_start:
                    continue
                week_key_order = order_week_start.isoformat() if hasattr(order_week_start, 'isoformat') else str(order_week_start)
                if not week_key_order:
                    continue
                if week_key_order not in orders_by_week:
                    orders_by_week[week_key_order] = []
                orders_by_week[week_key_order].append(order)
            except Exception as e:
                print(f"⚠️  Error procesando pedido {order.id} para seller_return_rate: {e}")
                continue
        
        # Obtener todas las semanas ordenadas
        sorted_weeks = sorted(orders_by_week.keys())
        if week_key not in sorted_weeks:
            return None  # Retornar None en lugar de 0 para que no se incluya en el promedio
        
        current_week_index = sorted_weeks.index(week_key)
        
        # Las primeras dos semanas se ignoran (índices 0 y 1) - retornar None
        if current_week_index < 2:
            return None  # Retornar None para que no se incluya en el promedio
        
        # Semana actual y anterior
        current_week_start = week_start_date
        previous_week_start = current_week_start - timedelta(days=7)
        
        # Semanas de referencia (1 y 2 semanas atrás)
        week_minus_1_start = current_week_start - timedelta(days=7)
        week_minus_2_start = current_week_start - timedelta(days=14)
        
        # Semana actual
        current_week_start = week_start_date
        
        # Semanas de referencia: vendedores que tuvieron pedidos hace 1 o 2 semanas (N-1 o N-2)
        week_minus_1_start = current_week_start - timedelta(days=7)
        week_minus_2_start = current_week_start - timedelta(days=14)
        week_minus_1_key = week_minus_1_start.isoformat()
        week_minus_2_key = week_minus_2_start.isoformat()
        
        # Semanas de retorno: esta semana (N) o la anterior (N-1)
        previous_week_start = current_week_start - timedelta(days=7)
        previous_week_key = previous_week_start.isoformat()
        
        # Obtener vendedores únicos que tuvieron pedidos en las semanas de referencia (N-1 o N-2)
        sellers_in_reference = set()
        for ref_week_key in [week_minus_1_key, week_minus_2_key]:
            if ref_week_key in orders_by_week:
                for order in orders_by_week[ref_week_key]:
                    try:
                        if hasattr(order, 'seller_id') and order.seller_id:
                            sellers_in_reference.add(order.seller_id)
                    except Exception as e:
                        print(f"⚠️  Error procesando seller_id del pedido {order.id}: {e}")
                        continue
        
        if not sellers_in_reference:
            print(f"📊 Semana {week_key}: No hay vendedores de referencia (buscó en {week_minus_1_key} y {week_minus_2_key})")
            return 0.0
        
        # Obtener vendedores que tuvieron pedidos en la semana actual (N) o anterior (N-1)
        sellers_returned = set()
        for ret_week_key in [week_key, previous_week_key]:
            if ret_week_key in orders_by_week:
                for order in orders_by_week[ret_week_key]:
                    try:
                        if hasattr(order, 'seller_id') and order.seller_id and order.seller_id in sellers_in_reference:
                            sellers_returned.add(order.seller_id)
                    except Exception as e:
                        print(f"⚠️  Error procesando seller_id del pedido {order.id}: {e}")
                        continue
        
        # Calcular porcentaje
        if len(sellers_in_reference) == 0:
            return 0.0
        
        percentage = (len(sellers_returned) / len(sellers_in_reference)) * 100
        
        # Debug: imprimir información útil
        print(f"📊 Semana {week_key} (vendedores):")
        print(f"   - Vendedores de referencia (tuvieron pedidos en {week_minus_1_key} o {week_minus_2_key}): {len(sellers_in_reference)}")
        print(f"   - Vendedores que retornaron (tuvieron pedidos en {week_key} o {previous_week_key}): {len(sellers_returned)}")
        print(f"   - Porcentaje: {percentage:.2f}%")
        
        return percentage
        
    except Exception as e:
        print(f"⚠️  Error calculando seller_return_rate para semana {week_key}: {e}")
        import traceback
        traceback.print_exc()
        return 0.0


@bp.route("/revenue-by-seller", methods=["GET"])
def get_revenue_by_seller():
    """
    Obtiene el monto facturado por vendedores.
    Puede filtrarse por última semana o histórico.
    Permite filtrar por mejores x o peores x vendedores.
    """
    try:
        # Obtener parámetros
        filter_type = request.args.get("filter", "historical")  # last_week o historical
        filter_mode = request.args.get("filter_mode", "all")  # all, top, bottom
        filter_count = int(request.args.get("filter_count", "10"))  # cantidad de vendedores
        
        # Calcular rango de última semana si es necesario (desde el 1 de marzo)
        orders_query = Order.query.filter(
            Order.status.in_(['completed', 'emitted']),
            Order.created_at >= KPI_START_DATE
        )
        
        if filter_type == "last_week":
            last_week_start_date, last_week_end_date = get_last_completed_week()
            last_week_start = datetime.combine(last_week_start_date, datetime.min.time())
            last_week_end = datetime.combine(last_week_end_date, datetime.max.time())
            
            # Asegurar que el inicio no sea anterior al 1 de marzo
            effective_start = max(last_week_start, KPI_START_DATE)
            orders_query = orders_query.filter(
                Order.created_at >= effective_start,
                Order.created_at <= last_week_end
            )
        
        orders = orders_query.all()
        
        # Agrupar por vendedor
        sellers_revenue = {}  # {seller_id: {'name': ..., 'revenue': ...}}
        
        for order in orders:
            # Solo considerar pedidos con vendedor
            if not order.seller_id:
                continue
            
            order_data = calculate_order_total(order)
            if order_data['order_total'] <= 0:
                continue
            
            seller_id = order.seller_id
            if seller_id not in sellers_revenue:
                seller = order.seller
                sellers_revenue[seller_id] = {
                    'seller_id': seller_id,
                    'seller_name': seller.name if seller else f'Vendedor #{seller_id}',
                    'revenue': 0
                }
            
            sellers_revenue[seller_id]['revenue'] += order_data['order_total']
        
        # Convertir a lista
        sellers_list = list(sellers_revenue.values())
        
        # Ordenar por revenue (mayor a menor)
        sellers_list.sort(key=lambda x: x['revenue'], reverse=True)
        
        # Aplicar filtro si es necesario
        if filter_mode == "top" and filter_count > 0:
            sellers_list = sellers_list[:filter_count]
        elif filter_mode == "bottom" and filter_count > 0:
            sellers_list = sellers_list[-filter_count:]
            sellers_list.reverse()  # Mantener orden de menor a mayor
        
        # Calcular total
        total_revenue = sum(s['revenue'] for s in sellers_list)
        
        return jsonify({
            'sellers': sellers_list,
            'total_revenue': round(total_revenue),
            'filter': filter_type,
            'filter_mode': filter_mode,
            'filter_count': filter_count,
            'count': len(sellers_list)
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Error obteniendo revenue por vendedor: {str(e)}"}), 500

