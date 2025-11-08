"""
Configuración de la aplicación
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Directorio base del proyecto
BASE_DIR = Path(__file__).resolve().parent.parent

# Cargar .env desde el directorio del proyecto
load_dotenv(BASE_DIR / '.env')


class Config:
    """Configuración base"""
    
    # Flask
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    FLASK_ENV = os.getenv("FLASK_ENV", "development")
    
    # Database con path absoluto
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL") or f"sqlite:///{BASE_DIR}/instance/kivi_v2.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False  # Desactivar logs SQL para evitar spam
    
    # Admin credentials
    ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "danteparodiwerht@gmail.com")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "Dante454@")
    
    # OpenAI
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    
    # Google Cloud Storage
    GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "kivi-v2-media")
    GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    
    # WhatsApp
    WHATSAPP_API_TOKEN = os.getenv("WHATSAPP_API_TOKEN")
    WHATSAPP_ADMIN_PHONE = os.getenv("WHATSAPP_ADMIN_PHONE")
    WHATSAPP_BUSINESS_URL = os.getenv("WHATSAPP_BUSINESS_URL", "https://wa.me/56912345678")
    
    # Upload limits
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}


class DevelopmentConfig(Config):
    """Configuración de desarrollo"""
    DEBUG = True


class ProductionConfig(Config):
    """Configuración de producción"""
    DEBUG = False
    SQLALCHEMY_ECHO = False


# Mapeo de configuraciones
config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
}


def get_config():
    """Obtiene la configuración según el entorno"""
    env = os.getenv("FLASK_ENV", "development")
    return config_by_name.get(env, DevelopmentConfig)

