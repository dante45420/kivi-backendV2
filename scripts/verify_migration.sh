#!/bin/bash
# Script para verificar que la migración fue exitosa
# Uso: ./verify_migration.sh

set -e

# Colores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔍 Verificando Migración a Google Cloud${NC}"
echo ""

ERRORS=0

# Verificar que gcloud está instalado
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}❌ gcloud CLI no está instalado${NC}"
    ERRORS=$((ERRORS + 1))
else
    echo -e "${GREEN}✅ gcloud CLI instalado${NC}"
fi

# Verificar autenticación
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo -e "${RED}❌ No hay cuenta autenticada en gcloud${NC}"
    echo "   Ejecuta: gcloud auth login"
    ERRORS=$((ERRORS + 1))
else
    ACTIVE_ACCOUNT=$(gcloud auth list --filter=status:ACTIVE --format="value(account)" | head -1)
    echo -e "${GREEN}✅ Autenticado como: $ACTIVE_ACCOUNT${NC}"
fi

# Verificar proyecto
PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
if [ -z "$PROJECT_ID" ]; then
    echo -e "${RED}❌ No hay proyecto configurado${NC}"
    ERRORS=$((ERRORS + 1))
else
    echo -e "${GREEN}✅ Proyecto: $PROJECT_ID${NC}"
fi

echo ""

# Verificar Cloud SQL
echo -e "${YELLOW}🗄️  Verificando Cloud SQL...${NC}"
if gcloud sql instances list --format="value(name)" | grep -q "kivi-db"; then
    INSTANCE_STATUS=$(gcloud sql instances describe kivi-db --format='value(state)' 2>/dev/null || echo "NOT_FOUND")
    if [ "$INSTANCE_STATUS" = "RUNNABLE" ]; then
        echo -e "${GREEN}✅ Instancia kivi-db está corriendo${NC}"
        
        # Verificar base de datos
        if gcloud sql databases list --instance=kivi-db --format="value(name)" | grep -q "kivi_v2"; then
            echo -e "${GREEN}✅ Base de datos kivi_v2 existe${NC}"
        else
            echo -e "${RED}❌ Base de datos kivi_v2 no existe${NC}"
            ERRORS=$((ERRORS + 1))
        fi
        
        # Verificar usuario
        if gcloud sql users list --instance=kivi-db --format="value(name)" | grep -q "kivi_user"; then
            echo -e "${GREEN}✅ Usuario kivi_user existe${NC}"
        else
            echo -e "${RED}❌ Usuario kivi_user no existe${NC}"
            ERRORS=$((ERRORS + 1))
        fi
    else
        echo -e "${RED}❌ Instancia kivi-db no está corriendo (estado: $INSTANCE_STATUS)${NC}"
        ERRORS=$((ERRORS + 1))
    fi
else
    echo -e "${YELLOW}⚠️  Instancia kivi-db no encontrada${NC}"
    echo "   Ejecuta: ./scripts/setup_cloud_sql.sh"
fi

echo ""

# Verificar Cloud Storage
echo -e "${YELLOW}📦 Verificando Cloud Storage...${NC}"
if gsutil ls -b gs://kivi-v2-media &> /dev/null; then
    echo -e "${GREEN}✅ Bucket kivi-v2-media existe${NC}"
    
    # Verificar permisos
    BUCKET_IAM=$(gsutil iam get gs://kivi-v2-media 2>/dev/null || echo "")
    if [ -n "$BUCKET_IAM" ]; then
        echo -e "${GREEN}✅ Permisos del bucket configurados${NC}"
    else
        echo -e "${YELLOW}⚠️  No se pudieron verificar permisos del bucket${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  Bucket kivi-v2-media no encontrado${NC}"
    echo "   Ejecuta: gsutil mb -p $PROJECT_ID -l us-central1 gs://kivi-v2-media"
fi

echo ""

# Verificar Cloud Run Backend
echo -e "${YELLOW}🚀 Verificando Cloud Run Backend...${NC}"
if gcloud run services describe kivi-backend --platform managed --region us-central1 &> /dev/null; then
    BACKEND_URL=$(gcloud run services describe kivi-backend \
        --platform managed \
        --region us-central1 \
        --format='value(status.url)' 2>/dev/null || echo "")
    
    if [ -n "$BACKEND_URL" ]; then
        echo -e "${GREEN}✅ Servicio kivi-backend desplegado${NC}"
        echo -e "   URL: $BACKEND_URL"
        
        # Health check
        if curl -s "$BACKEND_URL/health" | grep -q "ok"; then
            echo -e "${GREEN}✅ Health check pasó${NC}"
        else
            echo -e "${RED}❌ Health check falló${NC}"
            ERRORS=$((ERRORS + 1))
        fi
    else
        echo -e "${RED}❌ No se pudo obtener URL del backend${NC}"
        ERRORS=$((ERRORS + 1))
    fi
else
    echo -e "${YELLOW}⚠️  Servicio kivi-backend no encontrado${NC}"
    echo "   Ejecuta: gcloud run deploy kivi-backend ..."
fi

echo ""

# Verificar Cloud Run Frontend (opcional)
echo -e "${YELLOW}🌐 Verificando Cloud Run Frontend...${NC}"
if gcloud run services describe kivi-frontend --platform managed --region us-central1 &> /dev/null; then
    FRONTEND_URL=$(gcloud run services describe kivi-frontend \
        --platform managed \
        --region us-central1 \
        --format='value(status.url)' 2>/dev/null || echo "")
    
    if [ -n "$FRONTEND_URL" ]; then
        echo -e "${GREEN}✅ Servicio kivi-frontend desplegado${NC}"
        echo -e "   URL: $FRONTEND_URL"
    else
        echo -e "${RED}❌ No se pudo obtener URL del frontend${NC}"
        ERRORS=$((ERRORS + 1))
    fi
else
    echo -e "${YELLOW}⚠️  Servicio kivi-frontend no encontrado (opcional)${NC}"
fi

echo ""

# Verificar Secret Manager
echo -e "${YELLOW}🔐 Verificando Secret Manager...${NC}"
if gcloud secrets describe gcs-credentials &> /dev/null; then
    echo -e "${GREEN}✅ Secreto gcs-credentials existe${NC}"
else
    echo -e "${YELLOW}⚠️  Secreto gcs-credentials no encontrado${NC}"
    echo "   Ejecuta: gcloud secrets create gcs-credentials --data-file=./gcs-credentials.json"
fi

echo ""

# Resumen
echo -e "${BLUE}📊 Resumen${NC}"
if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}✅ Todas las verificaciones pasaron${NC}"
    echo ""
    echo -e "${GREEN}🎉 ¡La migración está completa y funcionando!${NC}"
    exit 0
else
    echo -e "${RED}❌ Se encontraron $ERRORS error(es)${NC}"
    echo ""
    echo -e "${YELLOW}💡 Revisa los errores arriba y corrige los problemas${NC}"
    exit 1
fi

