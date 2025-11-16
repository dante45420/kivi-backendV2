#!/bin/bash
# Script para hacer backup de la base de datos desde Railway
# Uso: ./backup_database.sh

set -e

echo "🔄 Iniciando backup de la base de datos desde Railway..."

# Colores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Verificar que DATABASE_URL esté configurado
if [ -z "$DATABASE_URL" ]; then
    echo -e "${RED}❌ Error: DATABASE_URL no está configurado${NC}"
    echo "Por favor, configura DATABASE_URL con la URL de tu base de datos de Railway"
    echo "Ejemplo: export DATABASE_URL='postgresql://user:pass@host:port/dbname'"
    exit 1
fi

# Crear directorio de backups si no existe
BACKUP_DIR="./backups"
mkdir -p "$BACKUP_DIR"

# Generar nombre de archivo con timestamp
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/kivi_backup_$TIMESTAMP.sql"
BACKUP_FILE_COMPRESSED="$BACKUP_FILE.gz"

echo -e "${YELLOW}📦 Creando backup...${NC}"

# Hacer backup usando pg_dump
# Extraer componentes de la URL
DB_URL=$DATABASE_URL

# Si DATABASE_URL tiene formato postgresql://, usar directamente
if [[ $DB_URL == postgresql://* ]]; then
    pg_dump "$DB_URL" > "$BACKUP_FILE"
else
    echo -e "${RED}❌ Error: DATABASE_URL debe tener formato postgresql://${NC}"
    exit 1
fi

# Verificar que el backup se creó correctamente
if [ ! -f "$BACKUP_FILE" ] || [ ! -s "$BACKUP_FILE" ]; then
    echo -e "${RED}❌ Error: El backup no se creó correctamente${NC}"
    exit 1
fi

# Comprimir el backup
echo -e "${YELLOW}🗜️  Comprimiendo backup...${NC}"
gzip "$BACKUP_FILE"
BACKUP_FILE="$BACKUP_FILE_COMPRESSED"

# Obtener el tamaño del archivo
FILE_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)

echo -e "${GREEN}✅ Backup creado exitosamente${NC}"
echo -e "   Archivo: $BACKUP_FILE"
echo -e "   Tamaño: $FILE_SIZE"
echo ""
echo -e "${YELLOW}💡 Próximos pasos:${NC}"
echo "   1. Verifica que el backup se creó correctamente"
echo "   2. Guarda este archivo en un lugar seguro"
echo "   3. Usa el script restore_database.sh para restaurar en Cloud SQL"

