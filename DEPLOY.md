# 🚀 Guía de Deploy - Kivi V2 Backend

## Prerrequisitos

1. **Google Cloud SDK** instalado y configurado
2. **Docker** instalado (opcional, para pruebas locales)
3. **Cuenta de Google Cloud** con facturación habilitada
4. **Proyecto de Google Cloud** creado

## Paso 1: Configurar Google Cloud

```bash
# Iniciar sesión
gcloud auth login

# Configurar proyecto
gcloud config set project YOUR_PROJECT_ID

# Habilitar APIs necesarias
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable sqladmin.googleapis.com
gcloud services enable storage-api.googleapis.com
```

## Paso 2: Configurar Base de Datos

### Opción A: Cloud SQL (PostgreSQL) - Recomendado para producción

```bash
# Crear instancia de Cloud SQL
gcloud sql instances create kivi-db \
    --database-version=POSTGRES_15 \
    --tier=db-f1-micro \
    --region=us-central1

# Crear base de datos
gcloud sql databases create kivi_v2 --instance=kivi-db

# Crear usuario
gcloud sql users create kivi --instance=kivi-db --password=YOUR_SECURE_PASSWORD
```

### Opción B: SQLite (Solo para testing, NO para producción)

```bash
# SQLite se creará automáticamente
# Pero NO es recomendado para Cloud Run (el filesystem es efímero)
```

## Paso 3: Configurar Google Cloud Storage

```bash
# Crear bucket para archivos subidos
gsutil mb -l us-central1 gs://kivi-v2-media

# Hacer el bucket público (opcional, solo si quieres URLs públicas)
gsutil iam ch allUsers:objectViewer gs://kivi-v2-media
```

## Paso 4: Configurar Service Account para GCS

```bash
# Crear service account
gcloud iam service-accounts create kivi-storage \
    --display-name="Kivi Storage Service Account"

# Dar permisos al bucket
gsutil iam ch serviceAccount:kivi-storage@YOUR_PROJECT_ID.iam.gserviceaccount.com:objectAdmin gs://kivi-v2-media

# Generar key JSON
gcloud iam service-accounts keys create gcs-key.json \
    --iam-account=kivi-storage@YOUR_PROJECT_ID.iam.gserviceaccount.com
```

## Paso 5: Deploy a Cloud Run

### Opción A: Deploy directo desde código local

```bash
# Build y deploy en un comando
gcloud run deploy kivi-backend \
    --source . \
    --platform managed \
    --region us-central1 \
    --allow-unauthenticated \
    --set-env-vars="FLASK_ENV=production,SECRET_KEY=your-secret-key,GCS_BUCKET_NAME=kivi-v2-media" \
    --set-secrets="DATABASE_URL=DATABASE_URL:latest,GOOGLE_APPLICATION_CREDENTIALS=GCS_KEY:latest"
```

### Opción B: Deploy con Cloud Build (CI/CD automático)

```bash
# Conectar repositorio de GitHub
gcloud alpha builds triggers create github \
    --repo-name=kivi-software \
    --repo-owner=YOUR_GITHUB_USERNAME \
    --branch-pattern="^main$" \
    --build-config=cloudbuild.yaml

# Cada push a main desplegará automáticamente
```

## Paso 6: Configurar Variables de Entorno en Cloud Run

```bash
# Secret Manager para datos sensibles
echo -n "postgresql://user:pass@/cloudsql/project:region:instance/kivi_v2" | gcloud secrets create DATABASE_URL --data-file=-
echo -n "$(cat gcs-key.json)" | gcloud secrets create GCS_KEY --data-file=-

# Variables de entorno públicas
gcloud run services update kivi-backend \
    --region=us-central1 \
    --set-env-vars="FLASK_ENV=production,SECRET_KEY=your-secret-key,GCS_BUCKET_NAME=kivi-v2-media,ALLOWED_ORIGINS=https://kivi.vercel.app"
```

## Paso 7: Conectar Cloud SQL a Cloud Run

```bash
# Obtener connection name de tu instancia
gcloud sql instances describe kivi-db --format="value(connectionName)"

# Actualizar Cloud Run para usar Cloud SQL
gcloud run services update kivi-backend \
    --region=us-central1 \
    --add-cloudsql-instances=YOUR_PROJECT_ID:us-central1:kivi-db
```

## Paso 8: Verificar Deploy

```bash
# Obtener URL del servicio
gcloud run services describe kivi-backend --region=us-central1 --format="value(status.url)"

# Probar endpoint
curl https://YOUR_SERVICE_URL/api/categories
```

## Migraciones de Base de Datos

```bash
# Conectarse a Cloud SQL para ejecutar migraciones
gcloud sql connect kivi-db --user=kivi

# O usar Cloud Run Job para ejecutar migraciones
gcloud run jobs create kivi-migrate \
    --image=gcr.io/YOUR_PROJECT_ID/kivi-backend:latest \
    --region=us-central1 \
    --execute-now \
    --command="python,-m,flask,db,upgrade"
```

## Logs y Monitoreo

```bash
# Ver logs en tiempo real
gcloud run services logs tail kivi-backend --region=us-central1

# Ver logs en Cloud Console
open https://console.cloud.google.com/run/detail/us-central1/kivi-backend/logs
```

## Costos Estimados

- **Cloud Run**: ~$5-10/mes (con tier gratuito de 2M requests)
- **Cloud SQL (db-f1-micro)**: ~$10-15/mes
- **Cloud Storage**: ~$1-5/mes (primeros 5GB gratis)
- **Total estimado**: ~$15-30/mes

## Troubleshooting

### Error: "Service account does not have permission"
```bash
# Dar permisos necesarios
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:kivi-storage@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/storage.objectAdmin"
```

### Error: "Database connection failed"
```bash
# Verificar connection string
gcloud sql instances describe kivi-db

# Verificar que Cloud Run tiene acceso
gcloud run services describe kivi-backend --region=us-central1
```

### Error: "CORS not working"
- Verificar que `ALLOWED_ORIGINS` incluye tu dominio de Vercel
- Verificar que no hay trailing slashes en las URLs

## Actualizaciones

```bash
# Para actualizar el servicio
git push origin main  # Si usas Cloud Build

# O deploy manual
gcloud run deploy kivi-backend --source .
```

## Rollback

```bash
# Listar revisiones
gcloud run revisions list --service=kivi-backend --region=us-central1

# Volver a revisión anterior
gcloud run services update-traffic kivi-backend \
    --region=us-central1 \
    --to-revisions=kivi-backend-00002-abc=100
```

## Contacto

Para más ayuda, consulta:
- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Cloud SQL Documentation](https://cloud.google.com/sql/docs)

