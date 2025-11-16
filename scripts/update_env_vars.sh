#!/bin/bash
# Script para actualizar variables de entorno del backend en Cloud Run

set -e

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🔧 Actualizar Variables de Entorno del Backend${NC}"
echo ""

# Verificar que gcloud está configurado
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}❌ gcloud no está instalado${NC}"
    exit 1
fi

export PATH="/usr/local/share/google-cloud-sdk/bin:$PATH"
export CLOUDSDK_PYTHON=$(which python3)

# Obtener connection name
CLOUD_SQL_CONNECTION=$(gcloud sql instances describe kivi-db --format="value(connectionName)" 2>/dev/null || echo "")
if [ -z "$CLOUD_SQL_CONNECTION" ]; then
    echo -e "${RED}❌ No se pudo obtener el connection name de Cloud SQL${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Connection: $CLOUD_SQL_CONNECTION${NC}"
echo ""

# Solicitar información
read -p "Email del administrador (default: danteparodiwerht@gmail.com): " ADMIN_EMAIL
ADMIN_EMAIL=${ADMIN_EMAIL:-danteparodiwerht@gmail.com}

read -sp "Password del administrador: " ADMIN_PASSWORD
echo ""

if [ -z "$ADMIN_PASSWORD" ]; then
    echo -e "${RED}❌ La contraseña es requerida${NC}"
    exit 1
fi

read -p "ALLOWED_ORIGINS (default: *): " ALLOWED_ORIGINS
ALLOWED_ORIGINS=${ALLOWED_ORIGINS:-*}

# Generar SECRET_KEY
SECRET_KEY=$(openssl rand -hex 32)
echo -e "${GREEN}✅ Secret Key generada${NC}"

# Obtener password de la base de datos (puedes cambiarlo si quieres)
read -sp "Password de kivi_user en Cloud SQL (presiona Enter para usar la actual): " DB_PASSWORD
echo ""
DB_PASSWORD=${DB_PASSWORD:-Q3sKF14Uppj/EXH/Bi2A5g==}

# Construir DATABASE_URL
DATABASE_URL="postgresql://kivi_user:$DB_PASSWORD@/kivi_v2?host=/cloudsql/$CLOUD_SQL_CONNECTION"

echo ""
echo -e "${YELLOW}📋 Resumen de configuración:${NC}"
echo "   ADMIN_EMAIL: $ADMIN_EMAIL"
echo "   ADMIN_PASSWORD: ${ADMIN_PASSWORD:0:3}***"
echo "   ALLOWED_ORIGINS: $ALLOWED_ORIGINS"
echo "   SECRET_KEY: ${SECRET_KEY:0:20}..."
echo ""

read -p "¿Continuar con la actualización? (y/n): " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}❌ Cancelado${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}🔄 Actualizando variables de entorno...${NC}"

gcloud run services update kivi-backend \
    --platform managed \
    --region us-central1 \
    --update-env-vars "FLASK_ENV=production,DATABASE_URL=$DATABASE_URL,GCS_BUCKET_NAME=kivi-v2-media,SECRET_KEY=$SECRET_KEY,ADMIN_EMAIL=$ADMIN_EMAIL,ADMIN_PASSWORD=$ADMIN_PASSWORD,ALLOWED_ORIGINS=$ALLOWED_ORIGINS" \
    --quiet

echo ""
echo -e "${GREEN}✅ Variables actualizadas correctamente${NC}"
echo ""
echo -e "${BLUE}⏳ El servicio se está reiniciando... (espera 30 segundos)${NC}"
sleep 30

echo ""
echo -e "${GREEN}🎉 ¡Configuración completada!${NC}"
echo ""
echo -e "${YELLOW}💡 Próximos pasos:${NC}"
echo "   1. Verifica que el backend esté funcionando:"
echo "      curl https://kivi-backend-nn6ybvu7tq-uc.a.run.app/health"
echo ""
echo "   2. Prueba el login con:"
echo "      Email: $ADMIN_EMAIL"
echo "      Password: (la que ingresaste)"

