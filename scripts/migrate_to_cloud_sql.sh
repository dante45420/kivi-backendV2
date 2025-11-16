#!/bin/bash
# Script completo de migración a Cloud SQL
# Este script automatiza todo el proceso de migración

set -e

# Colores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Migración Completa a Cloud SQL${NC}"
echo ""

# Verificar que estamos en el directorio correcto
if [ ! -f "wsgi.py" ]; then
    echo -e "${RED}❌ Error: Este script debe ejecutarse desde v2-backend/${NC}"
    exit 1
fi

# Verificar que DATABASE_URL de Railway esté configurado
if [ -z "$RAILWAY_DATABASE_URL" ]; then
    echo -e "${YELLOW}⚠️  RAILWAY_DATABASE_URL no está configurado${NC}"
    read -p "Ingresa la DATABASE_URL de Railway: " RAILWAY_DATABASE_URL
    export DATABASE_URL="$RAILWAY_DATABASE_URL"
else
    export DATABASE_URL="$RAILWAY_DATABASE_URL"
fi

# Paso 1: Backup
echo -e "${YELLOW}📦 Paso 1: Creando backup desde Railway...${NC}"
chmod +x scripts/backup_database.sh
./scripts/backup_database.sh

# Obtener el archivo de backup más reciente
LATEST_BACKUP=$(ls -t backups/*.sql.gz | head -1)
if [ -z "$LATEST_BACKUP" ]; then
    echo -e "${RED}❌ Error: No se encontró el archivo de backup${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Backup creado: $LATEST_BACKUP${NC}"
echo ""

# Paso 2: Configurar Cloud SQL
echo -e "${YELLOW}🗄️  Paso 2: Configurando Cloud SQL...${NC}"
read -p "¿Ya tienes una instancia de Cloud SQL configurada? (y/n): " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    chmod +x scripts/setup_cloud_sql.sh
    ./scripts/setup_cloud_sql.sh
fi

# Solicitar connection name
read -p "Connection name de Cloud SQL (formato: project:region:instance): " CLOUD_SQL_CONNECTION
if [ -z "$CLOUD_SQL_CONNECTION" ]; then
    echo -e "${RED}❌ Error: Connection name es requerido${NC}"
    exit 1
fi

echo ""

# Paso 3: Restaurar backup
echo -e "${YELLOW}📥 Paso 3: Restaurando backup en Cloud SQL...${NC}"
chmod +x scripts/restore_database.sh
./scripts/restore_database.sh "$LATEST_BACKUP" "$CLOUD_SQL_CONNECTION"

echo ""
echo -e "${GREEN}✅ Migración completada exitosamente${NC}"
echo ""
echo -e "${BLUE}📝 Próximos pasos:${NC}"
echo "   1. Actualiza DATABASE_URL en Cloud Run:"
echo "      postgresql://kivi_user:PASSWORD@/kivi_v2?host=/cloudsql/$CLOUD_SQL_CONNECTION"
echo "   2. Verifica que la aplicación funcione correctamente"
echo "   3. Una vez verificado, puedes eliminar la base de datos de Railway"
echo ""

