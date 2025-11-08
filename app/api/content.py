"""
API: Contenido IA
Generación de posts, stories y reels
"""
from flask import Blueprint, request, jsonify
from ..services.content_generator import generate_content, regenerate_content

bp = Blueprint("content", __name__)


@bp.route("/generate", methods=["POST"])
def generate():
    """Genera contenido nuevo con IA"""
    data = request.json
    
    template_type = data.get("template_type", "story_video")
    product_ids = data.get("product_ids", [])
    custom_prompt = data.get("custom_prompt")
    
    try:
        result = generate_content(template_type, product_ids, custom_prompt)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/<int:content_id>/approve", methods=["PUT"])
def approve(content_id):
    """Aprueba contenido generado"""
    # TODO: Implementar lógica de aprobación
    return jsonify({"message": "Contenido aprobado", "content_id": content_id})


@bp.route("/<int:content_id>/reject", methods=["PUT"])
def reject(content_id):
    """Rechaza y regenera contenido"""
    data = request.json
    feedback = data.get("feedback", "")
    
    try:
        result = regenerate_content(content_id, feedback)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

