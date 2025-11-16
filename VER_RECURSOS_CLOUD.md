# 📋 Ver Recursos en Google Cloud (kivi-storage)

Guía rápida para ver todos los recursos creados en tu proyecto de Google Cloud.

## 🌐 Consola Web (Recomendado)

### 1. **Cloud Storage (Bucket de Imágenes)**
```
https://console.cloud.google.com/storage/browser?project=kivi-storage
```
- Verás el bucket: `kivi-v2-media`
- Aquí están todas las imágenes subidas

### 2. **Cloud Run (Backend)**
```
https://console.cloud.google.com/run?project=kivi-storage
```
- Verás el servicio: `kivi-backend`
- URL: `https://kivi-backend-nn6ybvu7tq-uc.a.run.app`
- Aquí puedes ver logs, métricas, configuración

### 3. **Cloud SQL (Base de Datos)**
```
https://console.cloud.google.com/sql/instances?project=kivi-storage
```
- Verás la instancia: `kivi-db`
- Base de datos: `kivi_v2`
- Aquí puedes ver conexiones, backups, métricas

### 4. **Container Registry (Imágenes Docker)**
```
https://console.cloud.google.com/gcr/images/kivi-storage?project=kivi-storage
```
- Verás las imágenes: `gcr.io/kivi-storage/kivi-backend`
- Versiones con diferentes tags (COMMIT_SHA)

### 5. **Cloud Build (Builds y Triggers)**
```
https://console.cloud.google.com/cloud-build/builds?project=kivi-storage
```
- Verás todos los builds ejecutados
- Triggers configurados

### 6. **Secret Manager (Credenciales)**
```
https://console.cloud.google.com/security/secret-manager?project=kivi-storage
```
- Verás el secreto: `gcs-credentials`
- Credenciales para acceder a Cloud Storage

### 7. **Dashboard General**
```
https://console.cloud.google.com/home/dashboard?project=kivi-storage
```
- Vista general de todos los recursos
- Métricas y costos

## 💻 Desde la Terminal

### Ver todos los recursos de una vez:

```bash
# Cloud Storage
gcloud storage buckets list --project=kivi-storage

# Cloud Run
gcloud run services list --region=us-central1 --project=kivi-storage

# Cloud SQL
gcloud sql instances list --project=kivi-storage

# Container Registry
gcloud container images list --project=kivi-storage

# Cloud Build Triggers
gcloud builds triggers list --region=us-central1 --project=kivi-storage

# Secret Manager
gcloud secrets list --project=kivi-storage
```

## 📊 Información Detallada de Cada Recurso

### Backend (Cloud Run)
```bash
# Ver detalles del servicio
gcloud run services describe kivi-backend \
  --region=us-central1 \
  --project=kivi-storage

# Ver logs
gcloud run services logs read kivi-backend \
  --region=us-central1 \
  --project=kivi-storage \
  --limit=50
```

### Base de Datos (Cloud SQL)
```bash
# Ver detalles de la instancia
gcloud sql instances describe kivi-db \
  --project=kivi-storage

# Ver bases de datos
gcloud sql databases list \
  --instance=kivi-db \
  --project=kivi-storage
```

### Bucket de Imágenes (Cloud Storage)
```bash
# Listar archivos en el bucket
gsutil ls -r gs://kivi-v2-media/

# Ver tamaño del bucket
gsutil du -sh gs://kivi-v2-media/
```

## 🔗 Enlaces Rápidos

- **Dashboard Principal:** https://console.cloud.google.com/home/dashboard?project=kivi-storage
- **Cloud Run:** https://console.cloud.google.com/run?project=kivi-storage
- **Cloud SQL:** https://console.cloud.google.com/sql/instances?project=kivi-storage
- **Cloud Storage:** https://console.cloud.google.com/storage/browser?project=kivi-storage
- **Cloud Build:** https://console.cloud.google.com/cloud-build/builds?project=kivi-storage
- **Secret Manager:** https://console.cloud.google.com/security/secret-manager?project=kivi-storage

## 📝 Notas

- Todos los recursos están en el proyecto: **kivi-storage**
- Región principal: **us-central1**
- El backend está en Cloud Run (serverless)
- La base de datos está en Cloud SQL (PostgreSQL)
- Las imágenes están en Cloud Storage (bucket: kivi-v2-media)

