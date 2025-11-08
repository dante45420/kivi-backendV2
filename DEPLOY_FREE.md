# 🆓 Deploy GRATIS - Kivi V2

## Opción 100% Gratuita: Railway.app

Railway ofrece:
- ✅ Backend (Python/Flask) GRATIS
- ✅ PostgreSQL GRATIS
- ✅ 500GB bandwidth/mes GRATIS
- ✅ Deployments automáticos desde GitHub
- ✅ Variables de entorno
- ✅ Logs en tiempo real

### Límites del Plan Gratuito
- $5 USD en créditos mensuales (suficiente para apps pequeñas)
- 500 horas de ejecución/mes
- 1GB de RAM
- PostgreSQL con 1GB de storage

## Paso 1: Crear cuenta en Railway

1. Ir a [railway.app](https://railway.app)
2. Hacer login con GitHub
3. Railway te da $5 USD gratis cada mes

## Paso 2: Crear proyecto

```bash
# Opción A: Desde Railway Dashboard

1. Click en "New Project"
2. Seleccionar "Deploy from GitHub repo"
3. Conectar tu repositorio kivi-software
4. Railway detectará automáticamente que es Python

# Opción B: Desde Railway CLI

npm install -g @railway/cli
railway login
cd v2-backend
railway init
railway up
```

## Paso 3: Agregar PostgreSQL

```bash
# En Railway Dashboard
1. Click en tu proyecto
2. Click en "New" → "Database" → "PostgreSQL"
3. Railway creará automáticamente la base de datos
4. La variable DATABASE_URL se configurará automáticamente
```

## Paso 4: Configurar Variables de Entorno

En Railway Dashboard → Variables:

```bash
FLASK_ENV=production
SECRET_KEY=tu-secret-key-aqui
ALLOWED_ORIGINS=https://tu-app.vercel.app
GCS_BUCKET_NAME=  # Dejar vacío para usar storage local
ADMIN_EMAIL=admin@kivi.cl
ADMIN_PASSWORD=tu-password-seguro
```

## Paso 5: Configurar Railway.json

```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "gunicorn --bind :$PORT --workers 2 app:app",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

## Paso 6: Migraciones de Base de Datos

Railway no tiene filesystem persistente, así que ejecuta migraciones localmente:

```bash
# 1. Obtener DATABASE_URL de Railway
# En Dashboard → PostgreSQL → Connect → Connection URL

# 2. Ejecutar migraciones localmente
export DATABASE_URL="postgresql://..."
cd v2-backend
source venv/bin/activate
python << 'EOF'
from app import create_app
from app.db import db
from sqlalchemy import text

app = create_app()
with app.app_context():
    # Crear tablas
    db.create_all()
    
    # Agregar columnas nuevas
    try:
        db.session.execute(text('ALTER TABLE order_items ADD COLUMN charged_qty FLOAT'))
        db.session.execute(text('ALTER TABLE order_items ADD COLUMN charged_unit VARCHAR(16)'))
        db.session.commit()
        print("✅ Columnas agregadas")
    except Exception as e:
        print(f"Columnas ya existen o error: {e}")
EOF
```

## Storage de Archivos

### Opción A: Cloudinary (Gratis - Recomendado)

```bash
# 1. Crear cuenta en cloudinary.com (GRATIS)
# 2. Obtener credenciales
# 3. Agregar en Railway:

CLOUDINARY_CLOUD_NAME=tu-cloud-name
CLOUDINARY_API_KEY=tu-api-key
CLOUDINARY_API_SECRET=tu-api-secret
```

### Opción B: Railway Storage (Local)

Railway guarda archivos temporalmente, pero se pierden al redeploy.
Para producción, usar Cloudinary.

## Frontend en Vercel (Gratis SIEMPRE)

```bash
# 1. Obtener URL de Railway
# Ejemplo: https://kivi-backend-production.up.railway.app

# 2. En Vercel, configurar:
VITE_API_URL=https://kivi-backend-production.up.railway.app
```

## Costos

```
Railway Free Tier:
- $5 USD/mes en créditos GRATIS
- Suficiente para ~500 requests/día
- Si se agota, la app se pausa hasta el siguiente mes

Vercel Free Tier:
- 100GB bandwidth GRATIS
- Unlimited deployments
- GRATIS para siempre

Cloudinary Free Tier:
- 25 créditos/mes GRATIS
- 25GB storage GRATIS
- 25GB bandwidth/mes GRATIS

COSTO TOTAL: $0/mes 🎉
```

## Alternativa: Render.com

Render también es gratis:

```bash
# 1. Ir a render.com
# 2. Conectar GitHub
# 3. Crear "Web Service" desde tu repo
# 4. Crear "PostgreSQL" (gratis)
# 5. Configurar variables de entorno
```

Límites de Render Free:
- 750 horas/mes GRATIS
- PostgreSQL gratis (expira después de 90 días)
- La app se duerme después de 15 min de inactividad

## Comparación

| Servicio | Railway | Render | Google Cloud |
|----------|---------|--------|--------------|
| Backend | ✅ $5/mes créditos | ✅ 750h/mes | ✅ Free tier |
| PostgreSQL | ✅ Gratis | ⚠️ 90 días | ❌ ~$15/mes |
| Bandwidth | ✅ 500GB | ✅ 100GB | ✅ Incluido |
| Sleep/Pause | ❌ No duerme | ⚠️ Duerme 15min | ❌ No duerme |
| Duración | ♾️ Siempre | ⚠️ DB 90 días | ⚠️ $300 por 90d |

**Recomendación**: Railway.app es la mejor opción gratis a largo plazo.

## Deploy Completo Gratis

```bash
# 1. Backend en Railway
railway login
cd v2-backend
railway init
railway up

# 2. Agregar PostgreSQL en Railway Dashboard

# 3. Configurar variables en Railway

# 4. Frontend en Vercel
cd ../v2-frontend
vercel --prod

# 5. Actualizar CORS en Railway con URL de Vercel

# LISTO! Todo gratis 🎉
```

## Monitoreo

Railway te muestra:
- Uso de CPU y RAM
- Créditos gastados
- Logs en tiempo real
- Métricas de requests

## Upgrade (Si creces)

Si necesitas más recursos:
- Railway: $5/mes por $5 adicionales en créditos
- Render: $7/mes para PostgreSQL permanente
- Google Cloud: Paga solo lo que uses

## Siguiente Paso

¿Quieres que te ayude a hacer el deploy en Railway? Es más simple que Google Cloud y 100% gratis.

