# 🚀 Configurar Deploy Automático desde GitHub

Este documento explica cómo configurar el deploy automático del backend desde GitHub a Google Cloud Run.

## 📋 Prerrequisitos

✅ Repositorio de GitHub: `dante45420/kivi-backendV2`  
✅ Base de datos Cloud SQL funcionando: `kivi-db`  
✅ Servicio Cloud Run existente: `kivi-backend`

## 🔧 Paso 1: Conectar Repositorio de GitHub

1. **Abre la consola de Google Cloud:**
   ```
   https://console.cloud.google.com/cloud-build/triggers?project=kivi-storage
   ```

2. **Click en "Connect Repository"** (botón azul en la parte superior)

3. **Selecciona "GitHub (Cloud Build GitHub App)"**

4. **Autoriza la aplicación:**
   - Te pedirá autorizar Google Cloud Build en GitHub
   - Selecciona tu cuenta de GitHub
   - Autoriza el acceso

5. **Selecciona el repositorio:**
   - Busca: `dante45420/kivi-backendV2`
   - Click en "Connect"

## 🎯 Paso 2: Crear Trigger de Deploy Automático

Después de conectar el repositorio:

1. **Click en "Create Trigger"**

2. **Configuración básica:**
   - **Name:** `kivi-backend-auto-deploy`
   - **Description:** `Despliega automáticamente el backend cuando hay push a main`
   - **Event:** `Push to a branch`
   - **Branch:** `^main$` (solo la rama main)

3. **Configuración de build:**
   - **Type:** `Cloud Build configuration file (yaml or json)`
   - **Location:** `cloudbuild.yaml`
   - **Cloud Build configuration file location:** `cloudbuild.yaml`

4. **Substitution variables** (IMPORTANTE - usar estos valores exactos):

   ```
   _CLOUD_SQL_INSTANCE = kivi-storage:us-central1:kivi-db
   
   _DATABASE_URL = postgresql://kivi_user:Q3sKF14Uppj/EXH/Bi2A5g==@/kivi_v2?host=/cloudsql/kivi-storage:us-central1:kivi-db
   
   _GCS_BUCKET_NAME = kivi-v2-media
   
   _SECRET_KEY = [generar uno nuevo o usar el existente]
   
   _ADMIN_EMAIL = danteparodiwerht@gmail.com
   
   _ADMIN_PASSWORD = [tu contraseña de admin]
   
   _ALLOWED_ORIGINS = *
   
   _GCS_SECRET_NAME = gcs-credentials
   ```

5. **Click en "Create"**

## ✅ Paso 3: Verificar que Funciona

1. **Hacer un cambio pequeño en el código:**
   ```bash
   cd /Users/danteparodiwerth/Desktop/kivi-software/v2-backend
   echo "# Test deploy" >> README.md
   git add README.md
   git commit -m "Test: verificar deploy automático"
   git push origin main
   ```

2. **Verificar en Cloud Build:**
   - Ve a: https://console.cloud.google.com/cloud-build/builds?project=kivi-storage
   - Deberías ver un build iniciándose automáticamente
   - Espera a que termine (5-10 minutos)

3. **Verificar el servicio:**
   ```bash
   gcloud run services describe kivi-backend --region us-central1 --format="value(status.url)"
   ```

## 🔍 Valores Actuales de tu Configuración

Para referencia, estos son los valores que debes usar:

- **Proyecto:** `kivi-storage`
- **Región:** `us-central1`
- **Cloud SQL:** `kivi-storage:us-central1:kivi-db`
- **Base de datos:** `kivi_v2`
- **Usuario DB:** `kivi_user`
- **GCS Bucket:** `kivi-v2-media`
- **Secret Manager:** `gcs-credentials`

## ⚠️ Notas Importantes

1. **Solo la carpeta v2-backend:** El repositorio `kivi-backendV2` solo debe contener los archivos de `v2-backend`, no el directorio raíz del proyecto.

2. **Variables sensibles:** 
   - `_ADMIN_PASSWORD` debe ser tu contraseña real
   - `_SECRET_KEY` debe ser una clave secreta fuerte (puedes generar una con: `openssl rand -hex 32`)

3. **Primera vez:** El primer deploy puede tardar más porque construye la imagen desde cero.

4. **Logs:** Si algo falla, revisa los logs en:
   ```
   https://console.cloud.google.com/cloud-build/builds?project=kivi-storage
   ```

## 🐛 Solución de Problemas

### El trigger no se activa
- Verifica que el repositorio esté conectado
- Verifica que estés haciendo push a la rama `main`
- Revisa los permisos de la aplicación de GitHub

### El deploy falla
- Revisa los logs del build en la consola
- Verifica que todas las variables de sustitución estén correctas
- Verifica que el archivo `cloudbuild.yaml` esté en la raíz del repositorio

### Error de permisos
- Asegúrate de que Cloud Build tenga permisos para:
  - Cloud Run Admin
  - Service Account User
  - Secret Manager Secret Accessor

## 📝 Comandos Útiles

```bash
# Ver triggers configurados
gcloud builds triggers list --region=us-central1

# Ver builds recientes
gcloud builds list --limit=5

# Ver logs de un build específico
gcloud builds log [BUILD_ID]

# Ver estado del servicio
gcloud run services describe kivi-backend --region us-central1
```

