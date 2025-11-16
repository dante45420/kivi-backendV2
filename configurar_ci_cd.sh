#!/bin/bash
# Script para configurar CI/CD automático desde GitHub a Google Cloud

set -e

echo "🔧 Configurando CI/CD automático para el backend"
echo "================================================"
echo ""

# Verificar que estamos en el directorio correcto
if [ ! -f "cloudbuild.yaml" ]; then
    echo "❌ Error: No se encontró cloudbuild.yaml"
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

# Obtener URL del backend actual
BACKEND_URL=$(gcloud run services describe kivi-backend --platform managed --region us-central1 --format="value(status.url)" 2>/dev/null || echo "")
if [ -z "$BACKEND_URL" ]; then
    echo "⚠️  No se encontró el servicio kivi-backend, usando URL por defecto"
    BACKEND_URL="https://kivi-backend-xxxxx-uc.a.run.app"
fi
echo "✅ Backend URL: $BACKEND_URL"
echo ""

# Obtener variables de entorno actuales del servicio
echo "🔍 Obteniendo variables de entorno del servicio actual..."
ENV_VARS=$(gcloud run services describe kivi-backend --platform managed --region us-central1 --format="value(spec.template.spec.containers[0].env)" 2>/dev/null || echo "")

# Extraer valores de las variables de entorno
DATABASE_URL=$(echo "$ENV_VARS" | grep -oP 'DATABASE_URL=\K[^,]*' || echo "postgresql://kivi_user:PASSWORD@/kivi_v2?host=/cloudsql/$CLOUD_SQL_CONNECTION")
GCS_BUCKET_NAME=$(echo "$ENV_VARS" | grep -oP 'GCS_BUCKET_NAME=\K[^,]*' || echo "kivi-v2-media")
SECRET_KEY=$(echo "$ENV_VARS" | grep -oP 'SECRET_KEY=\K[^,]*' || openssl rand -hex 32)
ADMIN_EMAIL=$(echo "$ENV_VARS" | grep -oP 'ADMIN_EMAIL=\K[^,]*' || echo "danteparodiwerht@gmail.com")
ADMIN_PASSWORD=$(echo "$ENV_VARS" | grep -oP 'ADMIN_PASSWORD=\K[^,]*' || openssl rand -base64 16)
ALLOWED_ORIGINS=$(echo "$ENV_VARS" | grep -oP 'ALLOWED_ORIGINS=\K[^,]*' || echo "*")
GCS_SECRET_NAME="gcs-credentials"

echo "✅ Variables obtenidas"
echo ""

# Verificar si el repositorio ya está conectado
echo "🔍 Verificando conexión con GitHub..."
CONNECTED_REPOS=$(gcloud builds triggers list --region=us-central1 --format="value(github.owner,github.name)" 2>/dev/null | head -1 || echo "")

if [ -z "$CONNECTED_REPOS" ]; then
    echo ""
    echo "⚠️  El repositorio de GitHub NO está conectado a Cloud Build"
    echo ""
    echo "📋 Pasos para conectar el repositorio:"
    echo "   1. Abre: https://console.cloud.google.com/cloud-build/triggers?project=$PROJECT_ID"
    echo "   2. Click en 'Connect Repository'"
    echo "   3. Selecciona 'GitHub (Cloud Build GitHub App)'"
    echo "   4. Autoriza la aplicación de GitHub"
    echo "   5. Selecciona el repositorio: dante45420/kivi-backendV2"
    echo ""
    echo "   Una vez conectado, ejecuta este script nuevamente."
    echo ""
    exit 0
fi

echo "✅ Repositorio conectado"
echo ""

# Verificar si ya existe un trigger
EXISTING_TRIGGER=$(gcloud builds triggers list --region=us-central1 --filter="name:kivi-backend-auto-deploy" --format="value(id)" 2>/dev/null || echo "")

if [ -n "$EXISTING_TRIGGER" ]; then
    echo "⚠️  Ya existe un trigger con el nombre 'kivi-backend-auto-deploy'"
    read -p "¿Deseas eliminarlo y crear uno nuevo? (s/n): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Ss]$ ]]; then
        echo "🗑️  Eliminando trigger existente..."
        gcloud builds triggers delete "$EXISTING_TRIGGER" --region=us-central1 --quiet
        echo "✅ Trigger eliminado"
    else
        echo "❌ Operación cancelada"
        exit 0
    fi
fi

# Crear el trigger
echo "🚀 Creando trigger de Cloud Build..."
echo ""

# Nota: Necesitamos obtener el connection name del repositorio conectado
# Por ahora, intentamos crear el trigger con el nombre del repositorio

gcloud builds triggers create github \
  --name="kivi-backend-auto-deploy" \
  --repo-name="kivi-backendV2" \
  --repo-owner="dante45420" \
  --branch-pattern="^main$" \
  --build-config="cloudbuild.yaml" \
  --region="us-central1" \
  --substitutions="_CLOUD_SQL_INSTANCE=$CLOUD_SQL_CONNECTION,_DATABASE_URL=$DATABASE_URL,_GCS_BUCKET_NAME=$GCS_BUCKET_NAME,_SECRET_KEY=$SECRET_KEY,_ADMIN_EMAIL=$ADMIN_EMAIL,_ADMIN_PASSWORD=$ADMIN_PASSWORD,_ALLOWED_ORIGINS=$ALLOWED_ORIGINS,_GCS_SECRET_NAME=$GCS_SECRET_NAME" \
  --description="Despliega automáticamente el backend cuando hay push a main" || {
    echo ""
    echo "❌ Error al crear el trigger"
    echo ""
    echo "💡 Alternativa: Crear el trigger manualmente desde la consola:"
    echo "   https://console.cloud.google.com/cloud-build/triggers/add?project=$PROJECT_ID"
    echo ""
    echo "   Configuración:"
    echo "   - Event: Push to a branch"
    echo "   - Branch: ^main$"
    echo "   - Configuration: Cloud Build configuration file (yaml or json)"
    echo "   - Location: cloudbuild.yaml"
    echo "   - Substitution variables:"
    echo "     _CLOUD_SQL_INSTANCE=$CLOUD_SQL_CONNECTION"
    echo "     _DATABASE_URL=$DATABASE_URL"
    echo "     _GCS_BUCKET_NAME=$GCS_BUCKET_NAME"
    echo "     _SECRET_KEY=$SECRET_KEY"
    echo "     _ADMIN_EMAIL=$ADMIN_EMAIL"
    echo "     _ADMIN_PASSWORD=$ADMIN_PASSWORD"
    echo "     _ALLOWED_ORIGINS=$ALLOWED_ORIGINS"
    echo "     _GCS_SECRET_NAME=$GCS_SECRET_NAME"
    exit 1
}

echo ""
echo "✅ Trigger creado exitosamente!"
echo ""
echo "📋 Resumen:"
echo "   - Nombre: kivi-backend-auto-deploy"
echo "   - Repositorio: dante45420/kivi-backendV2"
echo "   - Rama: main"
echo "   - Configuración: cloudbuild.yaml"
echo ""
echo "🎉 Ahora cada push a la rama 'main' desplegará automáticamente el backend"
echo ""
echo "🔍 Ver triggers:"
echo "   gcloud builds triggers list --region=us-central1"
echo ""

