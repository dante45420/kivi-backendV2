"""
Configuración de base de datos 2.0
"""
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def init_db(app):
    """Inicializa la base de datos con la app Flask"""
    db.init_app(app)
    
    with app.app_context():
        db.create_all()
        print("✅ Base de datos inicializada")

