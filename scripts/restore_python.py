#!/usr/bin/env python3
"""
Restaurar backup usando Python/psycopg2
Funciona con cualquier versión de PostgreSQL
"""
import os
import sys
import gzip

try:
    import psycopg2
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
except ImportError:
    print("❌ Error: psycopg2 no está instalado")
    print("Instala con: pip install psycopg2-binary")
    sys.exit(1)

def restore_database(host, port, database, user, password, backup_file):
    """Restaura la base de datos desde un archivo SQL"""
    print(f"🔄 Conectando a la base de datos...")
    
    try:
        # Conectar a la base de datos usando parámetros separados
        conn = psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()
        
        print("✅ Conectado. Leyendo backup...")
        
        # Leer el archivo SQL
        if backup_file.endswith('.gz'):
            print("   Descomprimiendo backup...")
            with gzip.open(backup_file, 'rt', encoding='utf-8') as f:
                sql_content = f.read()
        else:
            with open(backup_file, 'r', encoding='utf-8') as f:
                sql_content = f.read()
        
        print(f"   Tamaño del SQL: {len(sql_content)} caracteres")
        print("📥 Ejecutando SQL (esto puede tardar...)")
        
        # Ejecutar el SQL
        # Dividir en statements individuales
        statements = []
        current_statement = ""
        
        for line in sql_content.split('\n'):
            # Saltar comentarios y líneas vacías al inicio
            stripped = line.strip()
            if not stripped or stripped.startswith('--'):
                continue
            
            current_statement += line + '\n'
            
            # Si la línea termina con ;, es el final de un statement
            if stripped.endswith(';'):
                statements.append(current_statement)
                current_statement = ""
        
        # Ejecutar cada statement
        total = len(statements)
        for i, statement in enumerate(statements, 1):
            if i % 10 == 0 or i == total:
                print(f"   Procesando statement {i}/{total}...")
            try:
                cur.execute(statement)
            except Exception as e:
                # Algunos errores son normales (tablas que ya existen, etc)
                if "already exists" not in str(e).lower() and "duplicate" not in str(e).lower():
                    print(f"   ⚠️  Advertencia en statement {i}: {e}")
        
        cur.close()
        conn.close()
        
        print("✅ Backup restaurado correctamente")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 7:
        print("Uso: python restore_python.py <host> <port> <database> <user> <password> <backup_file>")
        sys.exit(1)
    
    host = sys.argv[1]
    port = int(sys.argv[2])
    database = sys.argv[3]
    user = sys.argv[4]
    password = sys.argv[5]
    backup_file = sys.argv[6]
    
    if not os.path.exists(backup_file):
        print(f"❌ Error: El archivo de backup no existe: {backup_file}")
        sys.exit(1)
    
    restore_database(host, port, database, user, password, backup_file)

