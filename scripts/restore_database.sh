#!/bin/bash
# Script para restaurar backup en Cloud SQL
# Uso: ./restore_database.sh <backup_file.sql.gz> <cloud_sql_connection_name>

set -e

# Colores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Verificar argumentos
if [ $# -lt 2 ]; then
    echo -e "${RED}❌ Error: Faltan argumentos${NC}"
    echo "Uso: $0 <backup_file.sql.gz> <cloud_sql_connection_name>"
    echo ""
    echo "Ejemplo:"
    echo "  $0 ./backups/kivi_backup_20250101_120000.sql.gz kivi-project:us-central1:kivi-db"
    echo ""
    echo "Para obtener el connection name:"
    echo "  gcloud sql instances describe kivi-db --format='value(connectionName)'"
    exit 1
fi

BACKUP_FILE=$1
CLOUD_SQL_CONNECTION=$2

# Verificar que el archivo de backup existe
if [ ! -f "$BACKUP_FILE" ]; then
    echo -e "${RED}❌ Error: El archivo de backup no existe: $BACKUP_FILE${NC}"
    exit 1
fi

echo -e "${YELLOW}🔄 Iniciando restauración en Cloud SQL...${NC}"
echo -e "   Backup: $BACKUP_FILE"
echo -e "   Instancia: $CLOUD_SQL_CONNECTION"
echo ""

# Verificar que gcloud está instalado
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}❌ Error: gcloud CLI no está instalado${NC}"
    echo "Instala Google Cloud SDK: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Verificar que el usuario está autenticado
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo -e "${RED}❌ Error: No hay una cuenta de Google Cloud autenticada${NC}"
    echo "Ejecuta: gcloud auth login"
    exit 1
fi

# Descomprimir el backup si está comprimido
TEMP_SQL_FILE=""
if [[ $BACKUP_FILE == *.gz ]]; then
    echo -e "${YELLOW}📦 Descomprimiendo backup...${NC}"
    TEMP_SQL_FILE="/tmp/kivi_restore_$(date +%s).sql"
    gunzip -c "$BACKUP_FILE" > "$TEMP_SQL_FILE"
    SQL_FILE=$TEMP_SQL_FILE
else
    SQL_FILE=$BACKUP_FILE
fi

# Restaurar usando Cloud SQL Proxy o conexión directa
echo -e "${YELLOW}📥 Restaurando base de datos...${NC}"
echo -e "${YELLOW}⚠️  Esto puede tardar varios minutos dependiendo del tamaño del backup${NC}"

# Usar psql a través de Cloud SQL Proxy o conexión directa
# Opción 1: Si tienes Cloud SQL Proxy corriendo
if pg_isready -h 127.0.0.1 -p 5432 &> /dev/null; then
    echo -e "${GREEN}✅ Cloud SQL Proxy detectado, usando conexión local${NC}"
    psql "$DATABASE_URL" < "$SQL_FILE"
else
    # Opción 2: Usar gcloud sql import
    echo -e "${YELLOW}📤 Subiendo backup a Cloud Storage temporal...${NC}"
    
    # Crear bucket temporal si no existe
    TEMP_BUCKET="kivi-migration-temp-$(date +%s)"
    gsutil mb -p $(gcloud config get-value project) -l us-central1 "gs://$TEMP_BUCKET" 2>/dev/null || true
    
    # Subir el archivo SQL
    TEMP_GCS_PATH="gs://$TEMP_BUCKET/restore.sql"
    gsutil cp "$SQL_FILE" "$TEMP_GCS_PATH"
    
    # Importar a Cloud SQL
    echo -e "${YELLOW}📥 Importando a Cloud SQL...${NC}"
    gcloud sql import sql "$CLOUD_SQL_CONNECTION" "$TEMP_GCS_PATH" \
        --database=kivi_v2 \
        --quiet
    
    # Limpiar archivo temporal de GCS
    echo -e "${YELLOW}🧹 Limpiando archivos temporales...${NC}"
    gsutil rm "$TEMP_GCS_PATH"
    gsutil rb "gs://$TEMP_BUCKET" 2>/dev/null || true
fi

# Limpiar archivo temporal local si existe
if [ -n "$TEMP_SQL_FILE" ] && [ -f "$TEMP_SQL_FILE" ]; then
    rm "$TEMP_SQL_FILE"
fi

echo ""
echo -e "${GREEN}✅ Restauración completada exitosamente${NC}"
echo ""
echo -e "${YELLOW}💡 Próximos pasos:${NC}"
echo "   1. Verifica que los datos se restauraron correctamente"
echo "   2. Actualiza DATABASE_URL en tu aplicación para apuntar a Cloud SQL"
echo "   3. Prueba la conexión desde tu aplicación"

