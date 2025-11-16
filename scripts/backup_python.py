#!/usr/bin/env python3
"""
Backup de base de datos usando Python/psycopg2
Funciona con cualquier versión de PostgreSQL
"""
import os
import sys
import gzip
from datetime import datetime

try:
    import psycopg2
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
except ImportError:
    print("❌ Error: psycopg2 no está instalado")
    print("Instala con: pip install psycopg2-binary")
    sys.exit(1)

def backup_database(database_url, output_file):
    """Hace backup de la base de datos"""
    print(f"🔄 Conectando a la base de datos...")
    
    try:
        # Conectar a la base de datos
        conn = psycopg2.connect(database_url)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()
        
        print("✅ Conectado. Obteniendo esquema y datos...")
        
        # Obtener todas las tablas
        cur.execute("""
            SELECT tablename 
            FROM pg_tables 
            WHERE schemaname = 'public'
            ORDER BY tablename;
        """)
        tables = [row[0] for row in cur.fetchall()]
        
        print(f"📦 Encontradas {len(tables)} tablas")
        
        # Crear archivo SQL
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("-- Backup de base de datos Kivi\n")
            f.write(f"-- Fecha: {datetime.now().isoformat()}\n")
            f.write(f"-- Tablas: {', '.join(tables)}\n\n")
            f.write("BEGIN;\n\n")
            
            # Para cada tabla, obtener estructura y datos
            for table in tables:
                print(f"   Exportando tabla: {table}")
                
                # Obtener estructura de la tabla
                cur.execute(f"""
                    SELECT column_name, data_type, character_maximum_length
                    FROM information_schema.columns
                    WHERE table_name = '{table}'
                    ORDER BY ordinal_position;
                """)
                columns = cur.fetchall()
                
                # Obtener datos
                cur.execute(f'SELECT * FROM "{table}";')
                rows = cur.fetchall()
                
                # Escribir estructura y datos
                f.write(f"\n-- Tabla: {table}\n")
                f.write(f"CREATE TABLE IF NOT EXISTS \"{table}\" (\n")
                
                col_defs = []
                for col in columns:
                    col_name, data_type, max_len = col
                    if max_len:
                        col_def = f'    "{col_name}" {data_type}({max_len})'
                    else:
                        col_def = f'    "{col_name}" {data_type}'
                    col_defs.append(col_def)
                
                f.write(",\n".join(col_defs))
                f.write("\n);\n\n")
                
                # Insertar datos
                if rows:
                    f.write(f"INSERT INTO \"{table}\" VALUES\n")
                    values_list = []
                    for row in rows:
                        # Escapar valores
                        escaped_values = []
                        for val in row:
                            if val is None:
                                escaped_values.append("NULL")
                            elif isinstance(val, str):
                                escaped_val = val.replace("'", "''")
                                escaped_values.append(f"'{escaped_val}'")
                            else:
                                escaped_values.append(str(val))
                        values_list.append(f"({', '.join(escaped_values)})")
                    
                    f.write(",\n".join(values_list))
                    f.write(";\n\n")
            
            f.write("COMMIT;\n")
        
        cur.close()
        conn.close()
        
        print(f"✅ Backup creado: {output_file}")
        
        # Comprimir
        compressed_file = f"{output_file}.gz"
        with open(output_file, 'rb') as f_in:
            with gzip.open(compressed_file, 'wb') as f_out:
                f_out.writelines(f_in)
        
        os.remove(output_file)
        print(f"✅ Backup comprimido: {compressed_file}")
        
        return compressed_file
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python backup_python.py <DATABASE_URL> [output_file]")
        sys.exit(1)
    
    database_url = sys.argv[1]
    if len(sys.argv) > 2:
        output_file = sys.argv[2]
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"backups/kivi_backup_{timestamp}.sql"
    
    # Crear directorio si no existe
    os.makedirs(os.path.dirname(output_file) if os.path.dirname(output_file) else ".", exist_ok=True)
    
    backup_database(database_url, output_file)

