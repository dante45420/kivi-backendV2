#!/usr/bin/env python3
"""
Script de migración: Agregar columna cost a order_items
Ejecuta la migración SQL para agregar el campo cost a la tabla order_items
"""
import os
import sys
from pathlib import Path

# Agregar el directorio padre al path para importar módulos
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db import db
from flask import Flask
from app.config import get_config


def run_migration():
    """Ejecuta la migración para agregar la columna cost"""
    app = Flask(__name__)
    app.config.from_object(get_config())
    db.init_app(app)
    
    with app.app_context():
        try:
            # Leer el script SQL
            sql_file = Path(__file__).parent / "add_cost_to_order_items.sql"
            if not sql_file.exists():
                print(f"❌ Error: No se encontró el archivo SQL: {sql_file}")
                return False
            
            sql_content = sql_file.read_text()
            
            # Ejecutar la migración
            # Para SQLite, usar ALTER TABLE directamente
            # Para PostgreSQL, el script SQL ya tiene IF NOT EXISTS
            db_url = app.config.get('SQLALCHEMY_DATABASE_URI', '')
            
            if 'sqlite' in db_url.lower():
                # SQLite no soporta IF NOT EXISTS en ALTER TABLE ADD COLUMN
                # Verificar si la columna ya existe
                try:
                    result = db.session.execute(
                        "SELECT cost FROM order_items LIMIT 1"
                    )
                    print("✅ La columna 'cost' ya existe en order_items")
                    return True
                except Exception:
                    # La columna no existe, agregarla
                    db.session.execute(
                        "ALTER TABLE order_items ADD COLUMN cost FLOAT"
                    )
                    db.session.commit()
                    print("✅ Columna 'cost' agregada exitosamente a order_items")
                    return True
            else:
                # PostgreSQL u otra base de datos
                # Ejecutar el SQL directamente
                db.session.execute(sql_content)
                db.session.commit()
                print("✅ Migración ejecutada exitosamente")
                return True
                
        except Exception as e:
            print(f"❌ Error ejecutando migración: {e}")
            import traceback
            traceback.print_exc()
            db.session.rollback()
            return False


if __name__ == "__main__":
    print("🔄 Ejecutando migración: Agregar columna cost a order_items...")
    success = run_migration()
    sys.exit(0 if success else 1)


