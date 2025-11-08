"""
API: Categorías
CRUD completo de categorías
"""
from flask import Blueprint, jsonify, request
from ..models import Category
from ..db import db

bp = Blueprint("categories", __name__)


@bp.route("", methods=["GET"])
def get_categories():
    """Obtiene todas las categorías activas ordenadas"""
    categories = Category.query.filter_by(active=True).order_by(Category.order).all()
    return jsonify([c.to_dict() for c in categories])


@bp.route("", methods=["POST"])
def create_category():
    """Crea una nueva categoría"""
    data = request.json
    
    category = Category(
        name=data.get("name"),
        emoji=data.get("emoji", "📦"),
        order=data.get("order", 0)
    )
    
    db.session.add(category)
    db.session.commit()
    
    return jsonify(category.to_dict()), 201


@bp.route("/<int:id>", methods=["PUT"])
def update_category(id):
    """Actualiza una categoría"""
    category = Category.query.get_or_404(id)
    data = request.json
    
    category.name = data.get("name", category.name)
    category.emoji = data.get("emoji", category.emoji)
    category.order = data.get("order", category.order)
    
    db.session.commit()
    
    return jsonify(category.to_dict())


@bp.route("/<int:id>", methods=["DELETE"])
def delete_category(id):
    """Elimina (desactiva) una categoría"""
    category = Category.query.get_or_404(id)
    category.active = False
    db.session.commit()
    
    return jsonify({"message": "Categoría eliminada"})

