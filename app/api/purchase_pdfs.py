"""
API: Purchase PDFs
Gestión de PDFs de compras guardados
"""
import os
from datetime import datetime
from flask import Blueprint, request, jsonify, send_file
from ..db import db
from ..utils.cloud_storage import get_storage_client, get_file_content, upload_file
import json

bp = Blueprint("purchase_pdfs", __name__, url_prefix="/api/purchase-pdfs")

# Carpeta donde se guardan los PDFs
PDFS_FOLDER = "purchase_pdfs"
METADATA_FILE = "purchase_pdfs_metadata.json"


def get_metadata_path():
    """Obtiene la ruta del archivo de metadata"""
    bucket_name = os.getenv("GCS_BUCKET_NAME")
    if bucket_name:
        # En Cloud Storage, el metadata está en el bucket
        return f"{PDFS_FOLDER}/{METADATA_FILE}"
    else:
        # Localmente, en la carpeta del proyecto
        return os.path.join(os.path.dirname(__file__), '..', '..', PDFS_FOLDER, METADATA_FILE)


def get_pdfs_folder_path():
    """Obtiene la ruta de la carpeta de PDFs"""
    bucket_name = os.getenv("GCS_BUCKET_NAME")
    if bucket_name:
        return PDFS_FOLDER
    else:
        return os.path.join(os.path.dirname(__file__), '..', '..', PDFS_FOLDER)


def load_metadata():
    """Carga el metadata de PDFs guardados"""
    try:
        metadata_path = get_metadata_path()
        bucket_name = os.getenv("GCS_BUCKET_NAME")
        
        if bucket_name:
            # Cargar desde Cloud Storage
            client = get_storage_client()
            if client:
                bucket = client.bucket(bucket_name)
                blob = bucket.blob(metadata_path)
                if blob.exists():
                    content = blob.download_as_text()
                    return json.loads(content)
        else:
            # Cargar desde archivo local
            if os.path.exists(metadata_path):
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
    except Exception as e:
        print(f"Error cargando metadata: {e}")
    
    return []


def save_metadata(metadata):
    """Guarda el metadata de PDFs"""
    try:
        metadata_path = get_metadata_path()
        bucket_name = os.getenv("GCS_BUCKET_NAME")
        
        if bucket_name:
            # Guardar en Cloud Storage
            client = get_storage_client()
            if client:
                bucket = client.bucket(bucket_name)
                blob = bucket.blob(metadata_path)
                blob.upload_from_string(json.dumps(metadata, indent=2), content_type='application/json')
                return True
        else:
            # Guardar en archivo local
            folder = os.path.dirname(metadata_path)
            os.makedirs(folder, exist_ok=True)
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2)
            return True
    except Exception as e:
        print(f"Error guardando metadata: {e}")
        return False


@bp.route("", methods=["GET"])
def list_pdfs():
    """Lista todos los PDFs guardados, ordenados de más nuevo a más viejo"""
    try:
        metadata = load_metadata()
        # Ordenar por fecha (más nuevo primero)
        metadata.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        return jsonify(metadata)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Error listando PDFs: {str(e)}"}), 500


@bp.route("", methods=["POST"])
def save_pdf():
    """Guarda un PDF de compra"""
    try:
        if "file" not in request.files:
            return jsonify({"error": "No se envió archivo"}), 400
        
        file = request.files["file"]
        if file.filename == "":
            return jsonify({"error": "Archivo vacío"}), 400
        
        # Obtener metadata del request
        metadata_json = request.form.get('metadata')
        if not metadata_json:
            return jsonify({"error": "Metadata requerido"}), 400
        
        metadata = json.loads(metadata_json)
        
        # Generar nombre único para el archivo
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"compra_{timestamp}_{metadata.get('order_range', 'unknown')}.pdf"
        filename = filename.replace('/', '-').replace('#', '')
        
        bucket_name = os.getenv("GCS_BUCKET_NAME")
        
        if bucket_name:
            # Guardar en Cloud Storage
            # Subir directamente usando el cliente de Cloud Storage para controlar el nombre
            client = get_storage_client()
            if client:
                bucket = client.bucket(bucket_name)
                blob_path = f"{PDFS_FOLDER}/{filename}"
                blob = bucket.blob(blob_path)
                blob.upload_from_file(file, content_type='application/pdf')
                
                # URL relativa que apunta al endpoint del backend
                url = f"/api/purchase-pdfs/{filename}"
                
                # Guardar metadata
                pdf_metadata = {
                    'filename': filename,
                    'file_path': url,
                    'order_range': metadata.get('order_range', ''),
                    'date': metadata.get('date', ''),
                    'created_at': datetime.utcnow().isoformat()
                }
                
                all_metadata = load_metadata()
                all_metadata.append(pdf_metadata)
                save_metadata(all_metadata)
                
                return jsonify(pdf_metadata), 201
            else:
                return jsonify({"error": "Error conectando a Cloud Storage"}), 500
        else:
            # Guardar localmente
            folder = get_pdfs_folder_path()
            os.makedirs(folder, exist_ok=True)
            filepath = os.path.join(folder, filename)
            file.save(filepath)
            
            # Guardar metadata
            pdf_metadata = {
                'filename': filename,
                'file_path': f"/api/purchase-pdfs/{filename}",
                'order_range': metadata.get('order_range', ''),
                'date': metadata.get('date', ''),
                'created_at': datetime.utcnow().isoformat()
            }
            
            all_metadata = load_metadata()
            all_metadata.append(pdf_metadata)
            save_metadata(all_metadata)
            
            return jsonify(pdf_metadata), 201
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Error guardando PDF: {str(e)}"}), 500


@bp.route("/<filename>", methods=["GET"])
def download_pdf(filename):
    """Descarga un PDF guardado"""
    try:
        bucket_name = os.getenv("GCS_BUCKET_NAME")
        
        if bucket_name:
            # Descargar desde Cloud Storage usando get_file_content
            gcs_path = f"{PDFS_FOLDER}/{filename}"
            content, content_type = get_file_content(gcs_path)
            
            if content:
                from flask import Response
                return Response(
                    content,
                    mimetype='application/pdf',
                    headers={'Content-Disposition': f'attachment; filename={filename}'}
                )
        else:
            # Descargar desde archivo local
            folder = get_pdfs_folder_path()
            filepath = os.path.join(folder, filename)
            if os.path.exists(filepath):
                return send_file(filepath, mimetype='application/pdf', as_attachment=True, download_name=filename)
        
        return jsonify({"error": "PDF no encontrado"}), 404
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Error descargando PDF: {str(e)}"}), 500

