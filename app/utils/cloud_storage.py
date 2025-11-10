"""
Utilidad: Manejo de Google Cloud Storage
Upload, delete y obtención de URLs
"""
import os
import json
import tempfile
from google.cloud import storage
from werkzeug.utils import secure_filename
import uuid


def get_storage_client():
    """Obtiene el cliente de Cloud Storage"""
    try:
        # Railway puede pasar las credenciales como JSON string en variable de entorno
        creds_json = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        
        if not creds_json:
            print("⚠️ GOOGLE_APPLICATION_CREDENTIALS no está configurado")
            return None
        
        # Debug: ver qué tipo de valor recibimos
        print(f"🔍 GOOGLE_APPLICATION_CREDENTIALS tipo: {type(creds_json)}, primeros 50 chars: {str(creds_json)[:50]}")
        
        # Limpiar espacios en blanco
        creds_json = creds_json.strip()
        
        # Si es un JSON string (Railway), usar directamente
        if creds_json.startswith('{'):
            try:
                # IMPORTANTE: Remover la variable de entorno temporalmente para evitar que
                # la librería de Google Cloud la lea automáticamente como ruta de archivo
                original_creds = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
                if "GOOGLE_APPLICATION_CREDENTIALS" in os.environ:
                    del os.environ["GOOGLE_APPLICATION_CREDENTIALS"]
                
                try:
                    # Parsear el JSON
                    creds_data = json.loads(creds_json)
                    print(f"✅ JSON parseado correctamente. Project ID: {creds_data.get('project_id', 'N/A')}")
                    
                    # Usar from_service_account_info para crear el cliente directamente desde el dict
                    client = storage.Client.from_service_account_info(creds_data)
                    print("✅ Cloud Storage inicializado desde JSON string")
                    return client
                finally:
                    # Restaurar la variable de entorno original si existía
                    if original_creds:
                        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = original_creds
                    
            except json.JSONDecodeError as e:
                print(f"⚠️ GOOGLE_APPLICATION_CREDENTIALS no es un JSON válido: {e}")
                print(f"   Primeros 200 chars del JSON: {creds_json[:200]}")
                return None
            except Exception as e:
                print(f"⚠️ Error creando cliente desde JSON: {e}")
                import traceback
                traceback.print_exc()
                return None
        
        # Si es una ruta de archivo (desarrollo local)
        elif os.path.exists(creds_json):
            try:
                print(f"📁 Detectado como ruta de archivo: {creds_json}")
                client = storage.Client.from_service_account_json(creds_json)
                print("✅ Cloud Storage inicializado desde archivo")
                return client
            except Exception as e:
                print(f"⚠️ Error leyendo archivo de credenciales: {e}")
                return None
        
        # Si no es ni JSON ni archivo válido
        else:
            print(f"⚠️ GOOGLE_APPLICATION_CREDENTIALS no es válido (ni JSON ni archivo existente)")
            print(f"   Valor recibido (primeros 100 chars): {creds_json[:100]}...")
            print(f"   ¿Es ruta? {os.path.exists(creds_json) if creds_json else 'N/A'}")
            return None
        
    except Exception as e:
        print(f"⚠️ Error al inicializar Cloud Storage: {e}")
        import traceback
        traceback.print_exc()
        return None


def upload_file(file, folder="general"):
    """
    Sube un archivo a Cloud Storage
    
    Args:
        file: Archivo de Flask (FileStorage)
        folder: Carpeta destino en el bucket
        
    Returns:
        str: URL pública del archivo o None si falla
    """
    client = get_storage_client()
    
    if not client:
        return None
    
    bucket_name = os.getenv("GCS_BUCKET_NAME")
    
    if not bucket_name:
        print("⚠️ GCS_BUCKET_NAME no configurado")
        return None
    
    try:
        bucket = client.bucket(bucket_name)
        
        # Generar nombre único
        filename = secure_filename(file.filename)
        unique_filename = f"{folder}/{uuid.uuid4()}_{filename}"
        
        blob = bucket.blob(unique_filename)
        blob.upload_from_file(file, content_type=file.content_type)
        
        # Hacer público
        blob.make_public()
        
        return blob.public_url
    
    except Exception as e:
        print(f"❌ Error al subir archivo: {e}")
        return None


def delete_file(file_url):
    """
    Elimina un archivo de Cloud Storage
    
    Args:
        file_url: URL pública del archivo
        
    Returns:
        bool: True si se eliminó, False si falló
    """
    client = get_storage_client()
    
    if not client:
        return False
    
    bucket_name = os.getenv("GCS_BUCKET_NAME")
    
    if not bucket_name:
        return False
    
    try:
        # Extraer el path del blob desde la URL
        # Formato: https://storage.googleapis.com/bucket-name/path/to/file.jpg
        if bucket_name in file_url:
            blob_path = file_url.split(f"{bucket_name}/")[1]
            
            bucket = client.bucket(bucket_name)
            blob = bucket.blob(blob_path)
            blob.delete()
            
            return True
    
    except Exception as e:
        print(f"❌ Error al eliminar archivo: {e}")
        return False

