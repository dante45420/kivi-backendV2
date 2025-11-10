"""
Kivi V2.0 - Aplicación Flask Principal
Personal Shopper Lo Valledor
"""
import os
from flask import Flask
from flask_cors import CORS
from app.config import get_config
from app.db import db, init_db


def create_app():
    """Factory para crear la aplicación Flask"""
    app = Flask(__name__)
    
    # Cargar configuración
    app.config.from_object(get_config())
    
    # Debug: mostrar path de DB
    print(f"📍 Database URI: {app.config['SQLALCHEMY_DATABASE_URI']}")
    
    # Habilitar CORS
    # En producción, especificar dominios permitidos
    allowed_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")
    if "*" in allowed_origins:
        # Desarrollo: permitir todos
        CORS(app, resources={r"/api/*": {
            "origins": "*",
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }})
    else:
        # Producción: dominios específicos
        CORS(app, resources={r"/api/*": {
            "origins": allowed_origins,
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"],
            "supports_credentials": True
        }})
    
    # Inicializar base de datos
    db.init_app(app)
    
    with app.app_context():
        # Importar modelos
        from app.models import (
            Category, Product, Customer, Order, OrderItem,
            Expense, Payment, PaymentAllocation, WeeklyOffer,
            PriceHistory, ContentTemplate, KiviTip
        )
        
        # Crear carpeta instance si no existe
        os.makedirs(os.path.join(os.path.dirname(__file__), 'instance'), exist_ok=True)
        
        # Crear tablas
        db.create_all()
        
        # Inicializar datos de prueba si es desarrollo
        if app.config["FLASK_ENV"] == "development":
            init_dev_data()
        
        # Registrar blueprints de APIs
        from app.api import (
            categories_bp, products_bp, customers_bp,
            orders_bp, payments_bp, purchases_bp, kivi_bp, content_bp,
            weekly_offers_bp, auth_bp, images_bp
        )
        
        app.register_blueprint(auth_bp, url_prefix="/api/auth")
        app.register_blueprint(categories_bp, url_prefix="/api/categories")
        app.register_blueprint(products_bp, url_prefix="/api/products")
        app.register_blueprint(customers_bp, url_prefix="/api/customers")
        app.register_blueprint(orders_bp, url_prefix="/api/orders")
        app.register_blueprint(payments_bp, url_prefix="/api/payments")
        app.register_blueprint(purchases_bp, url_prefix="/api/purchases")
        app.register_blueprint(kivi_bp, url_prefix="/api/kivi")
        app.register_blueprint(content_bp, url_prefix="/api/content")
        app.register_blueprint(weekly_offers_bp, url_prefix="/api/weekly-offers")
        app.register_blueprint(images_bp, url_prefix="/api/images")
    
    # Ruta de health check
    @app.route("/health")
    def health():
        return {"status": "ok", "message": "Kivi V2.0 is running! 🐕"}
    
    # Servir archivos estáticos de uploads
    from flask import send_from_directory
    
    @app.route("/uploads/<path:filename>")
    def serve_upload(filename):
        # Obtener la ruta base del proyecto (donde está wsgi.py)
        base_dir = os.path.dirname(os.path.abspath(__file__))
        uploads_dir = os.path.join(base_dir, 'uploads')
        return send_from_directory(uploads_dir, filename)
    
    return app


def init_dev_data():
    """Inicializa datos de desarrollo"""
    from app.models import Category, KiviTip, Product
    
    # Verificar si ya hay datos
    if Category.query.first():
        return
    
    print("🌱 Inicializando datos de desarrollo...")
    
    # Crear categorías
    categories = [
        Category(name="Fruta", emoji="🍎", order=1),
        Category(name="Verdura", emoji="🥬", order=2),
        Category(name="Otros tipos de comida", emoji="🍴", order=3),
        Category(name="Bebidas", emoji="🥤", order=4),
    ]
    for cat in categories:
        db.session.add(cat)
    
    db.session.flush()  # Para obtener los IDs
    
    # Crear algunos productos de ejemplo
    products = [
        Product(name="Tomate", category_id=categories[1].id, sale_price=1500, unit="kg", active=True),
        Product(name="Palta Hass", category_id=categories[0].id, sale_price=2500, unit="kg", active=True),
        Product(name="Mango", category_id=categories[0].id, sale_price=1800, unit="unit", active=True),
        Product(name="Lechuga", category_id=categories[1].id, sale_price=800, unit="unit", active=True),
        Product(name="Manzana", category_id=categories[0].id, sale_price=1200, unit="kg", active=True),
    ]
    for prod in products:
        db.session.add(prod)
    
    # Crear tips de Kivi
    tips = [
        KiviTip(category="brand_info", message="¡Hola! Soy Kivi, tu personal shopper de Lo Valledor 🐕", emoji="🐕"),
        KiviTip(category="platform_usage", message="¿Sabías que puedes parsear pedidos directamente desde WhatsApp?", emoji="💡"),
        KiviTip(category="product_info", message="Los aguacates maduran mejor a temperatura ambiente", emoji="🥑"),
        KiviTip(category="promotion", message="Revisa las ofertas semanales para los mejores precios", emoji="🎉"),
    ]
    for tip in tips:
        db.session.add(tip)
    
    db.session.commit()
    print("✅ Datos de desarrollo inicializados (4 categorías, 5 productos, 4 tips)")


# Crear instancia de la app para gunicorn
app = create_app()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)

