"""
API: Weekly Costs / Costos Semanales
Gestión de costos adicionales por semana
"""
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify
from ..db import db
from ..models import WeeklyCost

bp = Blueprint("weekly_costs", __name__, url_prefix="/api/weekly-costs")


def get_week_start(date=None):
    """Obtiene el lunes de la semana para una fecha dada"""
    if date is None:
        date = datetime.utcnow().date()
    elif isinstance(date, str):
        date = datetime.fromisoformat(date).date()
    
    # Calcular días desde el lunes (0 = lunes, 6 = domingo)
    days_since_monday = date.weekday()
    week_start = date - timedelta(days=days_since_monday)
    return week_start


@bp.route("", methods=["POST"])
def create_weekly_cost():
    """Crear un nuevo costo semanal"""
    try:
        data = request.json
        
        # Obtener semana (si no se proporciona, usar la semana actual)
        week_date = data.get("week_start")
        if week_date:
            week_start = get_week_start(week_date)
        else:
            week_start = get_week_start()
        
        category = data.get("category")
        if not category:
            return jsonify({"error": "category es requerido"}), 400
        
        amount = data.get("amount")
        if not amount:
            return jsonify({"error": "amount es requerido"}), 400
        
        amount = int(amount)
        if amount <= 0:
            return jsonify({"error": "amount debe ser mayor a 0"}), 400
        
        # Verificar si ya existe un costo para esta semana y categoría
        existing = WeeklyCost.query.filter_by(
            week_start=week_start,
            category=category
        ).first()
        
        if existing:
            # Si existe, sumar el monto y aumentar el contador
            existing.amount += amount
            existing.count += 1
            if data.get("description"):
                # Agregar descripción si se proporciona
                if existing.description:
                    existing.description += f"\n{data.get('description')}"
                else:
                    existing.description = data.get("description")
            existing.updated_at = datetime.utcnow()
            db.session.commit()
            
            return jsonify({
                "message": "Costo actualizado exitosamente",
                "cost": existing.to_dict()
            }), 200
        else:
            # Crear nuevo costo
            cost = WeeklyCost(
                week_start=week_start,
                category=category,
                amount=amount,
                count=1,
                description=data.get("description")
            )
            db.session.add(cost)
            db.session.commit()
            
            return jsonify({
                "message": "Costo creado exitosamente",
                "cost": cost.to_dict()
            }), 201
    
    except Exception as e:
        db.session.rollback()
        import traceback
        error_trace = traceback.format_exc()
        print(f"❌ Error creando costo semanal: {e}")
        print(error_trace)
        return jsonify({
            "error": f"Error al crear costo: {str(e)}",
            "details": error_trace if request.args.get("debug") == "true" else None
        }), 500


@bp.route("", methods=["GET"])
def get_weekly_costs():
    """Obtener costos semanales, opcionalmente filtrados por semana"""
    try:
        week_start_param = request.args.get("week_start")
        
        query = WeeklyCost.query
        
        if week_start_param:
            week_start = get_week_start(week_start_param)
            query = query.filter_by(week_start=week_start)
        
        costs = query.order_by(WeeklyCost.week_start.desc(), WeeklyCost.category).all()
        
        return jsonify([cost.to_dict() for cost in costs])
    
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"❌ Error obteniendo costos semanales: {e}")
        print(error_trace)
        return jsonify({
            "error": f"Error al obtener costos: {str(e)}"
        }), 500


@bp.route("/by-week", methods=["GET"])
def get_costs_by_week():
    """Obtener costos agrupados por semana"""
    try:
        # Obtener todas las semanas únicas
        all_costs = WeeklyCost.query.order_by(WeeklyCost.week_start.desc()).all()
        
        # Agrupar por semana
        costs_by_week = {}
        for cost in all_costs:
            week_key = cost.week_start.isoformat()
            if week_key not in costs_by_week:
                costs_by_week[week_key] = {
                    "week_start": cost.week_start.isoformat(),
                    "categories": {}
                }
            
            if cost.category not in costs_by_week[week_key]["categories"]:
                costs_by_week[week_key]["categories"][cost.category] = {
                    "amount": 0,
                    "count": 0
                }
            
            costs_by_week[week_key]["categories"][cost.category]["amount"] += cost.amount
            costs_by_week[week_key]["categories"][cost.category]["count"] += cost.count
        
        # Convertir a lista y calcular totales
        result = []
        for week_key, week_data in costs_by_week.items():
            total_amount = sum(cat["amount"] for cat in week_data["categories"].values())
            result.append({
                "week_start": week_data["week_start"],
                "categories": week_data["categories"],
                "total_amount": total_amount
            })
        
        # Ordenar por semana (más antigua primero)
        result.sort(key=lambda x: x["week_start"])
        
        return jsonify(result)
    
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"❌ Error obteniendo costos por semana: {e}")
        print(error_trace)
        return jsonify({
            "error": f"Error al obtener costos por semana: {str(e)}"
        }), 500


@bp.route("/<int:cost_id>", methods=["PUT"])
def update_weekly_cost(cost_id):
    """Actualizar un costo semanal"""
    try:
        cost = WeeklyCost.query.get_or_404(cost_id)
        data = request.json
        
        if "amount" in data:
            cost.amount = int(data["amount"])
        if "category" in data:
            cost.category = data["category"]
        if "description" in data:
            cost.description = data["description"]
        if "week_start" in data:
            cost.week_start = get_week_start(data["week_start"])
        
        cost.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            "message": "Costo actualizado exitosamente",
            "cost": cost.to_dict()
        }), 200
    
    except Exception as e:
        db.session.rollback()
        import traceback
        error_trace = traceback.format_exc()
        print(f"❌ Error actualizando costo: {e}")
        print(error_trace)
        return jsonify({
            "error": f"Error al actualizar costo: {str(e)}"
        }), 500


@bp.route("/<int:cost_id>", methods=["DELETE"])
def delete_weekly_cost(cost_id):
    """Eliminar un costo semanal"""
    try:
        cost = WeeklyCost.query.get_or_404(cost_id)
        db.session.delete(cost)
        db.session.commit()
        
        return jsonify({"message": "Costo eliminado exitosamente"}), 200
    
    except Exception as e:
        db.session.rollback()
        import traceback
        error_trace = traceback.format_exc()
        print(f"❌ Error eliminando costo: {e}")
        print(error_trace)
        return jsonify({
            "error": f"Error al eliminar costo: {str(e)}"
        }), 500

