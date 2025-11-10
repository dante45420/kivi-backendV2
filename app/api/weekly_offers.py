"""
API: Ofertas semanales
Gestión y programación de ofertas
"""
from flask import Blueprint, request, jsonify
from datetime import datetime
from ..db import db
from ..models import WeeklyOffer, Product

bp = Blueprint("weekly_offers", __name__)


@bp.route("", methods=["GET"])
def get_weekly_offers():
    """Lista ofertas semanales"""
    active_only = request.args.get("active", "true").lower() == "true"
    current = request.args.get("current", "false").lower() == "true"
    
    query = WeeklyOffer.query
    
    if active_only:
        query = query.filter_by(active=True)
    
    if current:
        now = datetime.utcnow()
        query = query.filter(
            WeeklyOffer.start_date <= now,
            WeeklyOffer.end_date >= now
        )
    
    offers = query.order_by(WeeklyOffer.start_date.desc()).all()
    return jsonify([o.to_dict() for o in offers])


@bp.route("", methods=["POST"])
def create_weekly_offer():
    """Crea una oferta semanal"""
    data = request.json
    
    try:
        # Manejar fechas con formato ISO (remover Z)
        start_date_str = data["start_date"].replace('Z', '+00:00') if 'Z' in data["start_date"] else data["start_date"]
        end_date_str = data["end_date"].replace('Z', '+00:00') if 'Z' in data["end_date"] else data["end_date"]
        
    offer = WeeklyOffer(
        product_id=data["product_id"],
        special_price=round(data["special_price"]),
            start_date=datetime.fromisoformat(start_date_str),
            end_date=datetime.fromisoformat(end_date_str),
    )
    
    db.session.add(offer)
    db.session.commit()
    
    return jsonify(offer.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        print(f"Error creating weekly offer: {e}")
        return jsonify({"error": str(e)}), 500


@bp.route("/<int:id>", methods=["PUT"])
def update_weekly_offer(id):
    """Actualiza una oferta semanal"""
    offer = WeeklyOffer.query.get_or_404(id)
    data = request.json
    
    if "special_price" in data:
        offer.special_price = round(data["special_price"])
    if "start_date" in data:
        offer.start_date = datetime.fromisoformat(data["start_date"])
    if "end_date" in data:
        offer.end_date = datetime.fromisoformat(data["end_date"])
    if "active" in data:
        offer.active = data["active"]
    
    db.session.commit()
    
    return jsonify(offer.to_dict())


@bp.route("/<int:id>", methods=["DELETE"])
def delete_weekly_offer(id):
    """Elimina una oferta semanal"""
    offer = WeeklyOffer.query.get_or_404(id)
    
    db.session.delete(offer)
    db.session.commit()
    
    return jsonify({"message": "Oferta eliminada"})


@bp.route("/schedule", methods=["POST"])
def schedule_offers():
    """Programa ofertas para próxima semana"""
    data = request.json
    
    start_date = datetime.fromisoformat(data["start_date"])
    end_date = datetime.fromisoformat(data["end_date"])
    products = data.get("products", [])
    
    created = []
    
    for product_data in products:
        offer = WeeklyOffer(
            product_id=product_data["product_id"],
            special_price=round(product_data["special_price"]),
            start_date=start_date,
            end_date=end_date,
        )
        db.session.add(offer)
        created.append(offer)
    
    db.session.commit()
    
    return jsonify({
        "message": f"Se programaron {len(created)} ofertas",
        "offers": [o.to_dict() for o in created]
    }), 201

