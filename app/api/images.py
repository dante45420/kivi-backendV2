"""
API: Imágenes
Sirve imágenes desde Google Cloud Storage
"""
import os
from flask import Blueprint, Response
from ..utils.cloud_storage import get_file_content

bp = Blueprint("images", __name__)


@bp.route("/<path:image_path>", methods=["GET"])
def serve_image(image_path):
    """
    Sirve una imagen desde Google Cloud Storage
    
    Args:
        image_path: Path de la imagen (ej: products/17/filename.png)
        
    Returns:
        Response: Imagen con content-type apropiado
    """
    try:
        # El path viene como: products/17/filename.png
        # Construir el path completo para Cloud Storage
        bucket_name = os.getenv("GCS_BUCKET_NAME")
        if bucket_name:
            gcs_path = f"gs://{bucket_name}/{image_path}"
        else:
            # Fallback: usar el path directamente
            gcs_path = image_path
        
        content, content_type = get_file_content(gcs_path)
        
        if content is None:
            return Response("Imagen no encontrada", status=404, mimetype="text/plain")
        
        # Agregar headers de caché para mejorar rendimiento
        response = Response(content, mimetype=content_type)
        response.headers['Cache-Control'] = 'public, max-age=31536000'  # 1 año
        return response
    
    except Exception as e:
        print(f"❌ Error sirviendo imagen: {e}")
        import traceback
        traceback.print_exc()
        return Response(f"Error: {str(e)}", status=500, mimetype="text/plain")

