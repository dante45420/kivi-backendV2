"""
API: Productos
CRUD completo + manejo de imágenes
"""
from flask import Blueprint, request, jsonify
from ..db import db
from ..models import Product, PriceHistory
from ..utils.cloud_storage import upload_file, delete_file

bp = Blueprint("products", __name__)


@bp.route("", methods=["GET"])
def get_products():
    """Lista todos los productos"""
    active_only = request.args.get("active", "true").lower() == "true"
    category_id = request.args.get("category_id")
    
    query = Product.query
    
    if active_only:
        query = query.filter_by(active=True)
    
    if category_id:
        query = query.filter_by(category_id=int(category_id))
    
    products = query.order_by(Product.name).all()
    return jsonify([p.to_dict() for p in products])


@bp.route("/suggest", methods=["GET"])
def suggest_products():
    """Sugiere productos basándose en búsqueda fuzzy"""
    from ..utils.text_match import similarity_score
    
    query = request.args.get("q", "").strip()
    
    if not query or len(query) < 2:
        return jsonify([])
    
    # Buscar en todos los productos activos
    products = Product.query.filter_by(active=True).all()
    suggestions = []
    
    for product in products:
        score = similarity_score(query, product.name)
        if score >= 60:  # Umbral más bajo para sugerencias
            suggestions.append({
                "id": product.id,
                "name": product.name,
                "score": score,
                "category_id": product.category_id,
                "sale_price": product.sale_price,
                "unit": product.unit
            })
    
    # Ordenar por score descendente
    suggestions.sort(key=lambda x: x["score"], reverse=True)
    
    return jsonify(suggestions[:10])  # Top 10


@bp.route("/<int:id>", methods=["GET"])
def get_product(id):
    """Obtiene un producto por ID"""
    product = Product.query.get_or_404(id)
    return jsonify(product.to_dict())


@bp.route("", methods=["POST"])
def create_product():
    """Crea un nuevo producto"""
    data = request.json
    
    product = Product(
        name=data["name"],
        category_id=data["category_id"],
        unit=data.get("unit", "kg"),
        sale_price=data.get("sale_price"),
        purchase_price=data.get("purchase_price"),
        notes=data.get("notes"),
    )
    
    db.session.add(product)
    db.session.commit()
    
    return jsonify(product.to_dict()), 201


@bp.route("/<int:id>", methods=["PUT"])
def update_product(id):
    """Actualiza un producto"""
    product = Product.query.get_or_404(id)
    data = request.json
    
    # Guardar precio de compra anterior si cambió
    old_purchase_price = product.purchase_price
    new_purchase_price = data.get("purchase_price")
    
    if new_purchase_price and new_purchase_price != old_purchase_price:
        # Registrar en historial
        history = PriceHistory(
            product_id=product.id,
            purchase_price=new_purchase_price,
            notes=data.get("price_change_notes")
        )
        db.session.add(history)
    
    # Actualizar campos
    product.name = data.get("name", product.name)
    product.category_id = data.get("category_id", product.category_id)
    product.unit = data.get("unit", product.unit)
    product.sale_price = data.get("sale_price", product.sale_price)
    product.purchase_price = new_purchase_price or product.purchase_price
    product.notes = data.get("notes", product.notes)
    product.active = data.get("active", product.active)
    
    db.session.commit()
    
    return jsonify(product.to_dict())


@bp.route("/<int:id>", methods=["DELETE"])
def delete_product(id):
    """Elimina un producto (soft delete)"""
    product = Product.query.get_or_404(id)
    product.active = False
    db.session.commit()
    
    return jsonify({"message": "Producto desactivado"})


@bp.route("/<int:id>/photo", methods=["POST"])
def upload_photo(id):
    """Sube una foto para el producto (Google Cloud o local)"""
    product = Product.query.get_or_404(id)
    
    if "file" not in request.files:
        return jsonify({"error": "No se envió archivo"}), 400
    
    file = request.files["file"]
    
    if file.filename == "":
        return jsonify({"error": "Archivo vacío"}), 400
    
    try:
        from ..utils.cloud_storage import upload_file, delete_file
        import os
        import uuid
        from werkzeug.utils import secure_filename
        
        # Eliminar foto anterior si existe
        if product.photo_url:
            try:
                if 'storage.googleapis.com' in product.photo_url:
                    delete_file(product.photo_url)
                elif product.photo_url.startswith('/uploads/'):
                    # Eliminar archivo local
                    local_path = os.path.join(os.path.dirname(__file__), '..', '..', product.photo_url.lstrip('/'))
                    if os.path.exists(local_path):
                        os.remove(local_path)
            except Exception as e:
                print(f"Error deleting old photo: {e}")
        
        # Intentar Google Cloud Storage primero
        if os.getenv("GCS_BUCKET_NAME"):
            photo_url = upload_file(file, folder=f"products/{product.id}")
            if photo_url:
                product.photo_url = photo_url
                db.session.commit()
                return jsonify({"photo_url": photo_url})
        
        # Fallback: Guardar localmente
        upload_folder = os.path.join(os.path.dirname(__file__), '../../uploads/products')
        os.makedirs(upload_folder, exist_ok=True)
        
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4()}_{filename}"
        filepath = os.path.join(upload_folder, unique_filename)
        
        file.save(filepath)
        
        photo_url = f"/uploads/products/{unique_filename}"
        product.photo_url = photo_url
        db.session.commit()
        
        return jsonify({"photo_url": photo_url})
        
    except Exception as e:
        print(f"Error uploading photo: {e}")
        return jsonify({"error": f"Error al subir archivo: {str(e)}"}), 500


@bp.route("/<int:id>/photo", methods=["DELETE"])
def delete_photo(id):
    """Elimina la foto del producto"""
    product = Product.query.get_or_404(id)
    
    if not product.photo_url:
        return jsonify({"error": "No hay foto para eliminar"}), 400
    
    try:
        from ..utils.cloud_storage import delete_file
        import os
        
        if 'storage.googleapis.com' in product.photo_url:
            delete_file(product.photo_url)
        elif product.photo_url.startswith('/uploads/'):
            # Eliminar archivo local
            local_path = os.path.join(os.path.dirname(__file__), '..', '..', product.photo_url.lstrip('/'))
            if os.path.exists(local_path):
                os.remove(local_path)
        
        product.photo_url = None
        db.session.commit()
        
        return jsonify({"message": "Foto eliminada"})
    except Exception as e:
        print(f"Error deleting photo: {e}")
        return jsonify({"error": str(e)}), 500


@bp.route("/<int:id>/price-history", methods=["GET"])
def get_price_history(id):
    """Obtiene el historial de precios de compra"""
    product = Product.query.get_or_404(id)
    history = PriceHistory.query.filter_by(product_id=id).order_by(PriceHistory.date.desc()).all()
    
    return jsonify([h.to_dict() for h in history])

