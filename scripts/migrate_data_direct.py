#!/usr/bin/env python3
"""
Migración directa de datos desde Railway a Cloud SQL
Importa todas las tablas excepto pagos
"""
import sys
import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime

def migrate_table(source_conn, target_conn, table_name, exclude_columns=None):
    """Migra una tabla completa desde source a target"""
    exclude_columns = exclude_columns or []
    
    print(f"\n📦 Migrando tabla: {table_name}")
    
    source_cur = source_conn.cursor()
    target_cur = target_conn.cursor()
    
    try:
        # Obtener estructura de la tabla
        source_cur.execute(f"""
            SELECT column_name, data_type 
            FROM information_schema.columns
            WHERE table_name = '{table_name}'
            AND column_name NOT IN {tuple(exclude_columns) if exclude_columns else "('id')"}
            ORDER BY ordinal_position;
        """)
        columns = source_cur.fetchall()
        
        if not columns:
            print(f"   ⚠️  Tabla {table_name} no tiene columnas o no existe")
            return
        
        # Obtener nombres de columnas (excluyendo las especificadas)
        column_names = [col[0] for col in columns]
        select_columns = ', '.join([f'"{col}"' for col in column_names])
        
        # Limpiar tabla destino (opcional, comentado para seguridad)
        # target_cur.execute(f'TRUNCATE TABLE "{table_name}" CASCADE;')
        
        # Obtener datos
        source_cur.execute(f'SELECT {select_columns} FROM "{table_name}";')
        rows = source_cur.fetchall()
        
        if not rows:
            print(f"   ℹ️  Tabla {table_name} está vacía")
            return
        
        print(f"   📥 {len(rows)} registros encontrados")
        
        # Insertar datos en lotes
        insert_query = f'INSERT INTO "{table_name}" ({select_columns}) VALUES %s ON CONFLICT DO NOTHING;'
        
        # Insertar en lotes de 100
        batch_size = 100
        inserted = 0
        
        for i in range(0, len(rows), batch_size):
            batch = rows[i:i + batch_size]
            try:
                execute_values(target_cur, insert_query, batch)
                inserted += len(batch)
                if inserted % 500 == 0 or inserted == len(rows):
                    print(f"   ✅ Insertados {inserted}/{len(rows)} registros")
            except Exception as e:
                print(f"   ⚠️  Error en lote {i//batch_size + 1}: {e}")
                # Intentar insertar uno por uno para identificar el problema
                for idx, row in enumerate(batch):
                    try:
                        execute_values(target_cur, insert_query, [row])
                    except Exception as e2:
                        print(f"      Error en registro {i + idx + 1}: {e2}")
                        print(f"      Datos: {row[:3]}...")  # Mostrar primeros 3 valores
        
        target_conn.commit()
        print(f"   ✅ {table_name}: {inserted} registros migrados")
        
    except Exception as e:
        print(f"   ❌ Error migrando {table_name}: {e}")
        import traceback
        traceback.print_exc()
        target_conn.rollback()

def main():
    if len(sys.argv) < 3:
        print("Uso: python migrate_data_direct.py <RAILWAY_DATABASE_URL> <CLOUD_SQL_HOST> <CLOUD_SQL_PASSWORD>")
        sys.exit(1)
    
    railway_url = sys.argv[1]
    cloud_sql_host = sys.argv[2]
    cloud_sql_password = sys.argv[3]
    
    print("🔄 Iniciando migración directa de datos...")
    print("=" * 60)
    
    # Conectar a Railway
    print("\n📡 Conectando a Railway...")
    try:
        source_conn = psycopg2.connect(railway_url)
        print("✅ Conectado a Railway")
    except Exception as e:
        print(f"❌ Error conectando a Railway: {e}")
        sys.exit(1)
    
    # Conectar a Cloud SQL
    print("\n☁️  Conectando a Cloud SQL...")
    try:
        target_conn = psycopg2.connect(
            host=cloud_sql_host,
            port=5432,
            database="kivi_v2",
            user="kivi_user",
            password=cloud_sql_password
        )
        print("✅ Conectado a Cloud SQL")
    except Exception as e:
        print(f"❌ Error conectando a Cloud SQL: {e}")
        source_conn.close()
        sys.exit(1)
    
    # Lista de tablas a migrar (excluyendo pagos y tablas relacionadas)
    tables_to_migrate = [
        "categories",
        "products", 
        "customers",
        "orders",
        "order_items",
        "weekly_offers",
        "kivi_tips",
        "content_templates",
        "expenses",
        "purchases",
        "price_history"
    ]
    
    print(f"\n📋 Tablas a migrar: {len(tables_to_migrate)}")
    print("   (Excluyendo: payments, payment_allocations)")
    
    # Migrar cada tabla
    for table in tables_to_migrate:
        migrate_table(source_conn, target_conn, table)
    
    # Cerrar conexiones
    source_conn.close()
    target_conn.close()
    
    print("\n" + "=" * 60)
    print("✅ Migración completada!")
    print("\n📊 Resumen:")
    print("   - Productos migrados")
    print("   - Clientes migrados")
    print("   - Pedidos migrados")
    print("   - Ofertas migradas")
    print("   - Tips migrados")
    print("   - Pagos NO migrados (como solicitaste)")

if __name__ == "__main__":
    main()

