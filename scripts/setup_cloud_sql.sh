#!/bin/bash
# Script para configurar Cloud SQL desde cero
# Uso: ./setup_cloud_sql.sh

set -e

# Colores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Configurando Cloud SQL para Kivi${NC}"
echo ""

# Verificar que gcloud está instalado
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}❌ Error: gcloud CLI no está instalado${NC}"
    echo "Instala Google Cloud SDK: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Obtener proyecto actual
PROJECT_ID=$(gcloud config get-value project)
if [ -z "$PROJECT_ID" ]; then
    echo -e "${RED}❌ Error: No hay un proyecto de Google Cloud configurado${NC}"
    echo "Ejecuta: gcloud config set project TU_PROJECT_ID"
    exit 1
fi

echo -e "${GREEN}✅ Proyecto: $PROJECT_ID${NC}"
echo ""

# Solicitar información
read -p "Nombre de la instancia de Cloud SQL (default: kivi-db): " INSTANCE_NAME
INSTANCE_NAME=${INSTANCE_NAME:-kivi-db}

read -p "Región (default: us-central1): " REGION
REGION=${REGION:-us-central1}

read -sp "Password para el usuario root de PostgreSQL: " ROOT_PASSWORD
echo ""

read -sp "Password para el usuario kivi_user: " KIVI_PASSWORD
echo ""

read -p "Tier de la instancia (db-f1-micro, db-g1-small, etc.) (default: db-f1-micro): " TIER
TIER=${TIER:-db-f1-micro}

read -p "Tamaño del disco en GB (default: 10): " DISK_SIZE
DISK_SIZE=${DISK_SIZE:-10}

echo ""
echo -e "${YELLOW}📋 Resumen de configuración:${NC}"
echo "   Instancia: $INSTANCE_NAME"
echo "   Región: $REGION"
echo "   Tier: $TIER"
echo "   Disco: ${DISK_SIZE}GB"
echo ""

read -p "¿Continuar? (y/n): " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}❌ Cancelado${NC}"
    exit 1
fi

# Habilitar APIs necesarias
echo -e "${YELLOW}🔧 Habilitando APIs necesarias...${NC}"
gcloud services enable \
    sql-component.googleapis.com \
    sqladmin.googleapis.com \
    --quiet

# Crear instancia de Cloud SQL
echo -e "${YELLOW}🗄️  Creando instancia de Cloud SQL...${NC}"
gcloud sql instances create "$INSTANCE_NAME" \
    --database-version=POSTGRES_15 \
    --tier="$TIER" \
    --region="$REGION" \
    --root-password="$ROOT_PASSWORD" \
    --storage-type=SSD \
    --storage-size="${DISK_SIZE}GB" \
    --backup-start-time=03:00 \
    --enable-bin-log \
    --maintenance-window-day=SUN \
    --maintenance-window-hour=04 \
    --quiet

echo -e "${GREEN}✅ Instancia creada${NC}"

# Obtener connection name
CONNECTION_NAME=$(gcloud sql instances describe "$INSTANCE_NAME" \
    --format='value(connectionName)')

echo -e "${GREEN}✅ Connection name: $CONNECTION_NAME${NC}"

# Crear base de datos
echo -e "${YELLOW}📦 Creando base de datos kivi_v2...${NC}"
gcloud sql databases create kivi_v2 \
    --instance="$INSTANCE_NAME" \
    --quiet

echo -e "${GREEN}✅ Base de datos creada${NC}"

# Crear usuario
echo -e "${YELLOW}👤 Creando usuario kivi_user...${NC}"
gcloud sql users create kivi_user \
    --instance="$INSTANCE_NAME" \
    --password="$KIVI_PASSWORD" \
    --quiet

echo -e "${GREEN}✅ Usuario creado${NC}"

# Obtener IP pública (si existe)
PUBLIC_IP=$(gcloud sql instances describe "$INSTANCE_NAME" \
    --format='value(ipAddresses[0].ipAddress)' 2>/dev/null || echo "")

echo ""
echo -e "${GREEN}✅ Configuración completada${NC}"
echo ""
echo -e "${BLUE}📝 Información importante:${NC}"
echo "   Connection Name: $CONNECTION_NAME"
echo "   Database URL: postgresql://kivi_user:****@/kivi_v2?host=/cloudsql/$CONNECTION_NAME"
if [ -n "$PUBLIC_IP" ]; then
    echo "   IP Pública: $PUBLIC_IP"
fi
echo ""
echo -e "${YELLOW}💡 Próximos pasos:${NC}"
echo "   1. Guarda el connection name: $CONNECTION_NAME"
echo "   2. Usa el script restore_database.sh para restaurar tu backup"
echo "   3. Configura DATABASE_URL en Cloud Run con el formato:"
echo "      postgresql://kivi_user:PASSWORD@/kivi_v2?host=/cloudsql/$CONNECTION_NAME"
echo ""

