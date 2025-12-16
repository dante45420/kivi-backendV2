"""
API: Green Market 🌱
Tips aleatorios y chat con IA
"""
from flask import Blueprint, request, jsonify
from ..models import KiviTip
from ..services.kivi_chat import chat_with_kivi
import random

bp = Blueprint("kivi", __name__)


@bp.route("/tip/random", methods=["GET"])
def get_random_tip():
    """Obtiene un tip aleatorio de Green Market"""
    category = request.args.get("category")
    
    query = KiviTip.query.filter_by(active=True)
    
    if category:
        query = query.filter_by(category=category)
    
    tips = query.all()
    
    if not tips:
        return jsonify({
            "message": "¡Hola! Aquí estoy para ayudarte 🌱",
            "category": "default",
            "emoji": "🌱"
        })
    
    tip = random.choice(tips)
    return jsonify(tip.to_dict())


@bp.route("/tips", methods=["GET"])
def get_tips():
    """Lista todos los tips"""
    category = request.args.get("category")
    
    query = KiviTip.query.filter_by(active=True)
    
    if category:
        query = query.filter_by(category=category)
    
    tips = query.all()
    return jsonify([t.to_dict() for t in tips])


@bp.route("/chat", methods=["POST"])
def chat():
    """Chat con Green Market usando IA"""
    data = request.json
    message = data.get("message", "")
    context = data.get("context")
    
    if not message:
        return jsonify({"error": "No se envió mensaje"}), 400
    
    try:
        response = chat_with_kivi(message, context)
        return jsonify({"response": response})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/tips", methods=["POST"])
def create_tip():
    """Crea un nuevo tip de Green Market"""
    from ..db import db
    
    data = request.json
    
    tip = KiviTip(
        category=data.get("category", "platform_usage"),
        message=data["message"],
        emoji=data.get("emoji"),
        active=data.get("active", True)
    )
    
    db.session.add(tip)
    db.session.commit()
    
    return jsonify(tip.to_dict()), 201


@bp.route("/tips/<int:id>", methods=["PUT"])
def update_tip(id):
    """Actualiza un tip de Kivi"""
    from ..db import db
    
    tip = KiviTip.query.get_or_404(id)
    data = request.json
    
    if "category" in data:
        tip.category = data["category"]
    if "message" in data:
        tip.message = data["message"]
    if "emoji" in data:
        tip.emoji = data["emoji"]
    if "active" in data:
        tip.active = data["active"]
    
    db.session.commit()
    
    return jsonify(tip.to_dict())


@bp.route("/tips/<int:id>", methods=["DELETE"])
def delete_tip(id):
    """Elimina un tip de Green Market"""
    from ..db import db
    
    tip = KiviTip.query.get_or_404(id)
    
    db.session.delete(tip)
    db.session.commit()
    
    return jsonify({"message": "Tip eliminado"})

