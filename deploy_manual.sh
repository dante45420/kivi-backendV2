#!/bin/bash
# Script para hacer deploy manual del backend a Google Cloud Run

set -e

echo "🚀 Deploy Manual del Backend a Google Cloud Run"
echo "================================================"
echo ""

# Verificar que estamos en el directorio correcto
if [ ! -f "Dockerfile" ] || [ ! -f "cloudbuild.yaml" ]; then
    echo "❌ Error: No se encontraron Dockerfile o cloudbuild.yaml"
    echo "   Ejecuta este script desde el directorio v2-backend"
    exit 1
fi

# Configurar variables
export PATH="/usr/local/share/google-cloud-sdk/bin:$PATH"
export CLOUDSDK_PYTHON=$(which python3)

PROJECT_ID=$(gcloud config get-value project)
echo "📦 Proyecto: $PROJECT_ID"
echo ""

# Obtener información de Cloud SQL
echo "🔍 Obteniendo información de Cloud SQL..."
CLOUD_SQL_CONNECTION=$(gcloud sql instances describe kivi-db --format="value(connectionName)" 2>/dev/null || echo "")
if [ -z "$CLOUD_SQL_CONNECTION" ]; then
    echo "❌ Error: No se encontró la instancia de Cloud SQL 'kivi-db'"
    exit 1
fi
echo "✅ Cloud SQL: $CLOUD_SQL_CONNECTION"
echo ""

# Obtener variables de entorno actuales del servicio (si existe)
echo "🔍 Obteniendo variables de entorno del servicio actual..."
EXISTING_SERVICE=$(gcloud run services describe kivi-backend --platform managed --region us-central1 --format="value(metadata.name)" 2>/dev/null || echo "")

if [ -n "$EXISTING_SERVICE" ]; then
    echo "✅ Servicio existente encontrado, obteniendo configuración..."
    ENV_VARS=$(gcloud run services describe kivi-backend --platform managed --region us-central1 --format="get(spec.template.spec.containers[0].env)" 2>/dev/null || echo "")
    
    # Extraer valores (si existen)
    DATABASE_URL=$(echo "$ENV_VARS" | grep -oP 'DATABASE_URL[^,]*' | cut -d'=' -f2- | head -1 || echo "")
    GCS_BUCKET_NAME=$(echo "$ENV_VARS" | grep -oP 'GCS_BUCKET_NAME[^,]*' | cut -d'=' -f2- | head -1 || echo "")
    SECRET_KEY=$(echo "$ENV_VARS" | grep -oP 'SECRET_KEY[^,]*' | cut -d'=' -f2- | head -1 || echo "")
    ADMIN_EMAIL=$(echo "$ENV_VARS" | grep -oP 'ADMIN_EMAIL[^,]*' | cut -d'=' -f2- | head -1 || echo "")
    ADMIN_PASSWORD=$(echo "$ENV_VARS" | grep -oP 'ADMIN_PASSWORD[^,]*' | cut -d'=' -f2- | head -1 || echo "")
    ALLOWED_ORIGINS=$(echo "$ENV_VARS" | grep -oP 'ALLOWED_ORIGINS[^,]*' | cut -d'=' -f2- | head -1 || echo "")
    
    # Si no se encontraron, usar valores por defecto
    if [ -z "$DATABASE_URL" ]; then
        DATABASE_URL="postgresql://kivi_user:Q3sKF14Uppj/EXH/Bi2A5g==@/kivi_v2?host=/cloudsql/$CLOUD_SQL_CONNECTION"
    fi
    if [ -z "$GCS_BUCKET_NAME" ]; then
        GCS_BUCKET_NAME="kivi-v2-media"
    fi
    if [ -z "$SECRET_KEY" ]; then
        SECRET_KEY=$(openssl rand -hex 32)
    fi
    if [ -z "$ADMIN_EMAIL" ]; then
        ADMIN_EMAIL="danteparodiwerht@gmail.com"
    fi
    if [ -z "$ADMIN_PASSWORD" ]; then
        echo "⚠️  No se encontró ADMIN_PASSWORD, necesitarás configurarlo después"
        ADMIN_PASSWORD="CHANGE_ME"
    fi
    if [ -z "$ALLOWED_ORIGINS" ]; then
        ALLOWED_ORIGINS="*"
    fi
else
    echo "⚠️  Servicio no existe, usando valores por defecto"
    DATABASE_URL="postgresql://kivi_user:Q3sKF14Uppj/EXH/Bi2A5g==@/kivi_v2?host=/cloudsql/$CLOUD_SQL_CONNECTION"
    GCS_BUCKET_NAME="kivi-v2-media"
    SECRET_KEY=$(openssl rand -hex 32)
    ADMIN_EMAIL="danteparodiwerht@gmail.com"
    ADMIN_PASSWORD="CHANGE_ME"
    ALLOWED_ORIGINS="*"
fi

GCS_SECRET_NAME="gcs-credentials"

echo "✅ Variables configuradas"
echo ""

# Mostrar resumen de configuración
echo "📋 Resumen de configuración:"
echo "   - Cloud SQL: $CLOUD_SQL_CONNECTION"
echo "   - GCS Bucket: $GCS_BUCKET_NAME"
echo "   - Admin Email: $ADMIN_EMAIL"
echo "   - Allowed Origins: $ALLOWED_ORIGINS"
echo ""

# Construir imagen
echo "🔨 Construyendo imagen Docker..."
COMMIT_SHA=$(git rev-parse --short HEAD 2>/dev/null || echo "manual-$(date +%s)")
IMAGE_TAG="gcr.io/$PROJECT_ID/kivi-backend:$COMMIT_SHA"
echo "   Tag: $IMAGE_TAG"
echo ""

gcloud builds submit --tag "$IMAGE_TAG" --quiet || {
    echo "❌ Error al construir la imagen"
    exit 1
}

echo "✅ Imagen construida exitosamente"
echo ""

# Desplegar a Cloud Run
echo "🚀 Desplegando a Cloud Run..."
echo ""

gcloud run deploy kivi-backend \
  --image "$IMAGE_TAG" \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --add-cloudsql-instances "$CLOUD_SQL_CONNECTION" \
  --set-env-vars "FLASK_ENV=production,DATABASE_URL=$DATABASE_URL,GCS_BUCKET_NAME=$GCS_BUCKET_NAME,SECRET_KEY=$SECRET_KEY,ADMIN_EMAIL=$ADMIN_EMAIL,ADMIN_PASSWORD=$ADMIN_PASSWORD,ALLOWED_ORIGINS=$ALLOWED_ORIGINS" \
  --set-secrets "GOOGLE_APPLICATION_CREDENTIALS=$GCS_SECRET_NAME:latest" \
  --memory 512Mi \
  --cpu 1 \
  --timeout 300 \
  --max-instances 10 \
  --quiet || {
    echo "❌ Error al desplegar"
    exit 1
}

echo ""
echo "✅ Deploy completado exitosamente!"
echo ""

# Obtener URL del servicio
SERVICE_URL=$(gcloud run services describe kivi-backend --platform managed --region us-central1 --format="value(status.url)" 2>/dev/null || echo "")

if [ -n "$SERVICE_URL" ]; then
    echo "🌐 URL del servicio: $SERVICE_URL"
    echo ""
    echo "🔍 Verificando salud del servicio..."
    sleep 3
    if curl -s "$SERVICE_URL/health" > /dev/null 2>&1; then
        echo "✅ Servicio respondiendo correctamente"
        curl -s "$SERVICE_URL/health" | head -1
    else
        echo "⚠️  El servicio no responde en /health (puede estar iniciando)"
    fi
    echo ""
fi

echo "📋 Comandos útiles:"
echo "   Ver logs: gcloud run services logs read kivi-backend --region us-central1"
echo "   Ver detalles: gcloud run services describe kivi-backend --region us-central1"
echo "   URL: $SERVICE_URL"
echo ""

